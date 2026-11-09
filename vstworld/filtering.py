"""Conservative filter facts: unknown values stay empty."""
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict

from .details import FACT


class NativeFilters(BaseModel):
    model_config = ConfigDict(extra='forbid')
    system: Literal['', 'windows', 'macos', 'linux'] = ''
    architecture: Literal['', '32', '64'] = ''
    format: Literal['', 'vst', 'vst2', 'vst3', 'au', 'aax', 'kontakt'] = ''


def native_params(source, filters):
    params, applied = {}, []
    if (source.method != 'GET' or source.base_url.rstrip('/') != 'https://plugins4free.com'
            or source.search_path != '/search'):
        return params, applied
    if filters.system:
        params['os[]'] = {'windows': ['win' + filters.architecture] if filters.architecture else ['win32', 'win64'],
                          'macos': ['allmacos'], 'linux': ['linux']}[filters.system]
        applied.append('system')
        if filters.system == 'windows' and filters.architecture:
            applied.append('architecture')
    if filters.format in ('vst', 'vst2', 'vst3', 'au', 'aax'):
        params['fmt[]'] = 'vst' if filters.format.startswith('vst') else filters.format
        applied.append('format')
    return params, applied


# Use the same fact vocabulary as the details view, including inline listing facts.
INLINE_FACT = re.compile(FACT.pattern.replace('^', '', 1).rsplit('(.*)$', 1)[0], re.I)
SYSTEM = re.compile(r'\b(?:windows|win(?:dows)?\s*(?:32|64)?|mac\s*os\s*x?|macos|os\s*x|osx|mac|linux)\b', re.I)
ARCH = re.compile(r'\b(?:x86[_-](64)|(?:amd|aarch|arm)(64)|x(32|64|86)|(?:win|windows)\s*(32|64)|(32|64)\s*[- ]?\s*bits?|(32|64)\s*[- ]?\s*разряд\w*)\b', re.I)
FORMAT = re.compile(r'\b(?:vst\s*i?\s*([23])|vsti?|au|aax|kontakt)\b', re.I)


def inline_facts(text):
    matches = list(INLINE_FACT.finditer(text))
    for index, match in enumerate(matches):
        value = text[match.end():matches[index + 1].start() if index + 1 < len(matches) else len(text)]
        value = re.split(r'…|\.{3}|[\r\n]', value.lstrip(), maxsplit=1)[0].strip(' ;|')
        if value:
            yield {'label': match[1], 'value': value[:4000]}


def extract_filters(node, title='', metadata=None, section=None):
    result = {'system': [], 'format': [], 'architecture': [], 'kind': [],
              'developer': '', 'version': '', 'targets': []}
    facts = list(metadata or [])
    if node is not None:
        for message in node.select('.eMessage') or [node]:
            # Lines keep the last inline value from absorbing the following paragraph.
            facts.extend(inline_facts(message.get_text('\n', strip=True).replace('\n:', ':')))
        for labels, name in [('.os-label', 'Operating system'), ('.fmt-label', 'Format')]:
            facts.extend({'label': name, 'value': el.get_text(' ', strip=True)} for el in node.select(labels))
        developer = node.select_one('.dev-name')
        if developer:
            result['developer'] = developer.get_text(' ', strip=True)[:200]

    def add(key, value):
        if value not in result[key]:
            result[key].append(value)

    def architecture(match):
        value = next(value for value in match.groups() if value)
        return '32' if value == '86' else value

    def technical(text, kinds=False, formats=True, bits=True):
        architectures = [architecture(match) for match in ARCH.finditer(text)] if bits else []
        for value in architectures:
            add('architecture', value)
        systems = list(SYSTEM.finditer(text))
        for index, match in enumerate(systems):
            token = re.sub(r'\s+', '', match[0].lower())
            system = 'windows' if token.startswith('win') else 'linux' if token == 'linux' else 'macos'
            add('system', system)
            segment = text[match.start():systems[index + 1].start() if index + 1 < len(systems) else len(text)]
            local_arch = [architecture(found) for found in ARCH.finditer(segment)] if bits else []
            if not local_arch and len(systems) == 1:
                local_arch = architectures
            for bits in local_arch or [None]:
                add('targets', {'system': system, 'architecture': bits})
        for match in FORMAT.finditer(text) if formats else []:
            token = re.sub(r'\s+', '', match[0].lower())
            add('format', 'vst' + match[1] if match[1] else 'vst' if token == 'vsti' else token)
        if formats and re.search(r'\bvsti?\s*2\s*/\s*3\b', text, re.I):
            add('format', 'vst3')
        if (formats and re.search(r'\bvsti\s*[23]?\b', text, re.I)) or (kinds and re.search(r'\binstruments?\b|\bинструмент\w*', text, re.I)):
            add('kind', 'instrument')
        for kind, pattern in [('effect', r'\beffects?\b|\bэффект\w*'), ('samples', r'\bsamples\b|\bsample\s+(?:pack|library|libraries|collection)\b|\bс[эе]мпл(?:ы|ов)\b'),
                              ('presets', r'\bpresets\b|\bpreset\s+(?:pack|bank|collection)\b|\bпресеты\b'), ('software', r'\bDAW\b|\bsoftware\b')]:
            if kinds and re.search(pattern, text, re.I):
                add('kind', kind)

    technical(title, kinds=True)
    for fact in facts:
        label, value = fact['label'].strip().casefold(), fact['value'].strip()
        # Metadata from older detail extraction can contain several labels on one line.
        nested = list(inline_facts(fact['label'] + ': ' + value))
        if nested:
            label, value = nested[0]['label'].strip().casefold(), nested[0]['value']
        if re.fullmatch(r'developer|разработчик|desenvolvedor(?:a)?', label):
            result['developer'] = value[:200]
        elif re.fullmatch(r'version|версия|versão', label):
            result['version'] = value[:100]
        elif re.search(r'format|формат|operating|system|requirements|платформа|систем|операцион|platform|bitness|architecture|разряд|arquitetura|bits|requisitos|^os$', label):
            if re.search(r'bitness|architecture|разряд|arquitetura|bits', label) and re.fullmatch(r'32|64', value):
                value += ' bit'
            technical(value, formats=bool(re.search(r'format|формат', label)),
                      bits=not bool(re.search(r'requirements|requisitos|требования', label)))
    if not result['version']:
        version = re.search(r'\bv(?:ersion)?\.?\s*(\d+(?:\.\d+)+(?:[a-z]\d*)?)\b', title, re.I)
        if version:
            result['version'] = version[1]
    if section in ('vsti', 'apps', 'hosts'):
        add('kind', 'instrument' if section == 'vsti' else 'software')
    if len(result['system']) == 1 and len(result['architecture']) == 1:
        result['targets'] = [{'system': result['system'][0], 'architecture': result['architecture'][0]}]
    return result
