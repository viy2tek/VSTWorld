import unittest
import httpx

from vstworld.catalog import Catalog, SourceError
from test_catalog import source, PAGE


class ItemAPITests(unittest.IsolatedAsyncioTestCase):
    async def test_details_and_image_use_opaque_references(self):
        def handler(req):
            if req.url.path == '/robots.txt':
                return httpx.Response(404)
            if req.url.path == '/load/item':
                return httpx.Response(200, text='<h1>Plugin</h1><div class="eText">Version: 1.0<br>Size: 20 MB<div class="gallery"><a href="/image.png"><img src="/thumb.png"></a></div></div>')
            if req.url.path in ('/image.png', '/thumb.png'):
                return httpx.Response(200, content=b'\x89PNG\r\n\x1a\nimage', headers={'content-type': 'image/png'})
            return httpx.Response(200, text=PAGE)
        catalog = Catalog([source()], transport=httpx.MockTransport(handler))
        self.addAsyncCleanup(catalog.close)
        result = await catalog.search('test', 'plugin')
        item = await catalog.details(result['items'][0]['ref'])
        self.assertTrue(item['metadata'])
        self.assertTrue(item['images'])
        self.assertTrue(item['images'][0]['url'].startswith('/api/media/'))
        token = item['images'][0]['url'].rsplit('/', 1)[-1]
        body, mime = await catalog.media(token)
        self.assertEqual(mime, 'image/png')
        self.assertTrue(body.startswith(b'\x89PNG'))

    async def test_media_does_not_accept_html_or_private_redirect(self):
        for headers in [{'content-type': 'text/html'}, {'content-type': 'text/html; note=image/jpeg'}, {'location': 'https://127.0.0.1/private'}]:
            catalog = Catalog([source(respect_robots=False)], transport=httpx.MockTransport(
                lambda req: httpx.Response(302 if 'location' in headers else 200, text='<html>bad</html>', headers=headers)))
            self.addAsyncCleanup(catalog.close)
            token = catalog.remember('media', 'test', 'https://example.com/image.png')
            with self.assertRaises(SourceError):
                await catalog.media(token)

    async def test_image_viewer_prefers_actual_large_image_over_og_thumbnail(self):
        requested = []
        def handler(req):
            requested.append(req.url.path)
            if req.url.path == '/view.html':
                return httpx.Response(200, text='<meta property="og:image" content="/thumb.jpg"><img src="/big/original.jpg">', headers={'content-type':'text/html'})
            return httpx.Response(200, content=b'original', headers={'content-type':'image/jpeg'})
        catalog = Catalog([source(respect_robots=False)], transport=httpx.MockTransport(handler))
        self.addAsyncCleanup(catalog.close)
        token = catalog.remember('media', 'test', 'https://example.com/view.html')
        body, mime = await catalog.media(token)
        self.assertEqual(requested, ['/view.html', '/big/original.jpg'])
        self.assertEqual(body, b'original')

    async def test_extensionless_image_viewer_is_resolved_by_content_type(self):
        calls = []
        def handler(req):
            calls.append(req.url.path)
            if req.url.path == '/viewer':
                return httpx.Response(200, text='<meta property="og:image" content="/original.jpg">', headers={'content-type':'text/html'})
            return httpx.Response(200, content=b'original', headers={'content-type':'image/jpeg'})
        catalog = Catalog([source(respect_robots=False)], transport=httpx.MockTransport(handler))
        self.addAsyncCleanup(catalog.close)
        token = catalog.remember('media', 'test', 'https://example.com/viewer')
        self.assertEqual((await catalog.media(token))[0], b'original')
        self.assertEqual(calls, ['/viewer', '/original.jpg'])

    async def test_update_timestamp_is_never_publication(self):
        catalog = Catalog([source(respect_robots=False)], transport=httpx.MockTransport(lambda req:
            httpx.Response(200, text='<div class="eBlock"><div class="eTitle"><a href="/load/item">Plugin</a></div><time class="updated" datetime="2026-11-05"></time></div>')))
        self.addAsyncCleanup(catalog.close)
        result = await catalog.search('test', 'plugin')
        self.assertIsNone(result['items'][0]['published'])
        self.assertEqual(result['items'][0]['modified'], '2026-11-05')

    async def test_partial_image_response_cannot_serve_html(self):
        def handler(req):
            if req.url.path == '/viewer':
                return httpx.Response(200,text='<meta property="og:image" content="/file">',headers={'content-type':'text/html'})
            return httpx.Response(206,text='<h1>untrusted</h1>',headers={'content-type':'text/html'})
        catalog = Catalog([source(respect_robots=False)],transport=httpx.MockTransport(handler))
        self.addAsyncCleanup(catalog.close)
        ref = catalog.remember('media','test','https://example.com/viewer')
        with self.assertRaises(SourceError):
            await catalog.media(ref)

    async def test_search_dates_are_explicit_not_product_release(self):
        catalog = Catalog([source(respect_robots=False)], transport=httpx.MockTransport(lambda req:
            httpx.Response(200, text='<div class="eBlock"><div class="eTitle"><a href="/load/item">Plugin</a></div><time class="published" datetime="2026-11-05"></time><p>Release: 2020-01-01</p></div>')))
        self.addAsyncCleanup(catalog.close)
        result = await catalog.search('test', 'plugin')
        self.assertEqual(result['items'][0]['published'], '2026-11-05')
        self.assertIsNone(result['items'][0]['modified'])
