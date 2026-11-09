import threading
import types
import unittest
from unittest.mock import Mock, patch

from vstworld.tray import run_tray


class TrayTests(unittest.TestCase):
    def exercise(self, fails=False):
        started, stopped, opened, finished = (threading.Event() for _ in range(4))
        server = types.SimpleNamespace(should_exit=False)

        def serve(**kwargs):
            started.set()
            if fails:
                raise OSError('startup failed')
            while not server.should_exit:
                stopped.wait(.01)
            finished.set()

        server.run = serve
        case = self

        class Icon:
            def __init__(self, name, image, title, menu):
                self.menu = menu

            def run(self, setup):
                setup(self)
                case.assertTrue(started.wait(1))
                if not fails:
                    self.menu[0](self, None)
                    case.assertTrue(opened.wait(1))
                    self.menu[1](self, None)
                case.assertTrue(stopped.wait(1))

            def stop(self):
                stopped.set()

        modules = {'pystray':types.SimpleNamespace(Icon=Icon, Menu=lambda *items:items,
            MenuItem=lambda title,action,**kwargs:action),
            'PIL':types.SimpleNamespace(Image=Mock(), ImageDraw=Mock())}
        stop = threading.Event()
        with patch.dict('sys.modules', modules):
            if fails:
                with self.assertLogs('vstworld.tray', level='ERROR'), self.assertRaises(RuntimeError):
                    run_tray(server, Mock(), 'http://vstworld.local', stop, opened.set)
            else:
                run_tray(server, Mock(), 'http://vstworld.local', stop, opened.set)
                self.assertTrue(finished.is_set())
        self.assertTrue(server.should_exit)
        self.assertTrue(stop.is_set())

    def test_menu_opens_and_shutdown_stops_server(self):
        self.exercise()

    def test_startup_failure_removes_tray_and_reports_error(self):
        self.exercise(fails=True)
