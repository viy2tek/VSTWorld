# VSTWorld

**Seu catálogo de plugins, instrumentos e bibliotecas de áudio, no seu servidor.**

Pesquise em diferentes fontes por uma única interface. Abra cada resultado para consultar a ficha técnica, instruções, imagens, vídeos e links de download identificados, sem os anúncios incorporados das páginas de origem.

[![Verificações Windows e Linux](https://github.com/viy2tek/VSTWorld/actions/workflows/checks.yml/badge.svg?branch=main)](https://github.com/viy2tek/VSTWorld/actions/workflows/checks.yml)

**[Baixar para Windows x64](https://github.com/viy2tek/VSTWorld/releases/download/v0.2.0-beta.1/VSTWorld-windows-x64.exe)** · [Notas da beta 0.2.0-beta.1](https://github.com/viy2tek/VSTWorld/releases/tag/v0.2.0-beta.1) · [Reportar problema](https://github.com/viy2tek/VSTWorld/issues)

![Catálogo do VSTWorld com busca por piano, filtros ativos e resultados somente com títulos](docs/images/catalogo.jpg)

*Interface real da beta 0.2.0: consulta ao Plugins4Free com filtros. A contagem representa os itens carregados, não o tamanho total do catálogo.*

## Conteúdo

[Recursos](#recursos) · [Começar no Windows](#começar-no-windows) · [Como usar](#como-usar) · [Fontes](#fontes) · [Executar pelo código](#executar-pelo-código) · [Docker](#docker) · [Configuração e backup](#configuração-e-backup) · [Limitações](#limitações) · [Desenvolvimento](#desenvolvimento) · [Documentação](#documentação) · [Licença](#licença)

## Recursos

- **Busca unificada:** consultas ao vivo e paginação independente por fonte; resultados mostram somente títulos.
- **Filtros:** sistema operacional, formato, arquitetura, tipo, desenvolvedora, versão e datas verificáveis da página.
- **Detalhes dentro do app:** informações técnicas e instruções de instalação, sem comentários, recomendações ou parágrafos promocionais.
- **Imagens e vídeos:** galeria ampliável e player do YouTube carregado somente ao solicitar reprodução.
- **Fontes configuráveis:** cadastro por link, verificações da identificação e parâmetros técnicos em Configurações avançadas.
- **IA local opcional:** ajuda a propor configurações de fontes desconhecidas; a busca normal funciona sem IA.
- **Self-hosted:** executável Windows, execução pelo código ou Docker. Sem conta, banco de dados ou serviço pago obrigatório.

O VSTWorld consulta os sites e apresenta os links identificados. Nenhum plugin, instalador de produto ou torrent está incluído no aplicativo. É um projeto independente, sem afiliação à VSTHouse ou aos fabricantes.

## Começar no Windows

Não precisa instalar Python, Node ou Docker.

1. [Baixe VSTWorld-windows-x64.exe](https://github.com/viy2tek/VSTWorld/releases/download/v0.2.0-beta.1/VSTWorld-windows-x64.exe).
2. Salve o arquivo em uma pasta e abra com dois cliques.
3. Aguarde o navegador abrir e faça sua primeira pesquisa.

Mantenha a janela do programa aberta enquanto usa o app. Para encerrar, feche essa janela ou pressione **Ctrl+C** nela. Fechar somente a aba do navegador não encerra o servidor.

O aplicativo tenta usar `http://127.0.0.1:8787`. Se a porta estiver ocupada, o executável escolhe outra e abre o endereço correto. O binário é para **Windows x64**, não tem assinatura digital e pode gerar um aviso do Windows. O arquivo `SHA256SUMS.txt` está disponível nos [arquivos do release](https://github.com/viy2tek/VSTWorld/releases/tag/v0.2.0-beta.1).

### Atualizar uma versão anterior

Feche o programa, baixe o novo executável e abra-o. As fontes pessoais são preservadas; não existe atualização automática.

Se o Plugins4Free não aparecer numa instalação antiga, abra **Fontes → Fontes prontas para adicionar → Plugins4Free → Salvar fonte**. As fontes incluídas no novo binário não substituem silenciosamente a sua configuração.

## Como usar

1. Digite o nome de um item e pressione **Enter**. No VSTHouse, use palavras completas.
2. Expanda **Fontes** para escolher os sites consultados, ou **Navegar por categorias** para abrir uma seção da origem.
3. Use **Filtros** para refinar a busca. **Ler fichas dos itens carregados** busca dados adicionais, sem baixar produtos; a leitura pode ser interrompida.
4. Clique em um título para abrir os detalhes, ampliar imagens, solicitar a reprodução de vídeos e acessar os downloads identificados.
5. Use **Próxima página** para acrescentar resultados daquela fonte. **Voltar aos resultados** refaz a consulta preservando os filtros e as fontes na URL.

Os filtros locais e a ordenação consideram os **itens carregados de cada fonte**. Parte dos filtros também é enviada à busca nativa do Plugins4Free. Itens sem os dados exigidos por um filtro ficam de fora, com indicação na tela. Publicação da página, atualização da página e lançamento do produto são datas diferentes; o app não inventa datas ausentes. [Entenda o alcance dos filtros](docs/FILTERS.md).

## Fontes

| Fonte | Estado na beta 0.2.0-beta.1 |
| --- | --- |
| **VSTHouse** | Fonte principal incluída: busca, seções, detalhes e identificação de downloads. |
| **Plugins4Free** | Incluída: busca, seções, detalhes e integração de links de arquivo. |
| **Musicmakers** | Configuração candidata, **desativada**. Busca e downloads ainda não constituem uma integração completa. |
| Outros sites | Exigem inspeção e, em alguns casos, um conector específico. Veja o [roadmap](docs/ROADMAP.md). |

### Adicionar um site

Abra **Fontes → Adicionar fonte**, cole o endereço e clique em **Identificar site**. O app tenta reconhecer a busca, os resultados, a paginação, os detalhes e os downloads. Confira o que foi verificado antes de clicar em **Salvar fonte**.

A identificação não é universal. Sites que dependem de JavaScript, login, CAPTCHA ou fluxos de download diferentes podem exigir configuração manual ou uma integração própria. Seletores, método HTTP, parâmetros, testes e JSON ficam em **Configurações avançadas**, recolhidas por padrão. [Referência de configuração](docs/GUIA_TECNICO.md#configurar-fontes-em-detalhe).

### IA local opcional

Em **Fontes → IA local opcional**, é possível usar Ollama com um modelo instalado separadamente. O app não instala modelos nem consulta IA automaticamente. As propostas precisam passar pelas verificações do site antes de preparar uma fonte.

[Configurar Ollama no Windows ou Docker](docs/LOCAL_AI.md). A integração tem testes com respostas simuladas; a qualidade de um modelo real ainda não foi medida.

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

## Docker

Com o repositório clonado, Docker Engine 28+ e Docker Compose instalados:

```sh
docker compose up --build -d
```

Abra [http://127.0.0.1:8787](http://127.0.0.1:8787). Para acompanhar os logs, use `docker compose logs -f`; para parar, `docker compose down`.

A configuração fica no volume `source-data`. O Compose publica a porta somente no loopback e o app **não possui autenticação própria**. Para acesso remoto, consulte o [guia de Docker, backup e acesso ao servidor](docs/GUIA_TECNICO.md#docker-e-acesso-remoto). O fluxo Docker está documentado, mas ainda não foi executado nesta preparação.

## Configuração e backup

| Modo de execução | Arquivo de fontes |
| --- | --- |
| Executável da beta pública | `%LOCALAPPDATA%\VSTWorld\sources.json` |
| Código local | `sources.json` na pasta do projeto, ou caminho de `--sources` / `VSTWORLD_SOURCES` |
| Docker | `/data/sources.json`, no volume `source-data` |
| Builds antigas `0.2.0-dev` | `%LOCALAPPDATA%\VSTWorld Experimental\sources.json`, separado da beta pública |

Para fazer backup, feche o app e copie o JSON. No Docker, use `docker compose cp vstworld:/data/sources.json ./sources-backup.json`. `docker compose down` preserva o volume; `docker compose down -v` remove os dados persistidos.

Mantenha **uma instância por configuração**. O editor aplica alterações salvas sem reiniciar o servidor; recarregue outras abas do catálogo. Editar o JSON manualmente exige reiniciar.

O executável também reconhece a configuração do nome antigo `VSTHouse Brasil`, copiando-a na primeira execução quando o destino ainda não existe e o JSON é válido. Variáveis `VSTHOUSE_SOURCES` e `VSTHOUSE_ALLOWED_HOSTS` continuam como alternativas às variáveis `VSTWORLD_*`.

## Limitações

- **Precisa de internet para consultar fontes.** Hospedar o app localmente não cria um catálogo offline.
- **A extração depende dos sites.** Layouts, domínios, cookies e bloqueios podem mudar; encontrar um formulário não confirma downloads ou paginação.
- **Links externos têm regras próprias.** O app não contorna login, CAPTCHA ou respostas 403/429, nem verifica segurança, integridade ou licença dos produtos. Torrents precisam de um cliente externo.
- **Conteúdo permanece no idioma da fonte.** Alguns rótulos técnicos são apresentados em português; não há tradução automática dos artigos.
- **Mídia depende da origem.** Se só houver miniatura, o app informa a limitação. O YouTube é carregado ao reproduzir e pode ter anúncios ou restrições próprios.
- **Referências expiram.** Reiniciar o app ou trocar as fontes pode exigir uma nova pesquisa. Não há favoritos, índice persistente, streaming ou download em lote.

Novas fontes respeitam `robots.txt` por padrão. A configuração incluída do VSTHouse usa `respect_robots: false`, desativando o bloqueio local por solicitação do responsável pelo projeto; isso não modifica restrições reais do servidor nem comprova autorização de uso. Respeite as licenças e os termos das origens. [Inspeção e referências técnicas](docs/INSPECAO.md).

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
```

No Linux, use `.venv/bin/python` no primeiro comando. O [workflow Checks](https://github.com/viy2tek/VSTWorld/actions/workflows/checks.yml) executa os testes em Windows/Linux e constrói e verifica o executável no Windows. A beta 0.2.0-beta.1 passou por 103 testes Python, quatro verificações JavaScript e teste de inicialização/persistência do binário. [Evidências e limites](docs/RELEASE_0_2.md).

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

Manutenção: [@viy2tek](https://github.com/viy2tek). Próximas possibilidades estão no [roadmap](docs/ROADMAP.md).

## Documentação

| Guia | Conteúdo |
| --- | --- |
| [Guia técnico](docs/GUIA_TECNICO.md) | Campos JSON, seletores, operação em servidor, limites e referências técnicas |
| [Identificação de fontes](docs/DISCOVERY.md) | Métodos de inspeção e casos ainda não representáveis |
| [Filtros](docs/FILTERS.md) | Alcance, dados ausentes, datas e parâmetros nativos |
| [IA local](docs/LOCAL_AI.md) | Configuração opcional do Ollama no Windows e Docker |
| [Inspeção do VSTHouse](docs/INSPECAO.md) | Requisições, paginação e política da fonte principal |
| [Outras fontes](docs/FREE_SOURCES_INSPECTION.md) | Evidências de integração e limitações observadas |
| [Detalhes e mídia](docs/DETAIL_INSPECTION.md) | Fichas, instalação, imagens e vídeos |
| [Design](docs/REDESIGN.md) | Auditoria da interface e decisões do redesign |
| [Histórico](CHANGELOG.md) | Alterações por versão |

## Licença

O VSTWorld é distribuído sob a [licença MIT](LICENSE). Copyright © 2026 [viy2tek](https://github.com/viy2tek).

Os avisos de terceiros incluídos no executável referem-se às dependências. Conteúdo e arquivos das fontes mantêm suas próprias condições de uso.

## Referências deste README

A organização foi orientada pelas referências abaixo; os recursos e comandos descritos foram conferidos no próprio projeto.

- [Template de iuricode](https://github.com/iuricode/readme-template/blob/main/repositorio/exemplo-01.md): apresentação, requisitos, instalação, uso e contribuição.
- [LEIA-ME ou te devoro — GitHub/DEV](https://dev.to/github/leia-me-ou-te-devoro-como-escrever-um-bom-readme-5hl4): descrição clara, instruções úteis, exemplo visual e licença explícita.
- [Awesome README](https://github.com/matiassingers/awesome-readme): navegação, screenshot e acesso direto aos recursos principais.
- [Utrecht University — README Files](https://utrechtuniversity.github.io/workshop-computational-reproducibility/chapters/readme-files.html): comandos reproduzíveis, estrutura curta e links para documentação detalhada.
