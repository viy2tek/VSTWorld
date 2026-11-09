"""Bandeja do executável Windows; dependências só são carregadas no desktop."""
import logging
import threading


def run_tray(server, sock, url, stop, open_app):
    import pystray
    from PIL import Image, ImageDraw

    image = Image.new('RGB', (64, 64), '#285b64')
    draw = ImageDraw.Draw(image)
    draw.line([(10, 18), (20, 46), (32, 20), (44, 46), (54, 18)], fill='white', width=6)

    def open_window(icon, item):
        threading.Thread(target=open_app, daemon=True).start()

    def close(icon, item):
        server.should_exit = True
        icon.stop()

    icon = pystray.Icon('VSTWorld', image, f'VSTWorld — {url}', menu=pystray.Menu(
        pystray.MenuItem('Abrir VSTWorld', open_window, default=True),
        pystray.MenuItem('Encerrar', close)))
    errors = []

    def serve():
        try:
            server.run(sockets=[sock])
        except BaseException as error:
            logging.getLogger(__name__).exception('Falha ao iniciar o servidor local')
            errors.append(error)
        finally:
            stop.set()
            icon.stop()

    worker = threading.Thread(target=serve, daemon=True)

    def setup(tray):
        tray.visible = True
        worker.start()

    try:
        icon.run(setup=setup)
    finally:
        server.should_exit = True
        stop.set()
        if worker.ident is not None:
            worker.join(timeout=10)
    if errors:
        raise RuntimeError('Não foi possível iniciar o servidor local. Consulte vstworld.log.') from errors[0]
