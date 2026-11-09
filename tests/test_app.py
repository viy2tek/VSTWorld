import json
import tempfile
import unittest
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

from vstworld.app import create_app
from test_catalog import PAGE, source


class AppTests(unittest.TestCase):
    def test_included_sources_and_optional_ai_rejections(self):
        presets = self.client.get('/api/source-presets').json()
        self.assertEqual(presets[0]['id'], 'vsthouse')
        self.assertTrue(any(s['id'] == 'plugins4free' and s['download_adapter'] == 'plugins4free' for s in presets))
        self.assertTrue(any(s['id'] == 'musicmakers' and not s['enabled'] for s in presets))
        for body in [{'url':'https://127.0.0.1/'}, {'url':'https://new.example.org/', 'model':'test:cloud'}]:
            response = self.client.post('/api/source-detect-ai', json=body)
            self.assertEqual(response.status_code, 200)
            self.assertIsNone(response.json()['source'])
        self.assertEqual(self.client.post('/api/source-detect-ai', json={'url':'https://example.org/'},
            headers={'origin':'https://evil.example'}).status_code, 403)
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        config = Path(self.directory.name) / 'sources.json'
        config.write_text(json.dumps([source().model_dump(), source(id='other', name='Other').model_dump()]), encoding='utf-8')
        def handler(req):
            if req.url.path == '/robots.txt':
                return httpx.Response(404)
            if req.url.params.get('q') == 'fail':
                return httpx.Response(503)
            return httpx.Response(200, text=PAGE)
        self.client = self.enterContext(TestClient(create_app(config, httpx.MockTransport(handler))))

    def test_app_and_source_list(self):
        home = self.client.get('/')
        self.assertEqual(home.status_code, 200)
        self.assertIn('VSTWorld', home.text)
        self.assertIn("default-src 'self'", home.headers['content-security-policy'])
        self.assertEqual(len(self.client.get('/api/sources').json()), 2)

    def test_search_error_isolated_and_input_validation(self):
        first = self.client.post('/api/search', json={'source': 'test', 'query': 'fail'})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()['status'], 'error')
        second = self.client.post('/api/search', json={'source': 'other', 'query': 'A&B'})
        self.assertEqual(second.json()['items'][0]['title'], 'A & B')
        self.assertEqual(self.client.post('/api/search', json={'source': 'test', 'query': '', 'url': 'https://localhost/'}).status_code, 422)
        self.assertEqual(self.client.post('/api/files', json={'ref': 'fake'}).status_code, 422)
        self.assertEqual(self.client.post('/api/search', json={'source': 'test', 'query': 'x'}, headers={'origin': 'https://evil.example'}).status_code, 403)

    def test_cursor_bound_to_query(self):
        result = self.client.post('/api/search', json={'source': 'test', 'query': 'A&B'}).json()
        page = self.client.post('/api/search', json={'source': 'test', 'query': 'different', 'cursor': result['next']}).json()
        self.assertEqual(page['status'], 'error')
        self.assertIn('expirada', page['message'])

    def test_item_page_api_and_media_references(self):
        result = self.client.post('/api/search', json={'source':'test', 'query':'A'}).json()
        ref = result['items'][0]['ref']
        self.assertEqual(self.client.get('/item/' + ref).status_code, 200)
        details = self.client.post('/api/details', json={'ref':ref})
        self.assertEqual(details.status_code, 200)
        self.assertIn('metadata', details.json())
        self.assertEqual(self.client.get('/api/media/invalid').status_code, 404)
        invalid = self.client.post('/api/source-detect', json={'url':'https://127.0.0.1/'})
        self.assertEqual(invalid.status_code, 200)
        self.assertIsNone(invalid.json()['source'])

    def test_ordering_controls_have_real_options(self):
        soup = BeautifulSoup(self.client.get('/').text, 'html.parser')
        options = soup.select('#sort option')
        self.assertEqual([option.get('value') for option in options], ['source','published-new','published-old','modified'])
        self.assertIsNotNone(soup.select_one('#sort-published'))
