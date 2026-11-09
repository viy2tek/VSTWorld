import argparse
import logging
import os
from pathlib import Path
import socket
import sys
import threading
import urllib.request
import webbrowser

import uvicorn

from .app import create_app
from . import __version__


def desktop_sources(experimental=False):
    directory = Path(os.getenv('LOCALAPPDATA', Path.home() / 'AppData/Local')) / ('VSTWorld Experimental' if experimental else 'VSTWorld')
    return directory / 'sources.json'


def migrate_sources(target):
    legacy = target.parent.parent / 'VSTHouse Brasil' / 'sources.json'
    stable = target.parent.parent / 'VSTWorld' / 'sources.json'
    if target.parent.name == 'VSTWorld Experimental' and stable.exists():
        legacy = stable
    if target.exists() or not legacy.exists():
        return
    from .config import load_sources
    load_sources(legacy)
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target.open('xb') as stream:
            stream.write(legacy.read_bytes())
    except FileExistsError:
        pass


def reserve_port(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        try:
            sock.bind((host, port))
        except OSError:
            sock.bind((host, 0))
        sock.listen(128)
        return sock
    except BaseException:
        sock.close()
        raise


def open_when_ready(url, stop):
    for _ in range(100):
        if stop.wait(0.1):
            return
        try:
            with urllib.request.urlopen(url + '/api/health', timeout=0.5) as response:
                if response.status == 200:
                    webbrowser.open(url)
                    return
        except OSError:
            continue
    logging.getLogger(__name__).error('Não foi possível abrir o navegador automaticamente: %s', url)


def main():
    parser = argparse.ArgumentParser(description='VSTWorld — catálogo local')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8787)
    parser.add_argument('--sources', help='Caminho do JSON de fontes')
    parser.add_argument('--no-browser', action='store_true', help='Não abrir o navegador ao iniciar o executável')
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error('A porta deve estar entre 0 e 65535')
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(name)s %(message)s')
    # Logs de bibliotecas HTTP podem incluir URLs, cookies e cabeçalhos remotos.
    for name in ('httpx', 'httpcore'):
        logging.getLogger(name).setLevel(logging.WARNING)
    desktop = getattr(sys, 'frozen', False)
    if not os.getenv('VSTWORLD_SOURCES') and os.getenv('VSTHOUSE_SOURCES'):
        os.environ['VSTWORLD_SOURCES'] = os.environ['VSTHOUSE_SOURCES']
    if desktop and not args.sources and not os.getenv('VSTWORLD_SOURCES'):
        target = desktop_sources(experimental='-dev' in __version__)
        migrate_sources(target)
        os.environ['VSTWORLD_SOURCES'] = str(target)
    app = create_app(args.sources)
    if not desktop:
        uvicorn.run(app, host=args.host, port=args.port, log_level='debug', access_log=False)
        return
    sock = reserve_port(args.host, args.port)
    port = sock.getsockname()[1]
    url = f'http://127.0.0.1:{port}'
    stop = threading.Event()
    print(f'VSTWorld: {url}\nFontes: {args.sources or os.getenv("VSTWORLD_SOURCES")}\nCtrl+C para encerrar.', flush=True)
    server = uvicorn.Server(uvicorn.Config(app, host=args.host, port=port,
                                         log_level='debug', access_log=False))
    if not args.no_browser:
        threading.Thread(target=open_when_ready, args=(url, stop), daemon=True).start()
    try:
        server.run(sockets=[sock])
    finally:
        stop.set()
        sock.close()


if __name__ == '__main__':
    main()
