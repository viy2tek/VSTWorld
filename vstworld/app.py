import os
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, model_validator
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .catalog import Catalog, SourceError
from .config import Source, ConfigConflict, load_sources, source_snapshot, save_sources, validate_sources
from . import __version__

ROOT = Path(__file__).resolve().parent.parent
STATIC = Path(__file__).resolve().parent / 'static'


class Search(BaseModel):
    model_config = ConfigDict(extra='forbid')
    source: str = Field(pattern=r'^[a-z0-9_-]{1,50}$')
    query: str = Field(default='', max_length=500)
    cursor: str | None = Field(default=None, pattern=r'^[A-Za-z0-9_-]{32}$')
    section: str | None = Field(default=None, pattern=r'^[a-z0-9_-]{1,50}$')


class Files(BaseModel):
    model_config = ConfigDict(extra='forbid')
    ref: str = Field(pattern=r'^[A-Za-z0-9_-]{32}$')


class SourceConfig(BaseModel):
    model_config = ConfigDict(extra='forbid')
    revision: str = Field(pattern=r'^[a-f0-9]{64}$')
    sources: list[Source] = Field(max_length=30)

    @model_validator(mode='after')
    def unique_ids(self):
        validate_sources([source.model_dump() for source in self.sources])
        return self


class SourceTest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    source: Source
    query: str = Field(default='', max_length=500)
    section: str | None = Field(default=None, pattern=r'^[a-z0-9_-]{1,50}$')


class DetectSource(BaseModel):
    model_config = ConfigDict(extra='forbid')
    url: str = Field(min_length=1, max_length=2000)


class AIDetectSource(DetectSource):
    model: str = Field(default='qwen3.5:4b', min_length=1, max_length=120)


