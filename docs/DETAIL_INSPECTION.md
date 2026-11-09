# Item-page extraction evidence

Inspected through the existing `Catalog.fetch` / `PublicTransport` and
`Catalog.search('vsthouse', 'Waves')` on 2026-11-08 (local date). The configured
source already had `respect_robots: false`. Only text HTML was fetched; no
download binaries, installers or source scripts were executed.

## Omnivocal

Source: https://vsthouse.ru/load/semply_presety/zvukovye_ehffekty/steinberg_yamaha_omnivocal_v_1_0_5_vsti3_x64_vr_vokalnyj_sintezator/38-1-0-41735

- `.eTitle` supplies the item title; `.eText` scopes the product content.
- Metadata is one block separated by `<br>`, beginning with `Дата Выпуска:
  5.11.2026`, `Версия: 1.0.5`, `Разработчик: Steinberg`, and including `Формат:
  VSTi3`, `Разрядность: 64bit`, `Системные требования: Windows 10\ Cubase 16`,
  `Размер: 423.6 MB`. The live extraction returned nine facts.
- The installation spoiler is titled `Team VR`, not “Installation”. It contains
  explicit numbered install/run steps. `.uSpoilerText` is hidden by CSS but its
  text is already in the HTML. Extraction returned six paragraphs in order.
  Single `<br>` stays a newline; blank `<br><br>` becomes a paragraph boundary.
- `Подробнее` contains marketing and is omitted. `Скриншоты` contains two gallery
  thumbnails; the unlinked product cover above the facts is not a screenshot.
- `_uVideoPlayer` includes the explicit URL
  `https://www.youtube.com/watch?v=n6UNGaLyos8`; only ID `n6UNGaLyos8` is returned.
  Nothing is executed or embedded by the extractor.
- Gallery #1 thumbnail:
  `https://i129.fastpic.org/thumb/2026/1105/8d/966542ef64e480965c065daee47b938d.jpeg`.
  Its anchor href is `https://u.to/bcfhIg`; its title explicitly supplies viewer
  `https://fastpic.org/view/129/2026/1105/966542ef64e480965c065daee47b938d.jpg.html`.
  #2 href is `https://u.to/bMfhIg` with viewer
  `https://fastpic.org/view/129/2026/1105/7c426528c95e66b80121c77cc0b25442.jpg.html`.
  A viewer URL is not a confirmed original image. `original_available` remains
  false until another layer obtains an actual original URL. No `/big` URL is
  constructed from the thumbnail path.

## Waves

The first Waves search hit was actually Wave Arts; it was not mistaken for Waves.
The first matching `Waves - Ultimate` hit was:
https://vsthouse.ru/load/vst/svedenie_i_mastering/waves_ultimate_v2024_11_29_vst_vst3_aax_04_12_2024_r2r_nabor_plaginov/11-1-0-37229

- Nine facts extracted, including release `04.12.2024`, version `2024.11.29`,
  developer `Waves`, formats `VST, VST3, AAX`, `64bit`, `Win 10+`, and `8.35 GB`.
- The `Установка` spoiler returned 24 ordered paragraphs, including headings,
  source bullet lines, Windows paths, prerequisites and final instructions.
  `Что нового?`, `Особенности`, and `R2R Note` were not copied as installation.
  The extractor reports what the source says; it does not run those instructions.
- `VIDEO DEMOS` contains four explicit short YouTube URLs, IDs:
  `erzVpZjUQBc`, `gRWrJKO8_t4`, `OnVHcre9um0`, `qdXeLhF_rkM`.
- `Скриншоты` contains nine thumbnails with explicit ibb viewer titles, such as
  thumbnail `https://i.ibb.co/8dKqrqD/1.jpg`, title `https://ibb.co/8dKqrqD`,
  href `https://u.to/JgcMIQ`. The seven marketing images inside the “what's new”
  spoiler were excluded. None of the viewer links alone proves original size.

