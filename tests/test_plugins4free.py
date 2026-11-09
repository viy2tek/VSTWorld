import json
import unittest
from pathlib import Path

import httpx

from vstworld.catalog import Catalog
from vstworld.config import Source


class Plugins4FreeTests(unittest.IsolatedAsyncioTestCase):
    async def test_cards_json_resolution_and_head_without_binary_body(self):
        fixture = Path('tests/fixtures/plugins4free.html').read_text(encoding='utf-8')
        requested = []
        def handle(request):
            requested.append(request)
            if request.url.path == '/robots.txt':
                return httpx.Response(404)
            if request.url.path == '/download':
                self.assertEqual(request.method, 'POST')
                self.assertEqual(request.headers['X-CSRF-TOKEN'], 'synthetic-csrf-token')
                payload = json.loads(request.content)
                self.assertEqual(payload['plugin_id'], 970)
                return httpx.Response(200, json={'url':'https://plugins4free.com/get_plug/'+payload['filename']})
            if request.url.path.startswith('/get_plug/'):
                self.assertEqual(request.method, 'HEAD', 'Não baixar o corpo do arquivo para validar o link')
                return httpx.Response(200, headers={'content-type':'application/zip'})
            return httpx.Response(200, text=fixture)
        source = Source(id='p4f', name='P4F', base_url='https://plugins4free.com/', hosts=['plugins4free.com'],
            search_path='/search', query_param='term', item_selector='a.plugin-card', title_selector='.plugin-name',
            link_selector=':scope', download_selector='a.download-item[onclick]', download_adapter='plugins4free', interval=0)
        catalog = Catalog([source], transport=httpx.MockTransport(handle))
        self.addAsyncCleanup(catalog.close)
        result = await catalog.search('p4f', 'piano')
        self.assertEqual(len(result['items']), 2)
        self.assertTrue(result['items'][0]['url'].endswith('/plugin/970'))
        files = await catalog.downloads(result['items'][0]['ref'])
        self.assertEqual(len(files['files']), 3)
        self.assertEqual(files['notices'], [])

    async def test_adapter_rejects_unsupported_host(self):
        with self.assertRaises(ValueError):
            Source(id='bad', name='Bad', base_url='https://example.com/', hosts=['example.com'], search_path='/',
                item_selector='a', title_selector=':scope', download_selector='a', download_adapter='plugins4free')

    async def test_javascript_is_not_evaluated_and_external_api_url_is_rejected(self):
        from vstworld.plugins4free import download_links
        from bs4 import BeautifulSoup
        for onclick, expected_calls in [("startDownload(event, 970, 'safe.zip');evil()", 0),
                                         ("startDownload(event, 970, 'safe.zip')", 1)]:
            calls = []
            def handler(request):
                calls.append(request)
                return httpx.Response(200, json={'url':'https://evil.example/file.zip'})
            source = Source(id='p4f', name='P4F', base_url='https://plugins4free.com/', hosts=['plugins4free.com'],
                search_path='/', item_selector='a', title_selector=':scope', download_selector='a',
                download_adapter='plugins4free', respect_robots=False, interval=0)
            catalog = Catalog([source], transport=httpx.MockTransport(handler))
            try:
                soup = BeautifulSoup('<a></a>', 'html.parser')
                soup.a['onclick'] = onclick
                links, notices = await download_links(catalog, source, [soup.a], b"'X-CSRF-TOKEN':'synthetic-token'")
                self.assertEqual(links, [])
                self.assertTrue(notices)
                self.assertEqual(len(calls), expected_calls)
            finally:
                await catalog.close()
