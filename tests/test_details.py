import unittest
from pathlib import Path

from vstworld.details import extract_details


PAGE = 'https://vsthouse.ru/load/item/38-1-0-41735'


class DetailsTests(unittest.TestCase):
    def test_dle_installation_and_gallery_are_not_lost(self):
        result = extract_details(Path('tests/fixtures/musicmakers.html').read_bytes(), 'https://musicmakers.ru/item', 'article.fullstory')
        self.assertTrue(result['installation'])
        self.assertEqual(len(result['images']), 1)
        self.assertEqual(len(result['metadata']), 5)
        self.assertIn('do=go', result['images'][0]['url'])

    def test_plugins4free_structured_facts_and_main_screenshot(self):
        result = extract_details(Path('tests/fixtures/plugins4free.html').read_bytes(), 'https://plugins4free.com/plugin/970', '.plugin-detail')
        facts = {field['label']:field['value'] for field in result['metadata']}
        self.assertEqual(facts['Operating system'], 'Win64')
        self.assertEqual(facts['Format'], 'VST')
        self.assertEqual(len(result['images']), 1)
        self.assertFalse(result['images'][0]['original_available'])

    def extract(self, html, selector=None):
        return extract_details(html.encode('utf-8'), PAGE, selector)

    def test_observed_ucoz_structure(self):
        result = extract_details(Path('tests/fixtures/details-structure.html').read_bytes(), PAGE)
        metadata = {entry['label']: entry['value'] for entry in result['metadata']}
        self.assertEqual(metadata['Версия'], '1.0.5')
        self.assertEqual(metadata['Системные требования'], 'Windows 10\\ Cubase 16')
        self.assertEqual(metadata['Дата Выпуска'], '5.11.2026')
        self.assertNotIn('Marketing', str(result))
        self.assertNotIn('fake', str(result))
        self.assertEqual(len(result['installation']), 1)
        blocks = result['installation'][0]['blocks']
        self.assertEqual(blocks[0]['text'], '0 Скачайте последнюю версию (с сайта steinberg):')
        self.assertIn('2. Запустите V.R Unlocker.', str(blocks))
        self.assertEqual(result['videos'], [{'id': 'n6UNGaLyos8'}])
        self.assertEqual(len(result['images']), 2)
        self.assertIn('fastpic.org/view/', result['images'][0]['url'])
        self.assertFalse(result['images'][0]['original_available'])
        self.assertEqual(result['images'][1]['url'], 'https://images.example/original.png')
        self.assertTrue(result['images'][1]['original_available'])
        self.assertEqual(result['dates']['published'], '2026-11-06T11:17:00+03:00')

    def test_preserves_paragraphs_lists_links_and_order(self):
        result = self.extract('''<article><h1>Package</h1><p>Version: 2</p>
        <details><summary>Installation</summary><p>Before <b>starting</b>, read
        <a href="/manual">the manual</a>.</p><ol start="3"><li>Install A</li>
        <li value="7">Install B <a href="javascript:evil()">unsafe link</a></li></ol>
        <p>Finish.<br>Restart.</p></details></article>''')
        blocks = result['installation'][0]['blocks']
        self.assertEqual([b['kind'] for b in blocks], ['paragraph', 'list', 'paragraph'])
        self.assertEqual(blocks[0]['text'], 'Before starting, read the manual.')
        self.assertEqual(blocks[0]['links'], [{'label': 'the manual', 'url': 'https://vsthouse.ru/manual'}])
        self.assertEqual(blocks[1]['items'], ['3. Install A', '7. Install B unsafe link'])
        self.assertEqual(blocks[1]['links'], [])
        self.assertEqual(blocks[2]['text'], 'Finish.\nRestart.')

    def test_waves_spoilers_and_video_demos(self):
        result = extract_details(Path('tests/fixtures/details-waves.html').read_bytes(), PAGE)
        self.assertEqual([x['title'] for x in result['installation']], ['Установка'])
        self.assertEqual(len(result['videos']), 4)
        self.assertEqual(result['images'][0]['url'], 'https://ibb.co/8dKqrqD')
        self.assertEqual(len(result['images']), 1)
        self.assertNotIn('marketing', str(result))
        text = '\n'.join(b.get('text', '') for b in result['installation'][0]['blocks'])
        self.assertLess(text.index('Примечание'), text.index('Удаление/очистка'))
        self.assertLess(text.index('Удаление/очистка'), text.index('Установить Runtime'))
        self.assertIn('• C:\\Program Files (x86)\\Waves\\', text)
        self.assertEqual(result['dates'], {'published': None, 'modified': None})

    def test_unknown_layout_and_release_are_not_page_dates(self):
        result = self.extract('<div>Version: wrong</div><div class="eText">Дата Выпуска: 2026-11-05</div>')
        self.assertEqual(result['dates'], {'published': None, 'modified': None})
        self.assertEqual(len(result['metadata']), 1)
        self.assertEqual(self.extract('<div>Installation: wrong</div>')['installation'], [])

    def test_portuguese_facts_and_technical_requirement_continuations(self):
        result = self.extract('''<article>Data de lançamento: 05.11.2026<br>Versão: 1.0.5<br>
        Desenvolvedora: Steinberg<br>Desenvolvedor: Yamaha<br>Distribuidora: Publisher<br>
        Site do desenvolvedor: steinberg.net<br>Formato: VSTi3<br>
        Profundidade de bits: 64 bits<br>Arquitetura: x64<br>Tamanho: 423.6 MB<br>
        Requisitos do sistema: Windows 10<br>RAM: 8 GB<br>CPU: Intel Core i5<br>
        Windows 11 também compatível<br>Transforme suas músicas com nossa revolução vocal.</article>''')
        facts = {entry['label']: entry['value'] for entry in result['metadata']}
        self.assertEqual(len(facts), 11)
        self.assertEqual(facts['Versão'], '1.0.5')
        self.assertEqual(facts['Site do desenvolvedor'], 'steinberg.net')
        self.assertEqual(facts['Requisitos do sistema'],
            'Windows 10\nRAM: 8 GB\nCPU: Intel Core i5\nWindows 11 também compatível')
        self.assertNotIn('revolução', str(result))

    def test_requirements_last_does_not_absorb_promotional_sentence(self):
        result = self.extract('''<article>System requirements: Windows 10<br>
        Create inspiring music with our revolutionary product.<br>RAM: discount offer</article>''')
        self.assertEqual(result['metadata'], [{'label': 'System requirements', 'value': 'Windows 10'}])

    def test_selector_and_url_trust_boundary(self):
        result = self.extract('''<article><p>Version: wrong</p></article><div id="wanted">
        <p>Publisher: Publisher Ltd</p><div class="gallery"><a href="javascript:x">
        <img src="https://127.0.0.1/private.png"></a><img src="/safe.png"></div>
        <iframe src="https://youtu.be/erzVpZjUQBc"></iframe></div>''', '#wanted')
        self.assertEqual(result['metadata'], [{'label': 'Publisher', 'value': 'Publisher Ltd'}])
        self.assertEqual(len(result['images']), 1)
        self.assertEqual(result['images'][0]['url'], 'https://vsthouse.ru/safe.png')
        self.assertFalse(result['images'][0]['original_available'])
        self.assertEqual(result['videos'], [{'id': 'erzVpZjUQBc'}])

    def test_bounds_and_deduplication(self):
        result = self.extract('<article>' + '<p>Version: 1</p>' * 200 +
            '<div class="gallery">' + ''.join(f'<img src="/image{i}.jpg">' for i in range(100)) + '</div>' +
            '<details><summary>Installation</summary><p>' + 'a' * 10000 + '</p>' +
            '<p>Finish.</p>' * 200 + '</details></article>')
        self.assertEqual(len(result['metadata']), 1)
        self.assertLessEqual(len(result['images']), 40)
        self.assertLessEqual(len(result['installation'][0]['blocks']), 100)
        self.assertLessEqual(len(result['installation'][0]['blocks'][0]['text']), 8000)


if __name__ == '__main__':
    unittest.main()
