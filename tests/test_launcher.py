import os
import socket
import threading
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from vstworld.__main__ import desktop_sources, migrate_sources, open_when_ready, reserve_port


class LauncherTests(unittest.TestCase):
    def test_experimental_clones_stable_without_changing_it(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'LOCALAPPDATA':folder}):
            stable = desktop_sources()
            stable.parent.mkdir()
            stable.write_text('[]', encoding='utf-8')
            target = desktop_sources(experimental=True)
            self.assertNotEqual(stable, target)
            migrate_sources(target)
            self.assertEqual(target.read_text(), '[]')
            target.write_text('[1]', encoding='utf-8')
            self.assertEqual(stable.read_text(), '[]')

    def test_rename_copies_legacy_sources_without_overwriting(self):
        with tempfile.TemporaryDirectory() as folder:
            old = Path(folder) / 'VSTHouse Brasil/sources.json'
            old.parent.mkdir()
            old.write_text('[]', encoding='utf-8')
            new = Path(folder) / 'VSTWorld/sources.json'
            migrate_sources(new)
            self.assertEqual(new.read_bytes(), old.read_bytes())
            old.write_text('invalid', encoding='utf-8')
            migrate_sources(new)
            self.assertEqual(new.read_text(), '[]')
            self.assertEqual(old.read_text(), 'invalid')

    def test_invalid_legacy_config_is_not_copied(self):
        with tempfile.TemporaryDirectory() as folder:
            old = Path(folder) / 'VSTHouse Brasil/sources.json'
            old.parent.mkdir()
            old.write_text('invalid', encoding='utf-8')
            new = Path(folder) / 'VSTWorld/sources.json'
            with self.assertRaises(ValueError):
                migrate_sources(new)
            self.assertFalse(new.exists())

    def test_sources_live_outside_executable(self):
        with patch.dict(os.environ, {'LOCALAPPDATA': str(Path('user-data').resolve())}):
            self.assertEqual(desktop_sources(), Path('user-data').resolve() / 'VSTWorld/sources.json')

    def test_occupied_port_uses_another_port(self):
        with socket.socket() as occupied:
            occupied.bind(('127.0.0.1', 0))
            occupied.listen()
            sock = reserve_port('127.0.0.1', occupied.getsockname()[1])
            try:
                self.assertNotEqual(sock.getsockname()[1], occupied.getsockname()[1])
                self.assertEqual(sock.getsockname()[0], '127.0.0.1')
            finally:
                sock.close()

    def test_browser_opens_only_when_ready(self):
        stop = MagicMock()
        stop.wait.return_value = False
        response = MagicMock()
        response.__enter__.return_value.status = 200
        with patch('vstworld.__main__.urllib.request.urlopen', side_effect=[OSError(), response]), patch('vstworld.__main__.webbrowser.open') as browser:
            open_when_ready('http://127.0.0.1:8787', stop)
            browser.assert_called_once_with('http://127.0.0.1:8787')

    def test_stopping_does_not_open_browser(self):
        stop = threading.Event()
        stop.set()
        with patch('vstworld.__main__.webbrowser.open') as browser:
            open_when_ready('http://127.0.0.1:8787', stop)
            browser.assert_not_called()
