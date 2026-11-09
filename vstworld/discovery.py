"""Inspeção limitada de formulários e HTML público; não salva configurações."""
import asyncio
import re
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

import httpx
from bs4 import BeautifulSoup

from .catalog import Catalog, SourceError, select_node
from .config import Source, load_sources
from .http import public_url


def result_pattern(soup):
    # shortcut: apenas estruturas uCoz e WordPress observadas; ampliar com exemplos reais de outros layouts.
    for item, title in [('.eBlock', '.eTitle a[href]'), ('article', 'h2 a[href]')]:
        if any(node.select_one(title) for node in soup.select(item)):
            return item, title
    return None


def disabled_control(node):
    if node.has_attr('disabled'):
        return True
    for fieldset in node.find_parents('fieldset', disabled=True):
        legend = fieldset.find('legend', recursive=False)
        if legend is None or not any(parent is legend for parent in node.parents):
            return True
    return False


def search_form(soup, catalog, source, base, issues=None):
    issues = issues if issues is not None else []
    search_words = re.compile(r'search|pesquis|busca|поиск|пошук|suche|recherch', re.I)
    mutation = re.compile(r'(^|[^a-z])(delete|remove|edit|update|create|login|logout|register|subscribe|upload)([^a-z]|$)', re.I)
    controls = soup.select('input, select, textarea, button')
    for form in soup.select('form')[:50]:
        fields = [node for node in controls if
                  (node.get('form') == form.get('id') if node.has_attr('form') else node.find_parent('form') is form)
                  and not disabled_control(node)]
        if len(fields) > 200 or any(node.get('type', '').lower() in ('password', 'file') for node in fields):
            issues.append('Não envio formulários de login, envio de arquivos ou formulários grandes demais.')
            continue
        text_fields = [node for node in fields if node.name == 'input' and node.get('name')
                       and node.get('type', 'text').lower() in ('text', 'search')]
        context = ' '.join(str(form.get(key, '')) for key in ('role', 'id', 'class', 'action'))
        queries = []
        for node in text_fields:
            labels = soup.find_all('label', attrs={'for': node.get('id')}) if node.get('id') else []
            if node.find_parent('label'):
                labels.append(node.find_parent('label'))
            signal = ' '.join([*(str(node.get(key, '')) for key in ('name', 'id', 'placeholder', 'aria-label')),
                               *(label.get_text(' ', strip=True) for label in labels)])
            if (node.get('type', '').lower() == 'search' or
                    node['name'].lower() in ('q', 's', 'query', 'keyword', 'searchword') or
                    search_words.search(signal) or (len(text_fields) == 1 and search_words.search(context))):
                queries.append(node)
        if len(queries) != 1:
            if queries:
                issues.append('Encontrei mais de um possível campo de busca e não vou escolher um ao acaso.')
            continue
        query = queries[0]
        submit = next((node for node in fields if node.get('type', 'submit' if node.name == 'button' else 'text').lower() == 'submit'), None)
        method = (submit.get('formmethod') if submit else None) or form.get('method', 'GET')
        method = method.upper()
        encoding = (submit.get('formenctype') if submit else None) or form.get('enctype', 'application/x-www-form-urlencoded')
        if method not in ('GET', 'POST') or (method == 'POST' and encoding.lower() != 'application/x-www-form-urlencoded'):
            issues.append('A busca usa um tipo de envio que ainda precisa de uma integração específica.')
            continue
        charset = form.get('accept-charset', 'utf-8').lower().strip()
        if charset not in ('utf-8', 'utf8'):
            issues.append('A busca declara uma codificação de texto ainda não suportada automaticamente.')
            continue
        try:
            action = (submit.get('formaction') if submit else None) or form.get('action') or base
            action = catalog.url(source, action.split('#', 1)[0] or base, base)
            if method == 'GET':
                action = str(httpx.URL(action).copy_with(query=None))
        except ValueError:
            issues.append('O formulário envia a busca para outro domínio ou endereço não permitido.')
            continue
        params = {}
        invalid = False
        for node in fields:
            name = node.get('name')
            if node is query or not name:
                continue
            kind = node.get('type', 'submit' if node.name == 'button' else 'text').lower()
            if node.name == 'select':
                explicit = node.select('option[selected]')
                options = [option for option in node.select('option') if not option.has_attr('disabled')
                           and not option.find_parent('optgroup', disabled=True)]
                selected = [option for option in explicit if any(option is enabled for enabled in options)]
                if not node.has_attr('multiple'):
                    selected = selected[-1:] if explicit else options[:1]
                if len(selected) > 1:
                    invalid = True
                    break
                if not selected:
                    continue
                value = selected[0].get('value', selected[0].get_text(' ', strip=True))
            elif kind in ('checkbox', 'radio'):
                if not node.has_attr('checked'):
                    continue
                value = node.get('value', 'on')
            elif kind in ('reset', 'button') or (kind == 'submit' and node is not submit):
                continue
            elif (node.name == 'input' and kind == 'hidden') or node is submit:
                value = node.get('value', '')
            else:
                invalid = True
                break
            if name in params or name == query['name']:
                invalid = True
                break
            params[name] = value
        if invalid:
            issues.append('A busca tem campos adicionais ou vários valores com o mesmo nome; ainda não consigo reproduzi-la sem perder informações.')
            continue
        if mutation.search(urlsplit(action).path) or any(mutation.search(value) for key, value in
                [*params.items(), *parse_qsl(urlsplit(action).query)]
                if key.lower() in ('action', 'do', 'subaction', 'op', 'operation')):
            issues.append('Este formulário parece alterar dados ou acessar uma conta; não foi enviado como busca.')
            continue
        maximum = query.get('maxlength', '200')
        return dict(search_path=action, method=method, query_param=query['name'], params=params,
                    max_query=min(500, max(1, int(maximum))) if maximum.isdigit() else 200)
    return None


