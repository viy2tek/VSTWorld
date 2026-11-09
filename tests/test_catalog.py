import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from vstworld.config import Source, load_sources
from vstworld.http import PublicTransport, public_url
from vstworld.catalog import Catalog, Robots, SourceError


def source(**changes):
    return Source.model_validate({
        'id': 'test', 'name': 'Test', 'base_url': 'https://example.com/',
        'hosts': ['example.com'], 'search_path': '/search/', 'interval': 0,
        'item_selector': '.eBlock', 'title_selector': '.eTitle a',
        'next_selector': '.swchItem-next', 'download_selector': 'a.sprite',
        **changes,
    })


PAGE = '''<div class="eBlock"><div class="eTitle"><a href="/load/item">A &amp; B</a></div></div>
<div class="eBlock"><div class="eTitle"><a href="javascript:alert(1)">Bad</a></div></div>
<a class="swchItem-next" href="/search/?q=A%26B&amp;p=2;md=">Next</a>'''


class CatalogTests(unittest.IsolatedAsyncioTestCase):
    async def make_catalog(self, handler, sources=None):
        catalog = Catalog(sources or [source()], transport=httpx.MockTransport(handler))
        self.addAsyncCleanup(catalog.close)
        return catalog

    async def test_query_parsing_pagination_and_reference(self):
        calls = []
        def handler(req):
            calls.append(req)
            if req.url.path == '/robots.txt':
                return httpx.Response(200, text='User-agent: *\nDisallow:')
            if req.url.path == '/load/item':
                return httpx.Response(200, text='<a class="sprite" href="/jump">Download</a>')
            if req.url.path == '/jump':
                return httpx.Response(301, headers={'location': '/files/test.torrent'})
            if req.url.path == '/files/test.torrent':
                return httpx.Response(200, headers={'content-type': 'application/octet-stream'})
            return httpx.Response(200, text=PAGE)
        catalog = await self.make_catalog(handler)
        result = await catalog.search('test', 'A&B')
        self.assertEqual(result['items'][0]['title'], 'A & B')
        self.assertEqual(len(result['items']), 1)
        self.assertEqual(calls[1].url.params['q'], 'A&B')
        await catalog.search('test', 'A&B', cursor=result['next'])
        self.assertIn('p=2;md=', str(calls[-1].url))
        files = await catalog.downloads(result['items'][0]['ref'])
        self.assertEqual(files['files'][0]['kind'], 'torrent')
        self.assertTrue(files['files'][0]['url'].endswith('test.torrent'))

    async def test_slow_robots_does_not_block_other_origin(self):
        entered, release, healthy = asyncio.Event(), asyncio.Event(), asyncio.Event()
        async def handler(req):
            if req.url.host == 'example.com' and req.url.path == '/robots.txt':
                entered.set()
                await release.wait()
            if req.url.host == 'other.example.com':
                healthy.set()
            return httpx.Response(404) if req.url.path == '/robots.txt' else httpx.Response(200, text=PAGE)
        catalog = await self.make_catalog(handler, [source(), source(id='other',
            base_url='https://other.example.com/', hosts=['other.example.com'])])
        slow = asyncio.create_task(catalog.search('test', 'test'))
        await entered.wait()
        fast = asyncio.create_task(catalog.search('other', 'test'))
        try:
            await asyncio.wait_for(healthy.wait(), 0.3)
        finally:
            release.set()
            await asyncio.gather(slow, fast)

    async def test_robots_restriction_never_requests_search(self):
        calls = []
        def handler(req):
            calls.append(req.url.path)
            return httpx.Response(200, text='User-agent: *\nDisallow: /search/')
        catalog = await self.make_catalog(handler)
        with self.assertRaisesRegex(SourceError, 'robots'):
            await catalog.search('test', 'test')
        self.assertEqual(calls, ['/robots.txt'])

    async def test_source_can_query_without_applying_robots_policy(self):
        calls = []
        def handler(req):
            calls.append(req.url.path)
            if req.url.path == '/robots.txt':
                return httpx.Response(200, text='User-agent: *\nDisallow: /')
            return httpx.Response(200, text=PAGE)
        catalog = await self.make_catalog(handler, [source(respect_robots=False)])
        result = await catalog.search('test', 'Reaper')
        self.assertEqual(len(result['items']), 1)
        self.assertNotIn('/robots.txt', calls)

    async def test_robots_option_does_not_disable_redirect_host_validation(self):
        catalog = await self.make_catalog(lambda req: httpx.Response(302,
            headers={'location': 'https://127.0.0.1/private'}), [source(respect_robots=False)])
        with self.assertRaises(SourceError):
            await catalog.search('test', 'Reaper')

    async def test_robots_redirects_are_checked_and_failure_closed(self):
        def handler(req):
            return httpx.Response(302, headers={'location': 'https://localhost/secret'})
        catalog = await self.make_catalog(handler)
        with self.assertRaises(SourceError):
            await catalog.search('test', 'test')

    async def test_redirect_to_disallowed_path_is_not_followed(self):
        calls = []
        def handler(req):
            calls.append(req.url.path)
            if req.url.path == '/robots.txt':
                return httpx.Response(200, text='User-agent: *\nDisallow: /secret')
            return httpx.Response(302, headers={'location': '/secret'})
        catalog = await self.make_catalog(handler)
        with self.assertRaisesRegex(SourceError, 'robots'):
            await catalog.search('test', 'test')
        self.assertNotIn('/secret', calls)

    async def test_html_download_is_not_a_file(self):
        def handler(req):
            if req.url.path == '/robots.txt':
                return httpx.Response(404)
            if req.url.path == '/load/item':
                return httpx.Response(200, text='<a class="sprite" href="/landing.zip">Download</a>')
            if req.url.path == '/landing.zip':
                return httpx.Response(200, headers={'content-type': 'text/html'})
            return httpx.Response(200, text=PAGE)
        catalog = await self.make_catalog(handler)
        result = await catalog.search('test', 'test')
        files = await catalog.downloads(result['items'][0]['ref'])
        self.assertEqual(files['files'], [])
        self.assertTrue(files['notices'])

    async def test_download_get_headers_resolve_inaccurate_html_head(self):
        calls = []
        def handler(req):
            calls.append((req.method,req.url.path))
            if req.url.path == '/robots.txt': return httpx.Response(404)
            if req.url.path == '/load/item': return httpx.Response(200,text='<a class="sprite" href="/jump">Download</a>')
            if req.url.path == '/jump':
                if req.method == 'HEAD': return httpx.Response(200,headers={'content-type':'text/html'})
                return httpx.Response(301,headers={'location':'/file.torrent'})
            return httpx.Response(200,headers={'content-type':'application/octet-stream'})
        catalog = await self.make_catalog(handler)
        ref = catalog.remember('item','test','https://example.com/load/item')
        files = await catalog.downloads(ref)
        self.assertEqual(files['files'][0]['kind'],'torrent')
        self.assertIn(('GET','/jump'),calls)

    async def test_expired_or_wrong_cursor(self):
        catalog = await self.make_catalog(lambda req: httpx.Response(404))
        with self.assertRaises(SourceError):
            await catalog.search('test', 'test', cursor='fake')
        with self.assertRaises(SourceError):
            await catalog.downloads('fake')

    async def test_response_limit(self):
        catalog = await self.make_catalog(lambda req: httpx.Response(200, text='x' * 2_000_001))
        with self.assertRaises(SourceError):
            await catalog.search('test', 'test')

    async def test_dns_private_rejected_before_connection(self):
        transport = PublicTransport()
        self.addAsyncCleanup(transport.aclose)
        addresses = [(2, 1, 6, '', ('127.0.0.1', 443))]
        with patch.object(asyncio.get_running_loop(), 'getaddrinfo', return_value=addresses):
            with self.assertRaises(ValueError):
                await transport.handle_async_request(httpx.Request('GET', 'https://example.com/'))

    async def test_connection_uses_validated_ip_with_original_tls_identity(self):
        captured = []
        def handler(request):
            captured.append(request)
            return httpx.Response(200, text='ok')
        transport = PublicTransport()
        await transport.transport.aclose()
        transport.transport = httpx.MockTransport(handler)
        self.addAsyncCleanup(transport.aclose)
        addresses = [(2, 1, 6, '', ('1.1.1.1', 443))]
        with patch.object(asyncio.get_running_loop(), 'getaddrinfo', return_value=addresses):
            await transport.handle_async_request(httpx.Request('GET', 'https://example.com/search/'))
        self.assertEqual(captured[0].url.host, '1.1.1.1')
        self.assertEqual(captured[0].headers['host'], 'example.com')
        self.assertEqual(captured[0].extensions['sni_hostname'], 'example.com')

    async def test_post_form_preserves_text_and_params(self):
        requests = []
        def handler(req):
            if req.url.path == '/robots.txt':
                return httpx.Response(404)
            requests.append(req)
            return httpx.Response(200, text=PAGE)
        catalog = await self.make_catalog(handler, [source(method='POST', params={'t': '0'})])
        await catalog.search('test', ' A&B ')
        from urllib.parse import parse_qs
        self.assertEqual(requests[0].method, 'POST')
        self.assertEqual(parse_qs(requests[0].content.decode()), {'t': ['0'], 'q': [' A&B ']})