## Scope and uncertainty

The supplied live pages did not expose explicit `datePublished`, `dateModified`
or article-time metadata. Omnivocal shows unlabeled `06.11.2026, 11:17` in the
header, distinct from its release date. The extractor intentionally returns null
page dates for that HTML rather than claiming that unlabeled timestamp is a
publication or modification date. `extract_page_dates` supports explicit article
meta/itemprop/time fields for sources which provide them. Release dates stay in
factual metadata and are never used as page dates.

`extract_details(body, page_url, selector=None)` returns the agreed JSON-ready
contract. Instruction blocks keep `kind`, `text` or `items`, and safe `links`.
Real HTML lists retain order and explicit ordered-list start/value numbers;
source plain-text bullet lines remain text with their original markers. Links
use HTTPS public URL validation shared with the existing transport. Actual DNS,
redirect validation, image decoding and viewer resolution belong to the caller.
The parser never returns source HTML or event handlers.

The tests use reduced synthetic structural fixtures with observed fields and
markup, not full remote pages with advertising and user comments. Limits: 2 MB
input, 40 facts, 10 installation sections, 100 blocks per section, 8000 characters
per paragraph/item, 30 links per block, 20 video IDs, 40 gallery images, 4096
characters per URL. Default extraction requires a recognized article container;
it does not fall back to indiscriminately reading the full body. Other layouts
may need an explicit content selector or evidence-based selector support.

Portuguese factual labels are also recognized without translating their values,
including release date, version, developer, publisher, site, format, bit depth,
architecture, requirements and size. Requirements continuation is restricted to
technical labels such as `RAM:`/`CPU:`/`OS:` and explicit operating-system or
runtime/version lines. An unrelated sentence ends continuation, preventing a
following product pitch from becoming part of the requirements field.

Verification: tests were first run before the module existed (expected import
failure); the two subsequent Portuguese-label/requirements regression tests also
failed before their fixes. All eight focused extraction tests passed. Live output was checked
against both inspected HTML pages for facts, paragraphs, video IDs and galleries.
## Integração verificada no aplicativo

Em 08/11/2026, o endpoint interno retornou para Omnivocal nove campos técnicos, uma seção de instalação, um vídeo, duas imagens e um link de download identificado. Para Waves Ultimate, item 37229, retornou nove campos, uma seção de instalação, quatro vídeos e nove imagens; a primeira imagem ampliada retornou HTTP 200, `image/jpeg`, 344.901 bytes. Não foram testadas todas as nove imagens.

Na primeira screenshot do Omnivocal, a miniatura realmente recebida tem 121×150 pixels. O visualizador do hospedeiro forneceu um endereço de imagem com 568×703 pixels, 50.763 bytes, confirmado pelo proxy e pela ampliação no navegador. O endereço `/big/` foi lido do HTML real do Fastpic, não construído trocando o caminho da miniatura. Respostas do hospedeiro variaram durante a inspeção; indisponibilidade continua possível.

O navegador confirmou ficha técnica sem texto promocional, instalação preservada, zero iframes do YouTube antes do clique e um player após a ação. O player carregou o título “Getting Started with Omnivocal Pro & Basic”. Isso verifica a incorporação deste vídeo; não garante reprodução de todo vídeo, região ou sessão.

No VSTHouse, datas de lançamento foram extraídas como fatos do produto. O timestamp isolado da página não teve sua semântica de publicação/atualização comprovada e não foi usado para oferecer uma ordenação fictícia. Ordenação local foi testada com datas explicitamente marcadas em respostas simuladas, mantendo itens sem data ao final.

O proxy só devolve MIME de imagem permitido, após validar o tipo base exato, inclusive respostas 206; páginas HTML de hospedeiros são analisadas internamente e não repassadas ao navegador. HTML com links para arquivos privados, imagens fora dos tipos permitidos e respostas falsas de imagem foram cobertos por regressões.
