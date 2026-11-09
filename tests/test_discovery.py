import unittest

import httpx
from bs4 import BeautifulSoup

from vstworld.config import Source
from vstworld.catalog import Catalog
from vstworld.discovery import detect_source, search_form


FORM = '<form action="/search/" method="get"><input name="q" maxlength="30"><input type="hidden" name="t" value="0"></form>'
ITEMS = '<div class="eBlock"><h2 class="eTitle"><a href="/load/item">Piano One instrument</a></h2></div>'
DETAIL = '<a class="sprite" href="/files/piano.torrent">Download</a>'


class SearchFormTests(unittest.IsolatedAsyncioTestCase):
    async def settings(self, html):
        source = Source(id='test', name='test', base_url='https://example.com/', hosts=['example.com'],
                        search_path='/', item_selector='article', title_selector='h2 a', download_selector='a')
        catalog = Catalog([source], transport=httpx.MockTransport(lambda req: httpx.Response(500)))
        try:
            return search_form(BeautifulSoup(html, 'html.parser'), catalog, source, source.base_url)
        finally:
            await catalog.close()

    async def test_musicmakers_search_name_and_hidden_fields(self):
        value = await self.settings('<form method="post"><input type="search" name="story">'
            '<input type="hidden" name="do" value="search"><input type="hidden" name="subaction" value="search"></form>')
        self.assertIsNotNone(value)
        self.assertEqual(value['query_param'], 'story')
        self.assertEqual(value['method'], 'POST')
        self.assertEqual(value['params'], {'do':'search', 'subaction':'search'})

    async def test_custom_names_from_labels_and_form_role(self):
        for html in ['<form><label for="term">Pesquisar produtos</label><input id="term" name="term"></form>',
                     '<form role="search"><input name="term"></form>',
                     '<form><input name="term" placeholder="Поиск по сайту"></form>',
                     '<form action="/search"><input name="term"></form>']:
            with self.subTest(html=html):
                value = await self.settings(html)
                self.assertIsNotNone(value)
                self.assertEqual(value['query_param'], 'term')

    async def test_successful_controls_and_submit_override(self):
        value = await self.settings('<form action="/other" method="post"><input type="search" name="term">'
            '<input type="hidden" name="token" value="observed">'
            '<input type="hidden" name="ignore" value="x" disabled>'
            '<fieldset disabled><input type="hidden" name="ignore2" value="x"></fieldset>'
            '<input type="checkbox" name="exact" checked><input type="checkbox" name="ignore3">'
            '<input type="radio" name="where" value="title" checked><input type="radio" name="where" value="all">'
            '<select name="category"><option value="all">All</option><option selected value="vst">VST</option></select>'
            '<select name="order"><option value="new">New</option></select>'
            '<button name="go" value="find" formaction="/search" formmethod="get">Search</button></form>')
        self.assertIsNotNone(value)
        self.assertEqual(value['search_path'], 'https://example.com/search')
        self.assertEqual(value['method'], 'GET')
        self.assertEqual(value['params'], {'token':'observed','exact':'on','where':'title','category':'vst','order':'new','go':'find'})

    async def test_form_associated_controls_and_disabled_query(self):
        value = await self.settings('<form id="find" action="/search"></form>'
            '<input form="find" type="search" name="term"><input form="find" type="hidden" name="mode" value="all">')
        self.assertIsNotNone(value)
        self.assertEqual(value['params'], {'mode':'all'})
        self.assertIsNone(await self.settings('<form><input type="search" name="term" disabled></form>'))

    async def test_disabled_options_and_first_legend_follow_form_semantics(self):
        value = await self.settings('<form><fieldset disabled><legend><input type="search" name="term">'
            '<input type="hidden" name="mode" value="all"></legend><input type="hidden" name="ignored" value="x"></fieldset>'
            '<select name="category"><option value="placeholder" selected disabled>Choose</option><option value="vst">VST</option></select></form>')
        self.assertIsNotNone(value)
        self.assertEqual(value['params'], {'mode':'all'})

    async def test_ambiguous_or_unrepresentable_forms_not_guessed(self):
        for inner in ['<input type="search" name="a"><input type="search" name="b">',
                      '<input type="search" name="q"><input name="email" type="email">',
                      '<input type="search" name="q"><input type="hidden" name="a" value="1"><input type="hidden" name="a" value="2">',
                      '<input type="search" name="q"><select name="a" multiple><option selected>1</option><option selected>2</option></select>']:
            with self.subTest(inner=inner):
                self.assertIsNone(await self.settings('<form>'+inner+'</form>'))

    async def test_no_mutation_or_unsupported_encoding(self):
        for html in ['<form method="post" action="/delete"><input type="search" name="q"></form>',
                     '<form method="post" action="/?action=delete"><input type="search" name="q"></form>',
                     '<form method="post"><input type="search" name="q"><input type="hidden" name="action" value="delete"></form>',
                     '<form method="post" enctype="multipart/form-data"><input type="search" name="q"></form>',
                     '<form><input name="email" placeholder="Your email"></form>',
                     '<form><input type="search" name="q"><input type="password"></form>']:
            with self.subTest(html=html):
                self.assertIsNone(await self.settings(html))


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
