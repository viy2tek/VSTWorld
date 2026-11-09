"""Extract source facts and instructions as text; never execute source HTML."""
import re
from urllib.parse import parse_qs, urljoin, urlsplit

from bs4 import BeautifulSoup, Comment, NavigableString

from .http import public_url


FACT = re.compile(r'^(дата\s+выпуска|год\s+выпуска|версия|разработчик|издатель|'
    r'сайт\s+разработчика|формат(?:ы)?|разрядность|табл[еэ]тка|системные\s+требования|'
    r'операционная\s+система|платформа|размер|язык\s+интерфейса|release(?:\s+date)?|'
    r'version|developer|publisher|developer\s+(?:website|site)|format(?:s)?|bitness|'
    r'architecture|system\s+requirements|requirements|operating\s+system|os|platform|'
    r'size|language|data\s+de\s+lançamento|versão|desenvolvedor(?:a)?|distribuidora|'
    r'site\s+do\s+desenvolvedor|formato(?:s)?|profundidade\s+de\s+bits|arquitetura|'
    r'requisitos\s+do\s+sistema|tamanho)\s*:\s*(.*)$', re.I)
REQUIREMENT_LINE = re.compile(r'^(?:(?:OS|RAM|CPU|GPU|DAW|memory|processor|disk|storage|'
    r'operating\s+system|memória|processador|espaço\s+em\s+disco|ОС|процессор|'
    r'оперативная\s+память)\s*:|Windows\s+\d|macOS\b|Mac\s+OS\b|Linux\b|'
    r'(?:DirectX|OpenGL|Cubase)\s+\d)', re.I)
INSTALL = re.compile(r'установк|инсталляц|installation|install\s+(?:guide|instructions)|instalação', re.I)
GALLERY = re.compile(r'скриншот|screenshots?|галерея|gallery', re.I)


def clean(value, limit=8000):
    return re.sub(r'\s+', ' ', value).strip()[:limit]


def safe_url(value, page_url):
    if not isinstance(value, str) or not value.strip() or len(value) > 4096:
        return None
    try:
        return str(public_url(urljoin(page_url, value.strip())))
    except ValueError:
        return None


def text_blocks(node, page_url):
    blocks, parts, links = [], [], []

    def flush():
        text = '\n'.join(clean(line) for line in ''.join(parts).split('\n')).strip()[:8000]
        if text and len(blocks) < 100:
            blocks.append({'kind': 'paragraph', 'text': text, 'links': links[:]})
        parts.clear()
        links.clear()

    def add_links(element):
        for anchor in element.select('a[href]')[:50]:
            url = safe_url(anchor.get('href'), page_url)
            link = {'label': clean(anchor.get_text(' ', strip=True), 500), 'url': url}
            if url and link not in links and len(links) < 30:
                links.append(link)

    def walk(element, depth=0):
        if depth > 100:
            return
        if isinstance(element, Comment):
            return
        if isinstance(element, NavigableString):
            parts.append(re.sub(r'\s+', ' ', str(element)))
            return
        if element.name in ('script', 'style', 'iframe', 'input', 'button', 'noscript', 'summary', 'img'):
            return
        if element.name == 'br':
            if ''.join(parts).rstrip(' \t').endswith('\n'):
                flush()
            else:
                parts.append('\n')
            return
        if element.name in ('ol', 'ul'):
            flush()
            items = []
            try:
                number = int(element.get('start', 1))
            except (ValueError, TypeError):
                number = 1
            for li in element.find_all('li', recursive=False)[:100]:
                try:
                    number = int(li.get('value', number))
                except (ValueError, TypeError):
                    pass
                text = clean(li.get_text(' ', strip=True))
                if text:
                    items.append(((f'{number}. ' if element.name == 'ol' else '• ') + text)[:8000])
                number += 1
                add_links(li)
            if items and len(blocks) < 100:
                blocks.append({'kind': 'list', 'items': items, 'links': links[:]})
            links.clear()
            return
        boundary = element.name in ('p', 'div', 'section', 'h2', 'h3', 'h4', 'pre', 'blockquote', 'tr')
        if boundary:
            flush()
        if element.name == 'a':
            url = safe_url(element.get('href'), page_url)
            link = {'label': clean(element.get_text(' ', strip=True), 500), 'url': url}
            if url and link not in links and len(links) < 30:
                links.append(link)
        for child in element.children:
            walk(child, depth + 1)
        if boundary:
            flush()

    walk(node)
    flush()
    return blocks


def extract_page_dates(node):
    dates = {'published': None, 'modified': None}
    for kind, selectors in {
        'published': 'meta[property="article:published_time"], [itemprop="datePublished"], time.published',
        'modified': 'meta[property="article:modified_time"], [itemprop="dateModified"], time.updated',
    }.items():
        element = node.select_one(selectors)
        if element:
            value = element.get('content') or element.get('datetime') or element.get_text(' ', strip=True)
            if re.fullmatch(r'\d{4}-\d{2}-\d{2}(?:[T ][\d:.+Z-]+)?', value.strip()):
                dates[kind] = value.strip()[:100]
    return dates


def youtube_id(value):
    try:
        url = urlsplit(value)
        if url.scheme not in ('http', 'https') or url.username or url.password:
            return None
        host = (url.hostname or '').lower()
        if host in ('youtu.be', 'www.youtu.be'):
            candidate = url.path.strip('/').split('/')[0]
        elif host in ('youtube.com', 'www.youtube.com', 'm.youtube.com', 'youtube-nocookie.com', 'www.youtube-nocookie.com'):
            parts = url.path.strip('/').split('/')
            candidate = parts[1] if len(parts) == 2 and parts[0] in ('embed', 'shorts', 'v') else parse_qs(url.query).get('v', [''])[0]
        else:
            return None
        return candidate if re.fullmatch(r'[A-Za-z0-9_-]{11}', candidate) else None
    except ValueError:
        return None


