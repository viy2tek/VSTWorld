import unittest

import httpx

from vstworld.config import Source
from vstworld.discovery import detect_source


FORM = '<form action="/search/" method="get"><input name="q" maxlength="30"><input type="hidden" name="t" value="0"></form>'
ITEMS = '<div class="eBlock"><h2 class="eTitle"><a href="/load/item">Piano One instrument</a></h2></div>'
DETAIL = '<a class="sprite" href="/files/piano.torrent">Download</a>'


class DiscoveryTests(unittest.IsolatedAsyncioTestCase):
    def transport(self, *, home=FORM + ITEMS, detail=DETAIL, robots='', search=None):
        self.calls = []
        def handler(req):
            self.calls.append(req)
            if req.url.path == '/robots.txt':
                return httpx.Response(200, text=robots)
            body = detail if req.url.path == '/load/item' else (search if req.url.path == '/search/' and search is not None else home)
            return httpx.Response(200, text=body)
        return httpx.MockTransport(handler)

    async def test_detail_url_detects_native_form_and_checks_real_search_without_binary(self):
        result = await detect_source('https://example.com/load/item', [], self.transport())
        source = Source.model_validate(result['source'])
        self.assertEqual(source.base_url, 'https://example.com/')
        self.assertEqual(source.hosts, ['example.com'])
        self.assertEqual(source.params, {'t': '0'})
        self.assertTrue(source.respect_robots)
        searches = [r for r in self.calls if r.url.path == '/search/']
        self.assertTrue(searches[0].url.params['q'].strip())
        self.assertFalse(any(r.url.path.startswith('/files/') for r in self.calls))
        self.assertEqual(next(c for c in result['checks'] if c['name'] == 'download')['status'], 'verified')
        self.assertEqual(next(c for c in result['checks'] if c['name'] == 'pagination')['status'], 'unverified')

    async def test_unknown_layout_and_missing_download_do_not_create_bogus_config(self):
        for home, detail in [('<h1>Welcome</h1>', DETAIL), (FORM + ITEMS, '<p>No links</p>')]:
            result = await detect_source('https://example.com/', [], self.transport(home=home, detail=detail))
            self.assertIsNone(result['source'])
            self.assertTrue(any(c['status'] == 'unverified' for c in result['checks']))

    async def test_supplied_installer_is_not_requested(self):
        result = await detect_source('https://example.com/setup.exe', [], self.transport())
        self.assertIsNone(result['source'])
        self.assertFalse(any(r.url.path == '/setup.exe' for r in self.calls))

    async def test_preserves_existing_customization_and_robots_override(self):
        existing = Source(id='custom', name='Meu site', base_url='https://example.com/', hosts=['example.com'],
                          respect_robots=False, interval=0, search_path='/search/', item_selector='.eBlock',
                          title_selector='.eTitle a', download_selector='a.sprite', note='customizado')
        result = await detect_source('https://example.com/load/item', [existing], self.transport())
        self.assertEqual(result['source'], existing.model_dump())
        self.assertFalse(any(r.url.path == '/robots.txt' for r in self.calls))

    async def test_robots_block_is_reported_and_search_not_requested(self):
        result = await detect_source('https://example.com/', [], self.transport(robots='User-agent: *\nDisallow: /search/'))
        self.assertTrue(any(c['status'] == 'blocked' for c in result['checks']))
        self.assertFalse(any(r.url.path == '/search/' for r in self.calls))
        self.assertIsNotNone(result['source'])
        self.assertTrue(result['source']['respect_robots'])

    async def test_homepage_robots_block_stops_inspection(self):
        result = await detect_source('https://example.com/', [], self.transport(robots='User-agent: *\nDisallow: /'))
        self.assertIsNone(result['source'])
        self.assertEqual([r.url.path for r in self.calls], ['/robots.txt'])

    async def test_search_without_matching_title_is_not_verified(self):
        result = await detect_source('https://example.com/', [], self.transport(search=ITEMS.replace('Piano One instrument', 'Unrelated result')))
        self.assertEqual(next(c for c in result['checks'] if c['name'] == 'search')['status'], 'unverified')

    async def test_observed_next_link_is_recorded_without_following(self):
        home = FORM + ITEMS + '<a rel="next" href="/page/2">Next</a>'
        result = await detect_source('https://example.com/', [], self.transport(home=home))
        self.assertEqual(result['source']['next_selector'], 'a[rel~="next"][href]')
        self.assertFalse(any(r.url.path == '/page/2' for r in self.calls))

    async def test_password_or_external_forms_are_not_submitted(self):
        for form in ['<form action="/search/"><input name="q"><input type="password"></form>',
                     '<form action="https://other.example/search/"><input name="q"></form>']:
            result = await detect_source('https://example.com/', [], self.transport(home=form + ITEMS))
            self.assertIsNone(result['source'])
            self.assertFalse(any(r.url.path == '/search/' for r in self.calls))

    async def test_invalid_public_url_does_not_request(self):
        result = await detect_source('https://127.0.0.1/', [], self.transport())
        self.assertIsNone(result['source'])
        self.assertEqual(self.calls, [])

    async def test_post_wordpress_form_and_external_links_filtered(self):
        home = '<form method="post" action="/search/"><input type="search" name="s"></form><article><h2><a href="/load/item">Piano One</a></h2></article>'
        result = await detect_source('https://example.com/', [], self.transport(home=home, detail='<a download href="https://evil.example/file.zip">x</a>'))
        self.assertIsNone(result['source'])
        self.assertTrue(any(r.method == 'POST' and b's=Piano' in r.content for r in self.calls))
        self.assertTrue(all(r.url.host == 'example.com' for r in self.calls))
