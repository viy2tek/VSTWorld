import json
import hashlib
import os
import tempfile
from pathlib import Path
from typing import Literal
from urllib.parse import urljoin

import soupsieve
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .http import public_url


class Section(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str = Field(pattern=r'^[a-z0-9_-]{1,50}$')
    name: str = Field(min_length=1, max_length=80)
    path: str


class Source(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str = Field(pattern=r'^[a-z0-9_-]{1,50}$')
    name: str = Field(min_length=1, max_length=80)
    enabled: bool = True
    respect_robots: bool = True
    base_url: str
    hosts: list[str] = Field(min_length=1, max_length=20)
    search_path: str
    method: Literal['GET', 'POST'] = 'GET'
    query_param: str = 'q'
    params: dict[str, str] = Field(default_factory=dict)
    max_query: int = Field(default=200, ge=1, le=500)
    item_selector: str = Field(min_length=1, max_length=2000)
    title_selector: str = Field(min_length=1, max_length=2000)
    link_selector: str | None = None
    description_selector: str | None = None
    next_selector: str | None = None
    download_selector: str = Field(min_length=1, max_length=2000)
    detail_selector: str | None = None
    published_selector: str | None = None
    modified_selector: str | None = None
    interval: float = Field(default=1.0, ge=0, le=60)
    sections: list[Section] = Field(default_factory=list, max_length=30)
    note: str = Field(default='', max_length=1000)

    @model_validator(mode='after')
    def validate_source(self):
        base = public_url(self.base_url)
        if base.host not in self.hosts:
            raise ValueError('O domínio base precisa constar em hosts')
        for host in self.hosts:
            if public_url(f'https://{host}/').host != host:
                raise ValueError('hosts deve conter nomes exatos em minúsculas, sem URL/porta')
        for selector in (self.item_selector, self.title_selector, self.link_selector,
                         self.description_selector, self.next_selector, self.download_selector,
                         self.detail_selector, self.published_selector, self.modified_selector):
            if selector:
                try:
                    soupsieve.compile(selector)
                except soupsieve.SelectorSyntaxError as exc:
                    raise ValueError('Seletor CSS inválido') from exc
        for path in [self.search_path, *(section.path for section in self.sections)]:
            if public_url(urljoin(self.base_url, path)).host not in self.hosts:
                raise ValueError('Caminho fora dos domínios permitidos')
        if len({section.id for section in self.sections}) != len(self.sections):
            raise ValueError('Seções duplicadas')
        return self


def validate_sources(raw) -> list[Source]:
    if not isinstance(raw, list) or len(raw) > 30:
        raise ValueError('sources.json deve conter uma lista com até 30 fontes')
    sources = [Source.model_validate(item) for item in raw]
    if len({source.id for source in sources}) != len(sources):
        raise ValueError('IDs de fontes duplicados')
    return sources


def load_sources(path: Path) -> list[Source]:
    return validate_sources(json.loads(Path(path).read_text(encoding='utf-8-sig')))


class ConfigConflict(Exception):
    pass


def source_snapshot(path: Path):
    content = path.read_bytes()
    sources = validate_sources(json.loads(content.decode('utf-8-sig')))
    return {'revision': hashlib.sha256(content).hexdigest(),
            'sources': [source.model_dump() for source in sources]}


def save_sources(path: Path, sources: list[Source], revision: str):
    if hashlib.sha256(path.read_bytes()).hexdigest() != revision:
        raise ConfigConflict('As fontes mudaram em outra aba ou no arquivo. Recarregue antes de salvar.')
    content = (json.dumps([source.model_dump() for source in sources], ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.sources-', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {'revision': hashlib.sha256(content).hexdigest(),
            'sources': [source.model_dump() for source in sources]}
