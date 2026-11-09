# Musicmakers e 4Download — inspeção pública

Data: 09/11/2026. Consultas pelo `Catalog`/`PublicTransport` do projeto, User-Agent VSTWorld, intervalo de 1 s, robots ativo. Nenhum arquivo de produto/torrent baixado ou executado; nenhum login, captcha ou restrição contornado. As evidências abaixo são do HTML e dos cabeçalhos, não garantem disponibilidade futura.

## Musicmakers: parcial; não promover a fonte completa

- `GET https://musicmakers.ru/robots.txt`: HTTP 200. Regras incluem `Disallow: /*do=search`, `/*do=download`, `/*do=go`, `/engine/go.php`, `/user/`.
- `GET https://musicmakers.ru/`: HTTP 200, 58.737 bytes na primeira amostra. Formulário nativo `#q_search`, método POST, ação ausente (mesma página), campo `story`, ocultos `do=search` e `subaction=search`.
- O envio POST / não foi repetido nesta inspeção: apesar de a implementação atual checar apenas URL para robots, enviar no corpo a mesma operação proibida por query seria uma interpretação inadequada para habilitar automaticamente a fonte. Inspeção anterior do fluxo não equivale a permissão da fonte.
- Cartões: `article.shortstory`, título/link `h2.title a[href]`, resumo `.text`, data `time.date[datetime]`. Categoria pública `/vsti/` observada nos links.
- Paginação do catálogo inicial: `.page_next a[href]`, URL observada `https://musicmakers.ru/page/2/`; próxima página não requisitada. Não foi confirmada paginação de pesquisa.
- Detalhe público confirmado HTTP 200: https://musicmakers.ru/vsti/32762-steinberg-yamaha-omnivocal-v105-vsti3-x64-r2r-vokalnyj-sintezator.html
- Conteúdo `article.fullstory`, título `h1.title`, corpo `.text`, publicação `time.date[datetime]` = `2026-11-05`.
- `extract_details` atual extraiu 9 fatos (versão, desenvolvedor, formato, requisitos, tamanho etc.) e YouTube `n6UNGaLyos8`. Não extraiu data, instruções ou galeria.
- Spoilers DLE usam pares irmãos `.title_spoiler` + `.text_spoiler`, com cabeçalhos `Установка` e `Скриншоты`; conteúdo já está no HTML, sem executar ShowOrHide. O parser só conhece uCoz/details/gallery, portanto perde essas duas seções.
- Galeria tem miniaturas `https://i129.fastpic.org/thumb/...jpeg`; âncoras apontam para `https://musicmakers.ru/index.php?do=go&url=...`, proibido por robots. Não seguir nem decodificar para contornar o redirecionamento proibido. Original não confirmado.
- Download observado no HTML: `.attachment a.dow[href]`, URL `https://musicmakers.ru/index.php?do=download&id=33112`, title terminado em `.torrent`. Não foi requisitado sequer por HEAD porque robots proíbe. Extensão no title não prova MIME/arquivo acessível.

Criado `artifacts/musicmakers-source.json` como configuração experimental **desativada** (`enabled=false`, `respect_robots=true`), conforme orientação de manter uma candidata revisável. Não é fonte completa: downloads continuam restritos/não validados e não deve ser habilitada automaticamente. O envio POST foi identificado/testado em inspeção anterior do projeto, não repetido nesta inspeção. A fixture sintética `tests/fixtures/musicmakers.html` registra somente a estrutura DLE observada para testes locais do parser.

## 4Download: busca funciona; arquivo direto não confirmado

- `GET https://4download.net/robots.txt`: HTTP 200, `User-agent: *` / `Disallow:` vazio.
- `GET https://4download.net/`: HTTP 200, 77.307 bytes na primeira amostra. Formulário `#quicksearch`, POST /, `story`, ocultos `do=search`, `subaction=search`.
- Busca real `FabFilter`: POST /, HTTP 200; Catalog.search com `item_selector=.item-card`, `title_selector=a.item__link` extraiu 4 itens, inclusive os bundles Windows/MacOS e Timeless. `h2 a` não atende esta fonte; resultados usam div.item__title dentro da âncora.
- Busca real `Windows`: HTTP 200, mensagem `Found 100 responses (Query results 1 - 10)`.
- Próxima página não é link GET: `a#nextlink[href="#"]`, onclick `list_submit(2)`. O JS envia formulário GET `#fullsearch` a `/index.php` com `do`, `subaction`, `search_start`, `full_search`, `story`. Reproduzido conforme formulário/JS observado: `GET https://4download.net/index.php?do=search&subaction=search&search_start=2&full_search=0&story=Windows`, HTTP 200, mensagem `Query results 11 - 20`; primeiros títulos Ultra.Audio Ultra e iZotope Ozone. Não selecionar href="#" como próximo: Catalog o converteria para a mesma página sem preservar a busca.
- Detalhe público HTTP 200: https://4download.net/4212-cradle-everything-bundle-for-windows.html
- Título real `.page__header-title h2` (sem h1), corpo `article.page__cols-main`; metadados estruturados em `.page__list li`. Parser atual deixou título/fatos vazios, capturou YouTube `D0uceadXgEc`, perdeu galeria (não envolta em .gallery/.screenshots). Cabeçalho Screenshots e imagem com âncora `.highslide` existem no HTML.
- Download `.dl__btn` aponta para `/downloads.html#...`, incluindo nome, tamanho e URLs externas em parâmetros do fragmento. Não é arquivo direto. Página HTTP 200 HTML; HEAD também 200 `Content-Type: text/html; charset=utf-8`, sem Content-Disposition de arquivo.
- `downloads.html` usa JavaScript para ler location.hash/sessionStorage, preencher botões data-link e contar tempo. O HTML do produto contém destinos MediaFire/MEGA/GoFile/Vikingfile. Eles não foram seguidos: ver URL de espelho não prova binário acessível.
- Catalog.downloads do primeiro resultado FabFilter retornou files vazio e aviso `Link indisponível ou destino não permitido.`. `a.dl__btn` não torna esta fonte um provedor direto suportado; fragmentos multilinha podem falhar validação e os espelhos estão fora de hosts.

