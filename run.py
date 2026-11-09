from vstworld.__main__ import main
import logging
import sys


if __name__ == '__main__':
    try:
        main()
    except Exception:
        logging.exception('Não foi possível iniciar o VSTWorld')
        if getattr(sys, 'frozen', False) and sys.platform == 'win32':
            import ctypes
            ctypes.windll.user32.MessageBoxW(None,
                'Não foi possível iniciar o VSTWorld. Consulte vstworld.log na pasta de configuração.',
                'VSTWorld', 0x10)
        else:
            raise