def extract_details(body: bytes, page_url: str, selector: str | None = None) -> dict:
    soup = BeautifulSoup(body[:2_000_000], 'html.parser')
    title = soup.select_one('.eTitle, h1')
    result = {'title': clean(title.get_text(' ', strip=True), 500) if title else '',
        'metadata': [], 'installation': [], 'videos': [], 'images': [],
        'dates': extract_page_dates(soup), 'notices': []}
    content = soup.select_one(selector or '.eText, [itemprop="articleBody"], .entry-content, article')
    if content is None:
        result['notices'].append('Conteúdo do item não identificado; o layout da fonte pode ter mudado.')
        return result
    for unwanted in content.select('.comments, .comment, .ads, .advertisement, [caramel-id], .uSpoilerButBl script'):
        unwanted.decompose()
    for heading in list(content.select('.title_spoiler'))[:30]:
        inner = heading.find_next_sibling()
        if inner is not None and 'text_spoiler' in inner.get('class', []):
            section, summary = soup.new_tag('details'), soup.new_tag('summary')
            summary.string = heading.get_text(' ', strip=True)
            heading.insert_before(section)
            section.append(summary)
            section.append(inner.extract())
            heading.decompose()
    candidates = []
    for node in content.select('iframe[src], a[href], script')[:500]:
        if node.name == 'script':
            candidates.extend(re.findall(r'https?://[^\s\'"<>\\]+', node.get_text()))
        else:
            candidates.append(node.get('src') or node.get('href'))
    for candidate in candidates:
        video = youtube_id(candidate)
        if video and {'id': video} not in result['videos'] and len(result['videos']) < 20:
            result['videos'].append({'id': video})

    seen_instructions, seen_images = set(), set()
    for section in content.select('.uSpoilerClosed, .uSpoilerOpened, details, .gallery, .screenshots')[:100]:
        button = section.select_one('.uSpoilerButton, summary')
        heading = clean((button.get('value') or button.get_text(' ', strip=True)) if button else '')
        heading = re.sub(r'^\[[^\]]*\]\s*', '', heading)[:200]
        inner = section.select_one('.uSpoilerText') or section
        installation = INSTALL.search(heading)
        # shortcut: generic team titles need explicit numbered installation steps; add source-specific evidence for other layouts.
        if not installation and re.search(r'team\s+v\.?r', heading, re.I):
            installation = re.search(r'(?:\b\d[.)]?\s+)(?:Установите|Запустите|Install|Run)\b', inner.get_text(' ', strip=True), re.I)
        if installation:
            blocks = text_blocks(inner, page_url)
            signature = str(blocks)
            if blocks and signature not in seen_instructions and len(result['installation']) < 10:
                seen_instructions.add(signature)
                result['installation'].append({'title': heading, 'blocks': blocks})
        if GALLERY.search(heading) or set(section.get('class', [])) & {'gallery', 'screenshots'}:
            for image in inner.select('img')[:100]:
                thumbnail = safe_url(image.get('src') or image.get('data-src'), page_url)
                if not thumbnail or thumbnail in seen_images or len(result['images']) >= 40:
                    continue
                seen_images.add(thumbnail)
                anchor = image.find_parent('a')
                target = None
                if anchor and anchor in inner.descendants:
                    target = safe_url(anchor.get('title'), page_url) if str(anchor.get('title', '')).startswith('https://') else None
                    target = target or safe_url(anchor.get('href'), page_url)
                direct = bool(target and re.search(r'\.(?:jpe?g|png|webp|gif|avif)$', urlsplit(target).path, re.I))
                result['images'].append({'thumbnail': thumbnail, 'url': target or thumbnail,
                    'original_available': direct})

    for node in content.select('.uSpoilerClosed, .uSpoilerOpened, details, script, style, .gallery, .screenshots'):
        node.decompose()
    for image in content.select('img.plugin-main-img[src]')[:5]:
        target = safe_url(image.get('src'), page_url)
        if target and target not in seen_images:
            seen_images.add(target)
            result['images'].append({'thumbnail':target, 'url':target, 'original_available':False})
    for group in content.select('.label-group')[:20]:
        label = group.select_one('.label-prefix')
        if label is None:
            continue
        key = clean(label.get_text(' ', strip=True)).rstrip(' :').casefold()
        name = {'system':'Operating system', 'format':'Format'}.get(key)
        value = clean(' '.join(child.get_text(' ', strip=True) for child in group.find_all(recursive=False) if child is not label))
        if name and value:
            result['metadata'].append({'label':name, 'value':value})
    seen_facts = {(field['label'].casefold(), field['value']) for field in result['metadata']}
    for block in text_blocks(content, page_url):
        current = None
        for line in block.get('text', '').splitlines():
            match = FACT.match(line)
            if match:
                label, value = match.groups()
                key = (label.casefold(), value)
                current = None
                if value and key not in seen_facts and len(result['metadata']) < 40:
                    seen_facts.add(key)
                    current = {'label': label[:100], 'value': value[:4000]}
                    result['metadata'].append(current)
            elif (current and re.search(r'требования|requirements|requisitos', current['label'], re.I)
                    and REQUIREMENT_LINE.match(line)):
                current['value'] = (current['value'] + '\n' + line)[:4000]
            else:
                current = None
    if any(not image['original_available'] for image in result['images']):
        result['notices'].append('Algumas imagens oferecem apenas miniatura ou página do hospedeiro; o original ainda não foi confirmado.')
    if not result['installation']:
        result['notices'].append('Nenhuma seção de instalação identificada nesta página.')
    return result
