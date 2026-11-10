"""Verifica o .exe com dados temporários, sem consultar fontes externas."""
import json
import argparse
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import urllib.request


parser = argparse.ArgumentParser()
parser.add_argument('exe', nargs='?', type=Path, default=Path(__file__).resolve().parent.parent / 'dist/VSTWorld.exe')
exe = parser.parse_args().exe.resolve()
with tempfile.TemporaryDirectory(prefix='vstworld-smoke-') as folder:
    env = dict(os.environ, LOCALAPPDATA=folder)
    for name in ('VSTWORLD_SOURCES', 'VSTHOUSE_SOURCES'):
        env.pop(name, None)
    with socket.socket() as reserved:
        reserved.bind(('127.0.0.1', 0))
        port = reserved.getsockname()[1]
    base = f'http://127.0.0.1:{port}'
    for attempt in range(2):
        log_path = Path(folder) / f'run-{attempt}.log'
        with log_path.open('w') as log:
            process = subprocess.Popen([str(exe), '--no-browser', '--port', str(port)],
                                       cwd=folder, env=env, stdout=log, stderr=log)
            try:
                for _ in range(200):
                    if process.poll() is not None:
                        raise RuntimeError(log_path.read_text())
                    try:
                        with urllib.request.urlopen(base + '/api/health', timeout=1) as response:
                            health = json.load(response)
                            assert health['app'] == 'VSTWorld' and health['version']
                        break
                    except OSError:
                        time.sleep(.1)
                else:
                    raise RuntimeError('O executável não iniciou a tempo')
                for route in ('/', '/sources', '/static/app.js', '/static/item.js', '/static/filters.js', '/static/i18n.js', '/static/locales.json'):
                    with urllib.request.urlopen(base + route, timeout=3) as response:
                        assert response.status == 200
                with urllib.request.urlopen(base + '/api/source-presets', timeout=3) as response:
                    assert any(source['id'] == 'plugins4free' for source in json.load(response))
                with urllib.request.urlopen(base + '/static/item.html', timeout=3) as response:
                    page = response.read().decode('utf-8')
                    assert 'translation-provider' in page and 'LibreTranslate local' in page and 'Ollama local' in page
                request = urllib.request.Request(base + '/api/source-detect-ai', method='POST',
                    data=b'{"url":"https://127.0.0.1/"}', headers={'Content-Type':'application/json'})
                with urllib.request.urlopen(request, timeout=3) as response:
                    assert json.load(response)['source'] is None
                with urllib.request.urlopen(base + '/api/source-config', timeout=3) as response:
                    config = json.load(response)
                assert config['sources'][0]['id'] == 'vsthouse'
                assert any(source['id'] == 'plugins4free' and source['enabled'] for source in config['sources'])
                if attempt == 0:
                    config['sources'][0]['name'] = 'Persistence smoke test'
                    request = urllib.request.Request(base + '/api/source-config',
                        data=json.dumps(config).encode(), method='POST',
                        headers={'Content-Type': 'application/json', 'Origin': base})
                    with urllib.request.urlopen(request, timeout=3) as response:
                        assert response.status == 200
                else:
                    assert config['sources'][0]['name'] == 'Persistence smoke test'
                directory = 'VSTWorld Experimental' if '-dev' in health['version'] else 'VSTWorld'
                assert (Path(folder) / directory / 'sources.json').exists()
                print(f'PASS .exe: inicialização {attempt + 1}, interface e configuração')
            finally:
                subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                process.wait(timeout=10)
