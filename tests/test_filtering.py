import unittest

import httpx
from bs4 import BeautifulSoup
from pydantic import ValidationError

from vstworld.catalog import Catalog, SourceError
from vstworld.config import Source
from vstworld.details import extract_details
from vstworld.filtering import NativeFilters, extract_filters, native_params


def parse(html, title=''):
    return extract_filters(BeautifulSoup(html, 'html.parser'), title)


class FilterFactsTests(unittest.TestCase):
    def test_generic_vst_and_unknowns_stay_unknown(self):
        result = parse('<div>Marketing VST3 Windows</div>', 'Acme Piano VST')
        self.assertEqual(result['format'], ['vst'])
        self.assertEqual(result['system'], [])
        self.assertEqual(result['kind'], [])
        self.assertEqual(result['developer'], '')

    def test_title_explicit_tokens(self):
        result = parse('', 'Synth v.1.2.3 VSTi3 Win64 OSX')
        self.assertEqual(result['version'], '1.2.3')
        self.assertEqual(result['format'], ['vst3'])
        self.assertEqual(result['kind'], ['instrument'])
        self.assertEqual(result['targets'], [{'system': 'windows', 'architecture': '64'},
                                             {'system': 'macos', 'architecture': None}])

    def test_inline_facts_stop_at_next_label_and_ellipsis(self):
        result = parse('''<div class="eMessage">Версия:1.0.5 Разработчик:Steinberg
        Сайт разработчика:https://example.com Формат:VSTi3 Разрядность:64bit … Promotional words</div>''')
        self.assertEqual(result['developer'], 'Steinberg')
        self.assertEqual(result['version'], '1.0.5')
        self.assertEqual(result['format'], ['vst3'])
        self.assertEqual(result['architecture'], ['64'])

    def test_card_labels_and_developer(self):
        result = parse('''<div class="label-group"><span class="os-label">Win32</span>
        <span class="os-label">Win64</span><span class="os-label">Linux</span>
        <span class="fmt-label">VST</span><span class="fmt-label">AU</span></div>
        <span class="dev-name">A Developer</span>''')
        self.assertEqual(result['system'], ['windows', 'linux'])
        self.assertEqual(result['architecture'], ['32', '64'])
        self.assertEqual(result['format'], ['vst', 'au'])
        self.assertEqual(result['developer'], 'A Developer')
        self.assertIn({'system': 'linux', 'architecture': None}, result['targets'])

    def test_details_enrichment_does_not_turn_release_into_page_date(self):
        result = extract_details(b'''<h1>Plugin VST2</h1><article>Release date: 2025-01-01<br>
        Version: 2.0<br>Developer: Test<br>Operating system: Windows x64<br>
        Requirements: DAW supporting VST</article>''', 'https://example.com/item')
        self.assertEqual(result['dates'], {'published': None, 'modified': None})
        self.assertEqual(result['filters']['version'], '2.0')
        self.assertEqual(result['filters']['developer'], 'Test')
        self.assertEqual(result['filters']['kind'], [])
        self.assertEqual(result['filters']['format'], ['vst2'])
        self.assertEqual(result['filters']['targets'], [{'system': 'windows', 'architecture': '64'}])

    def test_separate_bitness_and_platform_have_one_unambiguous_target(self):
        result = parse('<div class="eMessage">Платформа: Windows Разрядность:64</div>')
        self.assertEqual(result['targets'], [{'system': 'windows', 'architecture': '64'}])

    def test_explicit_combined_formats_and_x86(self):
        result = parse('', 'Plugin VST2/3 Win x86')
        self.assertEqual(result['format'], ['vst2', 'vst3'])
        self.assertEqual(result['targets'], [{'system': 'windows', 'architecture': '32'}])

    def test_native_model_rejects_arbitrary_params(self):
        for value in [{'system': 'android'}, {'format': 'exe'}, {'os[]': 'win64'}]:
            with self.assertRaises(ValidationError):
                NativeFilters.model_validate(value)

    def test_common_64_bit_names_and_requirements_do_not_change_binary_bitness(self):
        for name in ('x86_64', 'x86-64', 'amd64', 'arm64', 'aarch64'):
            with self.subTest(name=name):
                self.assertEqual(parse('', 'Plugin Linux ' + name)['architecture'], ['64'])
        result = parse('<div class="eMessage">Requirements: Windows 10 x64 CPU AMD64</div>', 'Plugin VST2 x86')
        self.assertEqual(result['architecture'], ['32'])
        self.assertEqual(result['targets'], [{'system':'windows', 'architecture':'32'}])

    def test_brand_sample_and_preset_manager_are_not_sample_or_preset_packs(self):
        self.assertEqual(parse('', 'Sample Logic - Preset Manager VST3')['kind'], [])
        self.assertIn('samples', parse('', 'Author - Synth Samples')['kind'])
        self.assertIn('presets', parse('', 'Author - Synth Presets')['kind'])


class NativeSearchTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.requests = []
        self.source = Source(id='test', name='Test', base_url='https://plugins4free.com/',
            hosts=['plugins4free.com'], search_path='/search', query_param='term',
            item_selector='.card', title_selector='a', next_selector='.next',
            download_selector='a', interval=0, respect_robots=False)
        def handler(request):
            self.requests.append(request)
            return httpx.Response(200, text='<div class="card"><a href="/plugin/1">Piano VST</a></div><a class="next" href="/search?term=piano&amp;p=2">Next</a>')
        self.catalog = Catalog([self.source], transport=httpx.MockTransport(handler))
        self.addAsyncCleanup(self.catalog.close)

    async def test_safe_native_parameters_and_cursor_binding(self):
        filters = {'system': 'windows', 'architecture': '64', 'format': 'vst3'}
        result = await self.catalog.search('test', 'piano', filters=filters)
        self.assertEqual(self.requests[-1].url.params.get_list('os[]'), ['win64'])
        self.assertEqual(self.requests[-1].url.params['fmt[]'], 'vst')
        self.assertEqual(result['native_filters'], ['system', 'architecture', 'format'])
        with self.assertRaises(SourceError):
            await self.catalog.search('test', 'piano', cursor=result['next'], filters={'system': 'linux'})
        await self.catalog.search('test', 'piano', cursor=result['next'], filters=filters)
        self.assertEqual(self.requests[-1].url.params.get_list('os[]'), ['win64'])
        self.assertEqual(self.requests[-1].url.params['fmt[]'], 'vst')

    async def test_system_mapping_and_architecture_alone(self):
        for filters, expected in [({'system': 'windows'}, ['win32', 'win64']),
                                  ({'system': 'macos'}, ['allmacos']),
                                  ({'system': 'linux', 'architecture': '32'}, ['linux']),
                                  ({'architecture': '64'}, [])]:
            result = await self.catalog.search('test', 'piano', filters=filters)
            self.assertEqual(self.requests[-1].url.params.get_list('os[]'), expected)
            self.assertNotIn('architecture', result['native_filters'])

    async def test_other_sources_sections_and_unsupported_formats_stay_local(self):
        params, applied = native_params(self.source.model_copy(update={'base_url': 'https://example.com/'}),
                                       NativeFilters(system='windows', format='au'))
        self.assertEqual((params, applied), ({}, []))
        result = await self.catalog.search('test', 'piano', filters={'format': 'kontakt'})
        self.assertEqual(result['native_filters'], [])
        self.assertNotIn('fmt[]', self.requests[-1].url.params)
