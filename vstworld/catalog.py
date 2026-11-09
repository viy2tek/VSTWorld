import asyncio
import logging
import re
import secrets
import time
from collections import OrderedDict
from datetime import datetime
from urllib.parse import parse_qs, quote, urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup

from .http import PublicTransport, public_url

USER_AGENT = 'VSTWorld'
MAX_BYTES = 2_000_000
IMAGE_TYPES = ('image/jpeg', 'image/png', 'image/webp', 'image/gif', 'image/avif')
log = logging.getLogger(__name__)


class SourceError(Exception):
    pass


def normalized_path(value):
    # RFC 9309: decodificar apenas octetos ASCII não reservados.
    value = quote(value, safe="/%?&=;:+,$@!*'()-._~")
    return re.sub(r'%([0-9a-fA-F]{2})', lambda m: (
        chr(int(m[1], 16)) if chr(int(m[1], 16)) in
        'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~'
        else '%' + m[1].upper()), value)


class Robots:
    def __init__(self, text):
        groups, agents, rules = [], [], []
        for line in text.splitlines():
            key, sep, value = line.split('#', 1)[0].partition(':')
            if not sep:
                continue
            key, value = key.strip().lower(), value.strip()
            if key == 'user-agent':
                if rules:
                    groups.append((agents, rules))
                    agents, rules = [], []
                agents.append(value.lower())
            elif agents and key in ('allow', 'disallow', 'crawl-delay'):
                rules.append((key, value))
        groups.append((agents, rules))
        exact = [rules for agents, rules in groups if USER_AGENT.lower() in agents]
        selected = exact or [rules for agents, rules in groups if '*' in agents]
        self.rules = [rule for rules in selected for rule in rules]
        self.delay = max([0.0] + [float(value) for key, value in self.rules
                                  if key == 'crawl-delay' and re.fullmatch(r'\d+(\.\d+)?', value)])

    def allowed(self, url):
        split = urlsplit(str(url))
        path = normalized_path(split.path or '/') + ('?' + normalized_path(split.query) if split.query else '')
        matches = []
        for key, value in self.rules:
            if key not in ('allow', 'disallow') or not value:
                continue
            end = value.endswith('$')
            pattern = normalized_path(value[:-1] if end else value)
            regex = re.escape(pattern).replace(r'\*', '.*') + ('$' if end else '')
            if re.match(regex, path):
                matches.append((len(pattern.replace('*', '').encode()), key == 'allow'))
        return max(matches, default=(0, True))[1]