def create_app(config_path=None, transport=None):
    configured_path = os.getenv('VSTWORLD_SOURCES') or os.getenv('VSTHOUSE_SOURCES')
    path = Path(config_path or configured_path or ROOT / 'sources.json').resolve()
    if config_path is None and configured_path and not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write((ROOT / 'sources.json').read_bytes())
    sources = load_sources(path)

    @asynccontextmanager
    async def lifespan(app):
        app.state.catalog = Catalog(sources, transport=transport)
        app.state.inflight = {app.state.catalog: 0}
        app.state.config_lock = asyncio.Lock()
        yield
        await app.state.catalog.close()

    @asynccontextmanager
    async def use_catalog(app):
        catalog = app.state.catalog
        app.state.inflight[catalog] += 1
        try:
            yield catalog
        finally:
            app.state.inflight[catalog] -= 1
            if catalog is not app.state.catalog and app.state.inflight[catalog] == 0:
                del app.state.inflight[catalog]
                await catalog.close()

    app = FastAPI(title='VSTWorld', version=__version__, lifespan=lifespan)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=[
        '127.0.0.1', 'localhost', 'testserver',
        *filter(None, (os.getenv('VSTWORLD_ALLOWED_HOSTS') or os.getenv('VSTHOUSE_ALLOWED_HOSTS', '')).split(','))])

    @app.middleware('http')
    async def security_headers(request: Request, call_next):
        origin = request.headers.get('origin')
        if request.method == 'POST' and origin and urlsplit(origin).netloc != request.url.netloc:
            return JSONResponse({'detail': 'Origem não permitida'}, status_code=403)
        response = await call_next(request)
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; "
            "connect-src 'self'; frame-src https://www.youtube-nocookie.com; object-src 'none'; "
            "base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Cache-Control'] = 'no-store'
        return response

    @app.get('/api/health')
    async def health():
        return {'status': 'ok', 'app': 'VSTWorld', 'version': __version__}

    @app.get('/api/sources')
    async def source_list():
        return [{'id': s.id, 'name': s.name, 'enabled': s.enabled, 'max_query': s.max_query,
                 'note': s.note, 'sections': [section.model_dump(exclude={'path'}) for section in s.sections]}
                for s in app.state.catalog.sources.values()]

    @app.get('/api/source-presets')
    async def source_presets():
        return [source.model_dump() for source in load_sources(Path(__file__).with_name('presets.json'))]

    @app.get('/api/source-config')
    async def get_source_config():
        try:
            return await asyncio.to_thread(source_snapshot, path)
        except (OSError, ValueError):
            raise HTTPException(503, 'Não foi possível ler a configuração. Verifique o arquivo e as permissões.') from None

    @app.post('/api/source-config')
    async def update_source_config(body: SourceConfig):
        async with app.state.config_lock:
            replacement = Catalog(body.sources, transport=transport)
            try:
                snapshot = await asyncio.to_thread(save_sources, path, body.sources, body.revision)
            except (OSError, ConfigConflict) as exc:
                await replacement.close()
                raise HTTPException(409 if isinstance(exc, ConfigConflict) else 503,
                    str(exc) if isinstance(exc, ConfigConflict) else
                    'Não foi possível salvar. Verifique se a pasta da configuração permite escrita.') from None
            old = app.state.catalog
            app.state.catalog = replacement
            app.state.inflight[replacement] = 0
            if app.state.inflight[old] == 0:
                del app.state.inflight[old]
                await old.close()
            return snapshot

    @app.post('/api/source-test')
    async def test_source(body: SourceTest):
        catalog = Catalog([body.source.model_copy(update={'enabled': True})], transport=transport)
        try:
            result = await catalog.search(body.source.id, body.query, section=body.section)
            return {'status': result['status'], 'message': result['message'], 'count': len(result['items']),
                    'has_next': bool(result['next']), 'items': [
                        {'title': item['title'], 'url': item['url']} for item in result['items'][:5]]}
        except SourceError as exc:
            return {'status': 'error', 'message': str(exc), 'count': 0, 'has_next': False, 'items': []}
        finally:
            await catalog.close()

    @app.post('/api/source-detect')
    async def detect_source_config(body: DetectSource):
        from .discovery import detect_source
        return await detect_source(body.url, list(app.state.catalog.sources.values()), transport=transport)

    @app.post('/api/source-detect-ai')
    async def detect_source_ai(body: AIDetectSource):
        from .local_ai import detect_with_ai
        return await detect_with_ai(body.url, list(app.state.catalog.sources.values()), body.model, transport=transport)

    @app.post('/api/search')
    async def search(body: Search, request: Request):
        async with use_catalog(request.app) as catalog:
            try:
                return await catalog.search(body.source, body.query, body.cursor, body.section)
            except SourceError as exc:
                source = catalog.sources.get(body.source)
                return {'source': body.source, 'name': source.name if source else body.source,
                        'status': 'error', 'message': str(exc), 'items': [], 'next': None}

    @app.post('/api/files')
    async def files(body: Files, request: Request):
        async with use_catalog(request.app) as catalog:
            try:
                return await catalog.downloads(body.ref)
            except SourceError as exc:
                raise HTTPException(422, str(exc)) from exc

    @app.get('/sources')
    async def source_editor():
        return FileResponse(STATIC / 'sources.html')

    @app.post('/api/details')
    async def item_details(body: Files, request: Request):
        async with use_catalog(request.app) as catalog:
            try:
                return await catalog.details(body.ref)
            except SourceError as exc:
                raise HTTPException(422, str(exc)) from exc

    @app.get('/api/media/{ref}')
    async def item_image(ref: str, request: Request):
        if len(ref) != 32:
            raise HTTPException(404, 'Imagem não encontrada')
        async with use_catalog(request.app) as catalog:
            try:
                content, mime = await catalog.media(ref)
                return Response(content, media_type=mime)
            except SourceError as exc:
                raise HTTPException(422, str(exc)) from exc

    @app.get('/item/{ref}')
    async def item_page(ref: str):
        return FileResponse(STATIC / 'item.html')

    @app.get('/')
    async def home():
        return FileResponse(STATIC / 'index.html')

    app.mount('/static', StaticFiles(directory=STATIC), name='static')
    return app
