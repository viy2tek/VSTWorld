"""Gera o executável Windows usando o ambiente Python atual."""
from pathlib import Path
import argparse
import subprocess
import sys
from importlib.metadata import distributions


root = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser()
parser.add_argument('--experimental', action='store_true', help='Gerar em dist/experimental sem substituir a beta')
args = parser.parse_args()
notices = ['VSTWorld — avisos das dependências do ambiente de build\n'
           'As licenças abaixo pertencem aos respectivos componentes; não licenciam o código do VSTWorld.\n']
notices.append((Path(sys.base_prefix) / 'LICENSE.txt').read_text(encoding='utf-8'))
for dist in sorted(distributions(), key=lambda item: item.metadata['Name'].lower()):
    notices.append(f'\n=== {dist.metadata["Name"]} {dist.version} ===\n')
    for file in dist.files or []:
        if any(part.lower().startswith(('license', 'copying', 'notice', 'authors')) for part in file.parts):
            path = dist.locate_file(file)
            if path.is_file():
                notices.append(path.read_text(encoding='utf-8', errors='replace'))
notices_path = root / 'build/THIRD_PARTY_NOTICES.txt'
notices_path.parent.mkdir(exist_ok=True)
notices_path.write_text('\n'.join(notices), encoding='utf-8')
subprocess.run([
    sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onefile', '--console',
    '--name', 'VSTWorld', '--distpath', str(root / ('dist/experimental' if args.experimental else 'dist')),
    '--collect-submodules', 'uvicorn',
    '--add-data', f'{root / "vstworld/static"}:vstworld/static',
    '--add-data', f'{root / "sources.json"}:.', str(root / 'run.py'),
    '--add-data', f'{root / "vstworld/presets.json"}:vstworld',
    '--add-data', f'{notices_path}:.',
], cwd=root, check=True)