def download_pattern(soup, catalog, source, base, selectors=None):
    selectors = selectors or ['a.sprite[href]', 'a[download][href]', 'a[href^="magnet:?"]',
                 'a[href$=".torrent"]', 'a[href$=".zip"]', 'a[href$=".exe"]', 'a[href$=".msi"]']
    found = []
    for selector in selectors:
        for node in soup.select(selector):
            raw = node.get('href', '')
            if not raw:
                continue
            if raw.startswith('magnet:?'):
                if not re.search(r'(?:\?|&)xt=urn:btih:(?:[a-fA-F0-9]{40}|[A-Za-z2-7]{32})(?:&|$)', raw):
                    continue
            else:
                try:
                    catalog.url(source, raw, base)
                except ValueError:
                    continue
            found.append(selector)
            break
    return ', '.join(found) or None


async def detect_source(url: str, existing_sources: list[Source], transport=None) -> dict:
    checks = []
    candidate = None

    def check(name, status, message):
        checks.append(dict(name=name, status=status, message=message))

    def report():
        complete = {'search', 'download'} <= {c['name'] for c in checks if c['status'] == 'verified'}
        message = ('Configuração encontrada. Revise as verificações antes de salvar.' if candidate and complete else
                   'Inspeção parcial. Veja o que foi confirmado e o que ainda falta.' if candidate else
                   'Não foi possível montar uma configuração confiável com o HTML observado. Veja as verificações.')
        return dict(source=candidate, checks=checks, message=message)

    try:
        supplied = public_url(url.strip())
    except (ValueError, httpx.InvalidURL) as exc:
        check('url', 'blocked', str(exc))
        return report()
    origin = str(supplied.copy_with(path='/', query=None))
    existing = next((s for s in existing_sources if supplied.host in s.hosts), None)
    if existing is None:
        presets = load_sources(Path(__file__).with_name('presets.json'))
        existing = next((s for s in presets if supplied.host in s.hosts), None)
        if existing and any(s.id == existing.id for s in existing_sources):
            existing = None
        if existing and not existing.enabled:
            return {'source':existing.model_dump(), 'checks':[{'name':'preset', 'status':'unverified', 'message':existing.note}],
                    'message':'Configuração experimental desativada. Confira as limitações antes de habilitar; nenhuma consulta foi feita.'}
    source_id = re.sub('[^a-z0-9_-]', '-', supplied.host.lower())[:45].strip('-') or 'fonte'
    stem, suffix = source_id, 2
    while any(s.id == source_id for s in existing_sources):
        source_id = f'{stem}-{suffix}'
        suffix += 1
    source = existing or Source(id=source_id, name=supplied.host[:80], base_url=origin,
        hosts=[supplied.host], search_path='/', item_selector='body', title_selector='a', download_selector='a[download]')
    catalog = Catalog([source], transport=transport)
    candidate = existing.model_dump() if existing else None

    async def page(target, **kwargs):
        response, body = await catalog.fetch(source, target, **kwargs)
        response.raise_for_status()
        return BeautifulSoup(body, 'html.parser'), str(response.url)

    try:
        async with asyncio.timeout(45):
            home, home_url = await page(origin)
            check('homepage', 'verified', f'Página inicial consultada por HTTPS: {home_url}')
            check('robots', 'verified' if source.respect_robots else 'unverified',
                  'robots.txt aplicado às consultas.' if source.respect_robots else
                  'robots.txt não aplicado, conforme a configuração existente desta fonte.')
            form_issues = []
            form = search_form(home, catalog, source, home_url, form_issues)
            check('form', 'verified' if form else 'unverified',
                  f"Formulário nativo observado: {form['method']} {form['search_path']}; campo {form['query_param']}; "
                  f"parâmetros adicionais: {', '.join(form['params']) or 'nenhum'}." if form else
                  form_issues[-1] if form_issues else
                  'Não encontrei um campo de busca identificável no HTML. A busca pode depender de JavaScript ou de uma integração específica.')
            pattern = (source.item_selector, source.title_selector) if existing else result_pattern(home)
            if not pattern or not any(select_node(n, pattern[1]) for n in home.select(pattern[0])):
                check('results', 'unverified', 'Não encontrei blocos de resultados e títulos compatíveis no HTML inicial.')
                return report()
            item_selector, title_selector = pattern
            check('results', 'verified', f'Estrutura observada: {item_selector}; títulos: {title_selector}.')
            sample = None
            for node in home.select(item_selector):
                title = select_node(node, title_selector)
                link = select_node(node, source.link_selector) if existing and source.link_selector else title
                if title and link and link.get('href') and title.get_text(' ', strip=True):
                    try:
                        sample = title.get_text(' ', strip=True), catalog.url(source, link['href'], home_url)
                        break
                    except ValueError:
                        pass
            if not sample:
                check('search', 'unverified', 'Sem título e link interno válidos para testar uma pesquisa real.')
                return report()
            settings = dict(search_path=source.search_path, method=source.method, query_param=source.query_param,
                            params=source.params, max_query=source.max_query) if existing else form
            if not settings:
                return report()
            query = ' '.join(sample[0].split()[:3])[:settings['max_query']]
            search_url = catalog.url(source, settings['search_path'])
            params = {**settings['params'], settings['query_param']: query}
            search = None
            try:
                search, search_url = await page(str(httpx.URL(search_url).copy_merge_params(params))
                    if settings['method'] == 'GET' else search_url,
                    method=settings['method'], data=params if settings['method'] == 'POST' else None)
                titles = [select_node(n, title_selector) for n in search.select(item_selector)]
                matched = any(t and query.casefold() in t.get_text(' ', strip=True).casefold() for t in titles)
                check('search', 'verified' if matched else 'unverified',
                      f'Pesquisa enviada com o título real “{query}”; ' + ('resultados compatíveis encontrados.' if matched else
                      'não encontrei resultado compatível; a busca pode exigir JavaScript ou outro layout.'))
            except (SourceError, httpx.HTTPError, OSError, ValueError) as exc:
                check('search', 'blocked', f'Não foi possível verificar a pesquisa: {exc}')
            next_selector = source.next_selector if existing else None
            if search is not None and not existing:
                for selector in ('a[rel~="next"][href]', 'a.swchItem-next[href]', 'a.next.page-numbers[href]'):
                    if search.select_one(selector):
                        next_selector = selector
                        break
            next_node = search.select_one(next_selector) if search is not None and next_selector else None
            try:
                next_url = catalog.url(source, next_node['href'], search_url) if next_node else None
            except (ValueError, KeyError):
                next_url = None
            check('pagination', 'verified' if next_url else 'unverified',
                  'Link de próxima página observado; a página seguinte não foi consultada.' if next_url else
                  'Não encontrei link seguro de próxima página nesta amostra.')
            detail_url = str(supplied) if supplied.path not in ('', '/') else sample[1]
            if urlsplit(detail_url).path.lower().endswith(('.exe', '.msi', '.zip', '.rar', '.7z', '.dmg', '.pkg', '.torrent')):
                check('download', 'unverified', 'A URL de amostra aponta para um arquivo; ele não foi requisitado.')
                return report()
            detail, detail_url = await page(detail_url)
            check('detail', 'verified', f'Página de detalhes consultada: {detail_url}')
            download = download_pattern(detail, catalog, source, detail_url,
                                        [source.download_selector] if existing else None)
            check('download', 'verified' if download else 'unverified',
                  'Link de download observado no HTML. O destino e o arquivo não foram baixados nem validados.' if download else
                  'Não encontrei link de download reconhecível e permitido na página de detalhes.')
            if not existing and download:
                candidate = Source.model_validate({**source.model_dump(), **settings,
                    'item_selector': item_selector, 'title_selector': title_selector,
                    'next_selector': next_selector if next_url else None, 'download_selector': download}).model_dump()
    except (SourceError, httpx.HTTPError, OSError, ValueError, TimeoutError) as exc:
        check('access', 'blocked', f'Inspeção interrompida: {exc}')
    finally:
        await catalog.close()
    return report()
