import json
import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from vstworld.app import create_app
from test_catalog import PAGE, source


class SourceEditorTests(unittest.TestCase):
    def setUp(self):
        self.directory = self.enterContext(tempfile.TemporaryDirectory())
        self.path = Path(self.directory) / 'sources.json'
        self.initial = [source().model_dump()]
        self.path.write_text(json.dumps(self.initial), encoding='utf-8')
        def handler(req):
            return httpx.Response(404) if req.url.path == '/robots.txt' else httpx.Response(200, text=PAGE)
        self.app = create_app(self.path, httpx.MockTransport(handler))
        self.client = self.enterContext(TestClient(self.app))

    def snapshot(self):
        response = self.client.get('/api/source-config')
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_create_edit_delete_and_reload_without_restart(self):
        self.assertEqual(self.client.get('/sources').status_code, 200)
        data = self.snapshot()
        data['sources'].append(source(id='new', name='Nova').model_dump())
        saved = self.client.post('/api/source-config', json=data)
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertEqual(len(json.loads(self.path.read_text(encoding='utf-8'))), 2)
        self.assertEqual(len(self.client.get('/api/sources').json()), 2)
        self.assertEqual(self.client.post('/api/search', json={'source': 'new', 'query': 'A'}).json()['status'], 'ok')
        data = saved.json()
        data['sources'][1]['enabled'] = False
        saved = self.client.post('/api/source-config', json=data)
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(self.client.post('/api/search', json={'source': 'new', 'query': 'A'}).json()['status'], 'error')
        data = saved.json()
        data['sources'] = []
        self.assertEqual(self.client.post('/api/source-config', json=data).status_code, 200)
        self.assertEqual(self.client.get('/api/sources').json(), [])
        with TestClient(create_app(self.path, httpx.MockTransport(lambda req: httpx.Response(404)))) as restarted:
            self.assertEqual(restarted.get('/api/sources').json(), [])

    def test_invalid_config_and_stale_revision_do_not_overwrite(self):
        data = self.snapshot()
        old_bytes = self.path.read_bytes()
        invalid = {**data, 'sources': [source().model_dump(), source().model_dump()]}
        self.assertEqual(self.client.post('/api/source-config', json=invalid).status_code, 422)
        self.assertEqual(self.path.read_bytes(), old_bytes)
        invalid['sources'] = [{**source().model_dump(), 'item_selector': '['}]
        self.assertEqual(self.client.post('/api/source-config', json=invalid).status_code, 422)
        self.assertEqual(self.path.read_bytes(), old_bytes)
        self.path.write_text('[]', encoding='utf-8')
        self.assertEqual(self.client.post('/api/source-config', json=data).status_code, 409)
        self.assertEqual(self.path.read_text(), '[]')

    def test_disk_failure_preserves_config_and_runtime(self):
        data = self.snapshot()
        data['sources'] = []
        with patch('vstworld.config.os.replace', side_effect=PermissionError('read only')):
            response = self.client.post('/api/source-config', json=data)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(len(json.loads(self.path.read_text())), 1)
        self.assertEqual(len(self.client.get('/api/sources').json()), 1)

    def test_test_unsaved_source_without_persistence(self):
        response = self.client.post('/api/source-test', json={'source': source(id='draft', enabled=False).model_dump(), 'query': 'A'})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['count'], 1)
        self.assertEqual(self.snapshot()['sources'], self.initial)
        self.assertNotIn('ref', response.json()['items'][0])

    def test_editor_rejects_cross_origin_save_and_private_source(self):
        data = self.snapshot()
        self.assertEqual(self.client.post('/api/source-config', json=data, headers={'origin': 'https://evil.example'}).status_code, 403)
        data['sources'][0]['base_url'] = 'https://127.0.0.1/'
        self.assertEqual(self.client.post('/api/source-config', json=data).status_code, 422)

    def test_custom_config_seed_is_created_once(self):
        target = Path(self.directory) / 'data' / 'sources.json'
        with patch.dict('os.environ', {'VSTWORLD_SOURCES': str(target)}):
            create_app()
            self.assertTrue(target.exists())
            target.write_text('[]', encoding='utf-8')
            create_app()
            self.assertEqual(target.read_text(), '[]')


class LiveConfigTests(unittest.IsolatedAsyncioTestCase):
    async def test_save_does_not_close_client_used_by_active_search(self):
        entered, release = asyncio.Event(), asyncio.Event()
        async def handler(req):
            if req.url.path == '/robots.txt':
                return httpx.Response(404)
            entered.set()
            await release.wait()
            return httpx.Response(200, text=PAGE)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'sources.json'
            path.write_text(json.dumps([source().model_dump()]), encoding='utf-8')
            app = create_app(path, httpx.MockTransport(handler))
            async with app.router.lifespan_context(app):
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url='http://testserver') as client:
                    old = app.state.catalog
                    snapshot = (await client.get('/api/source-config')).json()
                    task = asyncio.create_task(client.post('/api/search', json={'source': 'test', 'query': 'A'}))
                    await entered.wait()
                    try:
                        result = await client.post('/api/source-config', json={**snapshot, 'sources': []})
                        self.assertEqual(result.status_code, 200)
                        self.assertFalse(old.client.is_closed)
                    finally:
                        release.set()
                        response = await task
                    self.assertEqual(response.json()['status'], 'ok')
                    self.assertTrue(old.client.is_closed)
