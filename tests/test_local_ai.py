import importlib
import json
import unittest
from unittest.mock import AsyncMock, patch

import httpx

from vstworld.config import Source
from vstworld.local_ai import detect_with_ai, _html


HOME = ('<form action="/search"><input type="search" name="q"></form>'
        '<section class="product"><h3><a href="/product/piano">Piano One</a></h3></section>')
DETAIL = '<main class="description"><a class="get" href="/files/piano.zip">Download</a></main>'
LISTING = dict(item_selector='.product', title_selector='h3 a', link_selector='h3 a', next_selector=None)
DETAIL_SELECTORS = dict(download_selector='a.get', detail_selector='main.description')


class LocalAITests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.calls = []
        self.ai_calls = []

    def web(self, home=HOME, search=HOME, detail=DETAIL):
        def handler(request):
            self.calls.append(request)
            if request.url.path == '/robots.txt':
                return httpx.Response(404)
            body = (search if request.url.path == '/search' else detail
                    if request.url.path == '/product/piano' else home)
            return httpx.Response(200, text=body, headers={'Content-Type': 'text/html'})
        return httpx.MockTransport(handler)

    def ai(self, listing=LISTING, detail=DETAIL_SELECTORS, info=None):
        def handler(request):
            self.ai_calls.append(request)
            self.assertEqual(str(request.url).split('/api/')[0], 'http://127.0.0.1:11434')
            payload = json.loads(request.content)
            if request.url.path == '/api/show':
                return httpx.Response(200, json=info if info is not None else
                    {'model_info': {'general.architecture': 'qwen35'}})
            self.assertFalse(payload['stream'])
            self.assertEqual(payload['format']['additionalProperties'], False)
            value = listing if payload['format']['title'] == 'Listing' else detail
            return httpx.Response(200, json={'done': True, 'response': value if isinstance(value, str) else json.dumps(value)})
        return httpx.MockTransport(handler)

    async def test_success_verifies_observed_search_and_download(self):
        result = await detect_with_ai('https://example.com/', [], transport=self.web(), ollama_transport=self.ai())
        self.assertIsNotNone(result['source'], result)
        self.assertEqual(result['source']['item_selector'], '.product')
        self.assertEqual(result['source']['query_param'], 'q')
        self.assertEqual(result['source']['hosts'], ['example.com'])
        verified = {check['name'] for check in result['checks'] if check['status'] == 'verified'}
        self.assertTrue({'search', 'download'} <= verified)
        self.assertTrue(any(request.url.path == '/search' and request.url.params['q'] == 'Piano One' for request in self.calls))
        self.assertFalse(any(request.url.path.startswith('/files/') for request in self.calls))
        self.assertEqual(len(self.ai_calls), 3)

    async def test_server_unavailable(self):
        def unavailable(request):
            raise httpx.ConnectError('offline', request=request)
        result = await detect_with_ai('https://example.com/', [], transport=self.web(),
            ollama_transport=httpx.MockTransport(unavailable))
        self.assertIsNone(result['source'])
        self.assertIn('Ollama indisponível', result['message'])
        self.assertEqual(self.calls, [])

    async def test_absent_model(self):
        result = await detect_with_ai('https://example.com/', [], transport=self.web(),
            ollama_transport=httpx.MockTransport(lambda request: httpx.Response(404, json={'error': 'not found'})))
        self.assertIsNone(result['source'])
        self.assertIn('instale o modelo', result['message'])

    async def test_invalid_json_schema_code_and_unbounded_selectors(self):
        for value in ['not json', 'import os; os.system("calc")', {**LISTING, 'script': 'alert(1)'},
                      {**LISTING, 'item_selector': 15}, {**LISTING, 'item_selector': 'x' * 501},
                      {**LISTING, 'item_selector': 'javascript:alert(1)'},
                      {**LISTING, 'item_selector': '['}, {**LISTING, 'item_selector': '.missing'}]:
            with self.subTest(value=value):
                result = await detect_with_ai('https://example.com/', [], transport=self.web(), ollama_transport=self.ai(listing=value))
                self.assertIsNone(result['source'])

    async def test_remote_models_blocked_before_generation(self):
        for info in [{'remote_host': 'https://ollama.com', 'model_info': {'general.architecture': 'qwen'}},
                     {'remote_model': 'qwen', 'model_info': {'general.architecture': 'qwen'}},
                     {'details': {'remote_host': 'https://elsewhere.com'}}, {}]:
            with self.subTest(info=info):
                self.ai_calls.clear()
                result = await detect_with_ai('https://example.com/', [], transport=self.web(), ollama_transport=self.ai(info=info))
                self.assertIsNone(result['source'])
                self.assertEqual(len(self.ai_calls), 1)
        for model in ['qwen:cloud', 'qwen:4b-cloud', 'https://example.com/qwen', '']:
            self.ai_calls.clear()
            result = await detect_with_ai('https://example.com/', [], model=model, transport=self.web(), ollama_transport=self.ai())
            self.assertIsNone(result['source'])
            self.assertEqual(self.ai_calls, [])

    async def test_private_urls_no_network(self):
        for url in ['https://127.0.0.1/', 'http://example.com/', 'https://192.168.1.3/', 'https://localhost/']:
            result = await detect_with_ai(url, [], transport=self.web(), ollama_transport=self.ai())
            self.assertIsNone(result['source'])
        self.assertEqual(self.calls, [])
        self.assertEqual(self.ai_calls, [])

    async def test_missing_form_empty_results_and_invalid_download(self):
        for options in [dict(home=HOME.split('</form>')[1]), dict(search='<p>No results</p>'),
                        dict(detail='<main>No links</main>'),
                        dict(detail='<main class="description"><a class="get" href="https://other.example/file.zip">File</a></main>')]:
            with self.subTest(options=options):
                result = await detect_with_ai('https://example.com/', [], transport=self.web(**options), ollama_transport=self.ai())
                self.assertIsNone(result['source'])

    async def test_existing_configuration_preserved_without_ai(self):
        source = Source(id='custom', name='Custom', base_url='https://example.com/', hosts=['example.com'],
            search_path='/search', item_selector='.product', title_selector='h3 a', download_selector='a.get',
            interval=0, note='My customizations')
        result = await detect_with_ai('https://example.com/', [source], transport=self.web(), ollama_transport=self.ai())
        self.assertEqual(result['source'], source.model_dump())
        self.assertEqual(self.ai_calls, [])

    async def test_import_does_not_contact_ollama(self):
        import vstworld.local_ai as module
        importlib.reload(module)
        self.assertEqual(self.ai_calls, [])

    async def test_native_validation_must_verify_both_checks(self):
        for check in ['search', 'download']:
            report = dict(source={'untrusted': True}, checks=[dict(name=check, status='verified')], message='partial')
            with patch('vstworld.local_ai.detect_source', new=AsyncMock(return_value=report)):
                result = await detect_with_ai('https://example.com/', [], transport=self.web(), ollama_transport=self.ai())
                self.assertIsNone(result['source'])

    async def test_robots_restrictions_stop_before_generation(self):
        def denied(request):
            return httpx.Response(200, text='User-agent: *\nDisallow: /', headers={'Content-Type': 'text/plain'})
        result = await detect_with_ai('https://example.com/', [], transport=httpx.MockTransport(denied),
            ollama_transport=self.ai())
        self.assertIsNone(result['source'])
        self.assertEqual(len(self.ai_calls), 1)

    async def test_size_limit_and_redirect_blocked(self):
        for response in [httpx.Response(200, content=b'x' * 262145),
                         httpx.Response(307, headers={'Location': 'https://other.example/api/show'})]:
            result = await detect_with_ai('https://example.com/', [], transport=self.web(),
                ollama_transport=httpx.MockTransport(lambda request: response))
            self.assertIsNone(result['source'])

    def test_sanitized_prompt_removes_code_credentials_and_is_bounded(self):
        value = _html('<script>evil()</script><style>.evil{}</style><form><input type="password" value="secret">'
                      '<p>private account</p></form><input name="token" value="private">'
                      '<a onclick="evil()" href="/detail">Piano</a>' + '<p>text</p>' * 5000)
        for forbidden in ['evil', 'secret', 'private', 'onclick', '<input', '<style', '<script']:
            self.assertNotIn(forbidden, value)
        self.assertLessEqual(len(value), 16000)