## Menor trabalho necessário

1. Manter Musicmakers parcial/desativado para pesquisa/download enquanto robots proibir as operações; não resolver ajustando seletor ou desligando respect_robots.
2. Se houver necessidade de detalhes Musicmakers: reconhecer pares DLE irmãos e data `time.date`, com teste usando fixture sintética; não seguir os go/download proibidos.
3. Para cadastrar 4Download como catálogo com links da página: usar seletor `.item-card` / `a.item__link`, POST story/do/subaction, declarar download não confirmado. Não marcar como download verificado somente pelo href.
4. Paginação 4Download exige converter exclusivamente a estrutura observada do formulário/list_submit em requisição GET preservando todos os parâmetros; não executar JS genérico. Alternativa mínima é não oferecer próxima página e declarar limite.
5. Título/fatos/galeria de 4Download exigem extração específica com evidência. Entregar espelhos exigiria modelo explícito de páginas externas não verificadas; não confundir espelho HTML com arquivo binário.

Não foram alterados código compartilhado, sources.json, testes existentes nem arquivos de produto. Não houve publicação.


## Triagem adicional: VSTon e PositiveRecords

Realizada em 09/11/2026, mesmas salvaguardas e cliente TLS validado.

### VSTon / VstiON

- `GET https://vston.ru/robots.txt` e `/`: HTTP 301, Location respectivamente `https://vstion.site/robots.txt` e `https://vstion.site/`. Trata-se do redirecionamento observado, não de domínio adivinhado.
- Robots canonical HTTP 200; inclui `Disallow: /?`, `/downloads/`, `/down`, `/page/`, `/wp-json/`; `Allow: /wp-admin/admin-ajax.php`. A existência desse Allow não autoriza trocar a busca bloqueada por outro fluxo para contornar a política.
- Home canonical HTTP 200, 260.497 bytes. Cartões `h2.post-card-title a`, data `.post-meta-date time[datetime]`.
- Formulário nativo `.oai-ajax-search__form`, GET `https://vstion.site/`, texto `s`, oculto `post_type=post`, vários checkboxes marcados `search_categories[]`. A busca resultaria em `/?...`, proibido por robots; não foi enviada. Além disso, o modelo atual params dict[str,str] não representa os múltiplos valores nativos com a mesma chave.
- Detalhe público HTTP 200: https://vstion.site/vst-vsti/izotope-ozone-12-advanced-v-12-2-0-vst3aax-x64-v-r/
- Href real observado: `a.Button` para `/downloads/iZotope-Ozone-12-Advanced-v.12.2.0-VST3AAX-x64-V.R.torrent`. Não foi feito HEAD/GET porque `/downloads/` é proibido por robots. A extensão torrent no href não basta para considerar arquivo acessível/validado.
- YouTube observado no iframe: `lwIuaD8O61M`.
- Resultado: catálogo/detalhe público disponível, busca e download não elegíveis com respeito às regras da fonte. Nenhuma Source criada.

### PositiveRecords

- `https://positiverecords.ru/robots.txt` e `https://www.positiverecords.ru/robots.txt` falharam com `SSL: CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate` usando PublicTransport/configuração TLS do projeto.
- Não foi possível confirmar robots nem catálogo. Não foi desativada validação TLS nem houve tentativa HTTP para contornar o erro. A causa pode ser cadeia do servidor ou ausência de CA no cliente; esta triagem não distingue as duas hipóteses.
- Resultado: fonte não validada; nenhuma Source criada.

`artifacts/additional-sources.json` não foi criado: nenhuma dessas duas fontes satisfez busca + detalhe + download permitido confirmado por cabeçalhos. Não foram geradas fixtures adicionais, pois não há integração recomendada para executar a partir destas amostras.