class Catalog:
    def __init__(self, sources, transport=None):
        self.sources = {source.id: source for source in sources}
        self.client = httpx.AsyncClient(transport=transport or PublicTransport(), trust_env=False,
            timeout=10, follow_redirects=False, headers={'User-Agent': USER_AGENT, 'Accept-Encoding': 'identity'})
        self.semaphore = asyncio.Semaphore(4)
        self.locks = {source.id: asyncio.Lock() for source in sources}
        self.last_request = {}
        self.robots = {}
        self.robot_locks = {}
        self.refs = OrderedDict()

    async def close(self):
        await self.client.aclose()

    def source(self, source_id):
        source = self.sources.get(source_id)
        if not source or not source.enabled:
            raise SourceError('Fonte inexistente ou desativada')
        return source

    def url(self, source, value, base=None):
        url = public_url(urljoin(base or source.base_url, value))
        if url.host not in source.hosts:
            raise ValueError('Destino fora dos domínios configurados')
        return str(url)

    def remember(self, kind, source_id, value, query=''):
        # shortcut: até 2000 referências por hora; ampliar se o catálogo consultado exceder esse volume.
        now = time.monotonic()
        while self.refs and (len(self.refs) >= 2000 or next(iter(self.refs.values()))[0] < now - 3600):
            self.refs.popitem(last=False)
        token = secrets.token_urlsafe(24)
        self.refs[token] = (now, kind, source_id, value, query)
        return token

    def recall(self, token, kind, source_id=None, query=None):
        saved = self.refs.get(token)
        if (not saved or saved[0] < time.monotonic() - 3600 or saved[1] != kind
                or (source_id is not None and saved[2] != source_id)
                or (query is not None and saved[4] != query)):
            raise SourceError('Referência expirada ou inválida; refaça a pesquisa')
        return saved[2], saved[3]

    async def policy(self, source, url):
        if not source.respect_robots:
            return 0
        origin = str(httpx.URL(url).copy_with(path='/robots.txt', query=None))
        async with self.robot_locks.setdefault(origin, asyncio.Lock()):
            saved = self.robots.get(origin)
            if not saved or saved[0] < time.monotonic() - 300:
                response, body = await self.fetch(source, origin, robots=False)
                if response.status_code in (404, 410):
                    policy = Robots('')
                elif response.status_code == 200 and b'<html' not in body[:500].lower():
                    policy = Robots(body.decode('utf-8-sig', errors='replace'))
                else:
                    raise SourceError('Não foi possível verificar robots.txt; consulta suspensa')
                saved = (time.monotonic(), policy)
                self.robots[origin] = saved
        if not saved[1].allowed(url):
            raise SourceError('Consulta restrita pelo robots.txt da fonte')
        return saved[1].delay

    async def fetch(self, source, url, *, method='GET', data=None, robots=True, headers_only=False,
                    content_types=('text/', 'xml', 'json'), max_bytes=MAX_BYTES):
        for _ in range(6):
            url = self.url(source, url)
            delay = await self.policy(source, url) if robots else 0
            async with self.locks[source.id]:
                wait = self.last_request.get(source.id, 0) + max(source.interval, delay) - time.monotonic()
                if wait > 0:
                    await asyncio.sleep(wait)
                async with self.client.stream(method, url, data=data) as response:
                    self.last_request[source.id] = time.monotonic()
                    if response.is_redirect:
                        location = response.headers.get('location')
                        if not location:
                            raise SourceError('Redirecionamento sem destino')
                        url = self.url(source, location, url)
                        if response.status_code == 303 or (method == 'POST' and response.status_code in (301, 302)):
                            method, data = 'GET', None
                        continue
                    if headers_only:
                        return response, b''
                    if response.headers.get('content-encoding', 'identity').lower() not in ('identity', ''):
                        raise SourceError('A fonte retornou compressão não solicitada')
                    mime = response.headers.get('content-type', '').split(';')[0].strip().lower()
                    if response.is_success and not any(
                            mime.startswith(kind) if kind.endswith('/') else
                            (kind in mime if kind in ('xml', 'json') else mime == kind) for kind in content_types):
                        raise SourceError('O destino retornou um tipo de conteúdo inesperado')
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > max_bytes:
                            raise SourceError('Resposta excedeu o limite de tamanho')
                    return response, bytes(body)
        raise SourceError('Excesso de redirecionamentos')

    async def search(self, source_id, query, cursor=None, section=None):
        source = self.source(source_id)
        if len(query) > source.max_query:
            raise SourceError(f'Esta fonte aceita até {source.max_query} caracteres')
        try:
            async with self.semaphore, asyncio.timeout(40):
                if cursor:
                    _, url = self.recall(cursor, 'page', source_id, query + '\0' + (section or ''))
                    method, data = 'GET', None
                elif section:
                    selected = next((item for item in source.sections if item.id == section), None)
                    if not selected:
                        raise SourceError('Seção não disponível nesta fonte')
                    url, method, data = self.url(source, selected.path), 'GET', None
                else:
                    if not query.strip():
                        raise SourceError('Digite uma pesquisa ou escolha uma seção')
                    url = self.url(source, source.search_path)
                    params = {**source.params, source.query_param: query}
                    method = source.method
                    data = params if method == 'POST' else None
                    if method == 'GET':
                        url = str(httpx.URL(url).copy_merge_params(params))
                response, body = await self.fetch(source, url, method=method, data=data)
                response.raise_for_status()
                soup = BeautifulSoup(body, 'html.parser')
                items = []
                for node in soup.select(source.item_selector)[:100]:
                    title = node.select_one(source.title_selector)
                    link = node.select_one(source.link_selector) if source.link_selector else title
                    if not title or not link or not link.get('href'):
                        continue
                    try:
                        target = self.url(source, link['href'], str(response.url))
                    except ValueError:
                        continue
                    description = node.select_one(source.description_selector) if source.description_selector else None
                    dates = {}
                    for key, selector in [('published', source.published_selector or 'time.published[datetime], [itemprop="datePublished"], meta[property="article:published_time"]'),
                                          ('modified', source.modified_selector or 'time.updated[datetime], [itemprop="dateModified"], meta[property="article:modified_time"]')]:
                        value = node.select_one(selector)
                        raw = (value.get('datetime') or value.get('content') or value.get_text(' ', strip=True)) if value else ''
                        try:
                            parsed = datetime.fromisoformat(raw.replace('Z', '+00:00')) if raw else None
                            dates[key] = (parsed.date().isoformat() if len(raw) == 10 else parsed.isoformat()) if parsed else None
                        except ValueError:
                            dates[key] = None
                    items.append({'title': title.get_text(' ', strip=True)[:500], 'url': target, **dates,
                        'description': description.get_text(' ', strip=True)[:600] if description else '',
                        'ref': self.remember('item', source_id, target)})
                next_node = soup.select_one(source.next_selector) if source.next_selector else None
                next_ref = None
                if next_node and next_node.get('href'):
                    try:
                        target = self.url(source, next_node['href'], str(response.url))
                        next_ref = self.remember('page', source_id, target, query + '\0' + (section or ''))
                    except ValueError:
                        pass
                log.debug('source=%s operation=search items=%d', source_id, len(items))
                return {'source': source_id, 'name': source.name, 'items': items, 'next': next_ref,
                        'status': 'ok', 'message': '' if items else 'Nenhum resultado extraível nesta página; a fonte pode ter mudado.'}
        except (httpx.HTTPError, OSError, ValueError, TimeoutError) as exc:
            log.debug('source=%s operation=search error=%s', source_id, type(exc).__name__)
            raise SourceError('Fonte indisponível ou resposta inválida; tente novamente') from exc

    async def downloads(self, ref):
        source_id, url = self.recall(ref, 'item')
        source = self.source(source_id)
        files, notices = [], []
        try:
            async with self.semaphore, asyncio.timeout(60):
                response, body = await self.fetch(source, url)
                response.raise_for_status()
                soup = BeautifulSoup(body, 'html.parser')
                candidates = soup.select(source.download_selector)
                seen = set()
                for node in candidates[:10]:
                    raw = node.get('href', '')
                    if raw.startswith('magnet:?'):
                        xt = parse_qs(urlsplit(raw).query).get('xt', [])
                        if len(raw) <= 8000 and any(re.fullmatch(r'urn:btih:(?:[0-9a-fA-F]{40}|[A-Z2-7a-z2-7]{32})', v) for v in xt):
                            files.append({'url': raw, 'kind': 'magnet', 'name': 'Abrir magnet no cliente torrent'})
                        continue
                    try:
                        target = self.url(source, raw, str(response.url))
                        if not raw or target in seen:
                            continue
                        seen.add(target)
                        final, _ = await self.fetch(source, target, method='HEAD', headers_only=True)
                        if final.status_code == 405 or (final.status_code == 200 and
                                'html' in final.headers.get('content-type', '').split(';')[0].lower()):
                            final, _ = await self.fetch(source, target, headers_only=True)
                        final.raise_for_status()
                        content_type = final.headers.get('content-type', '').split(';')[0].lower()
                        filename = urlsplit(str(final.url)).path.rsplit('/', 1)[-1]
                        attachment = 'attachment' in final.headers.get('content-disposition', '').lower()
                        binary = content_type.startswith(('application/', 'audio/')) and not any(
                            kind in content_type for kind in ('html', 'json', 'xml', 'javascript'))
                        if not binary or not (attachment or '.' in filename):
                            notices.append('Destino ainda é uma página externa ou arquivo não identificado; não exibido como download.')
                            continue
                        files.append({'url': str(final.url), 'name': filename or 'Arquivo da fonte',
                                      'kind': 'torrent' if filename.lower().endswith('.torrent') else 'arquivo'})
                    except (SourceError, ValueError, httpx.HTTPError) as exc:
                        notices.append(str(exc) if isinstance(exc, SourceError) else 'Link indisponível ou destino não permitido.')
                if not candidates:
                    notices.append('Nenhum link de download identificado; o layout pode ter mudado ou exigir acesso adicional.')
        except (httpx.HTTPError, OSError, ValueError, TimeoutError) as exc:
            raise SourceError('Não foi possível consultar os arquivos desta fonte') from exc
        return {'files': files, 'notices': list(dict.fromkeys(notices))}

    async def details(self, ref):
        from .details import extract_details
        source_id, url = self.recall(ref, 'item')
        source = self.source(source_id)
        try:
            async with self.semaphore, asyncio.timeout(40):
                response, body = await self.fetch(source, url)
                response.raise_for_status()
                result = extract_details(body, str(response.url), source.detail_selector)
                result.update({'source': source.name, 'source_url': str(response.url), 'ref': ref})
                for image in result['images']:
                    for key in ('url', 'thumbnail'):
                        target = str(public_url(image[key]))
                        token = self.remember('media', source_id, target)
                        image[key] = '/api/media/' + token
                return result
        except (httpx.HTTPError, OSError, ValueError, TimeoutError) as exc:
            raise SourceError('Não foi possível carregar os detalhes desta página') from exc

    async def media(self, ref):
        source_id, target = self.recall(ref, 'media')
        source = self.source(source_id)
        try:
            async with self.semaphore, asyncio.timeout(35):
                # Só URLs extraídas de um detalhe recebem referência; não há proxy de URL livre.
                media_source = source.model_copy(update={'hosts': list(set(source.hosts + [public_url(target).host]))})
                response, body = await self.fetch(media_source, target,
                    content_types=IMAGE_TYPES + ('text/html', 'application/xhtml+xml'), max_bytes=8_000_000)
                response.raise_for_status()
                mime = response.headers['content-type'].split(';')[0].strip().lower()
                if mime not in IMAGE_TYPES:
                    if len(body) > MAX_BYTES:
                        raise SourceError('Página do hospedeiro excedeu o limite de tamanho')
                    soup = BeautifulSoup(body, 'html.parser')
                    image = (soup.select_one('img[src*="/big/"], img#image, img#img')
                             or soup.select_one('meta[property="og:image"]'))
                    if not image:
                        raise SourceError('A origem não disponibilizou uma imagem original verificável')
                    target = str(public_url(urljoin(str(response.url), image.get('content') or image.get('src', ''))))
                    media_source = source.model_copy(update={'hosts': list(set(source.hosts + [public_url(target).host]))})
                    response, body = await self.fetch(media_source, target, content_types=IMAGE_TYPES, max_bytes=8_000_000)
                    response.raise_for_status()
                return body, response.headers['content-type'].split(';')[0].strip().lower()
        except (httpx.HTTPError, OSError, ValueError, TimeoutError) as exc:
            raise SourceError('Não foi possível carregar esta imagem da origem') from exc