class ConfigTests(unittest.TestCase):
    def test_robots_wildcard_specificity_and_percent_encoding(self):
        rules = Robots('User-agent: *\nDisallow: /*?\nAllow: /*?page\nDisallow: /search/\nDisallow: /private$')
        self.assertTrue(rules.allowed('https://example.com/?page2'))
        self.assertFalse(rules.allowed('https://example.com/?q=x'))
        self.assertFalse(rules.allowed('https://example.com/s%65arch/?q=x'))
        self.assertTrue(rules.allowed('https://example.com/private/child'))
        self.assertFalse(rules.allowed('https://example.com/private'))

    def test_robots_crawl_delay_not_reduced(self):
        self.assertEqual(Robots('User-agent: *\nCrawl-delay: 300').delay, 300)

    def test_public_urls_only(self):
        for value in ['http://example.com/', 'https://localhost/', 'https://127.0.0.1/',
                      'https://[::1]/', 'https://user:pw@example.com/', 'https://example.com:444/']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                public_url(value)
        self.assertEqual(public_url('https://example.com/').host, 'example.com')

    def test_invalid_selectors_and_duplicate_ids_fail_early(self):
        with self.assertRaises(ValueError):
            source(item_selector='[')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'sources.json'
            path.write_text(json.dumps([source().model_dump()] * 2), encoding='utf-8')
            with self.assertRaises(ValueError):
                load_sources(path)
