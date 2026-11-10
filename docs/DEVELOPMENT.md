# Desenvolvimento e execução pelo código

[Voltar ao README](../README.md)

Execute os comandos abaixo na raiz do repositório.

## Executar pelo código

Use **Python 3.14**, versão usada no workflow de testes, e Git para clonar o projeto. Node é necessário apenas para executar os testes JavaScript, não para usar o app.

### Windows — PowerShell

```powershell
git clone https://github.com/viy2tek/VSTWorld.git
cd VSTWorld
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m vstworld
```

### Linux

```sh
git clone https://github.com/viy2tek/VSTWorld.git
cd VSTWorld
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m vstworld
```

Abra [http://127.0.0.1:8787](http://127.0.0.1:8787). A execução pelo código permanece no terminal e não abre o navegador automaticamente. Use **Ctrl+C** para parar. No Windows, não é preciso ativar a venv ou alterar a política do PowerShell.

Para outra porta ou configuração, acrescente `--port 8790 --sources /caminho/sources.json` ao comando de execução. Use um arquivo JSON válido no caminho informado. O macOS não foi verificado nesta versão.

## Desenvolvimento

A base segue a arquitetura do EveryTune: **Python, FastAPI, HTTPX, BeautifulSoup e HTML/CSS/JavaScript locais**. Configuração em JSON; sem banco de dados ou build de frontend.

```text
vstworld/       Servidor, conectores, validação e interface em static/
sources.json   Configuração inicial das fontes
scripts/       Empacotamento e teste do executável
tests/         Testes Python, JavaScript e amostras HTML
docs/          Guias, inspeções, decisões e roadmap
```

### Verificar alterações

No Windows, com a venv preparada e Node instalado:

```powershell
.\.venv\Scripts\python -m unittest discover -s tests -v
node tests/ui-pagination.cjs
node tests/ui-source-editor.cjs
node tests/ui-filters.cjs
node tests/ui-filter-loader.cjs
node tests/ui-i18n.cjs
node tests/ui-translation.cjs
```

No Linux, use `.venv/bin/python` no primeiro comando. O [workflow Checks](https://github.com/viy2tek/VSTWorld/actions/workflows/checks.yml) executa os testes em Windows/Linux e constrói e verifica o executável no Windows. A beta 0.3.0-beta.1 passou por 118 testes Python, seis verificações JavaScript e teste de inicialização/persistência do binário. [Evidências e limites](RELEASE_0_3.md).

### Gerar o executável Windows

```powershell
.\.venv\Scripts\python -m pip install -r requirements-build.txt
.\.venv\Scripts\python scripts/build.py
.\.venv\Scripts\python scripts/smoke_exe.py
```

A saída é `dist/VSTWorld.exe`. O build usa [PyInstaller](https://pyinstaller.org/en/stable/runtime-information.html), inclui os arquivos da interface, fontes iniciais e avisos das dependências em `THIRD_PARTY_NOTICES.txt`. Não gera um binário para Linux ou macOS. `--no-browser` desativa a abertura automática do navegador no executável.

### Contribuir e pedir ajuda

Abra uma [issue](https://github.com/viy2tek/VSTWorld/issues) com versão do app, sistema operacional, fonte e passos para reproduzir o problema. Sugestões de novas fontes devem incluir exemplos públicos de busca e detalhes.

Para propor uma alteração, crie um fork, trabalhe em uma branch e envie um pull request com o que mudou e como foi verificado. Novos conectores precisam de inspeção documentada, amostras HTML e testes; não apresente um site apenas cadastrado como uma integração validada.

Manutenção: [@viy2tek](https://github.com/viy2tek). Próximas possibilidades estão no [roadmap](ROADMAP.md).
