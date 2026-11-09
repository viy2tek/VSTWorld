# Inspeção das fontes — 8 de novembro de 2026

Inspeção HTTP pontual, sem baixar instaladores nem o conteúdo de torrents. Nenhum extrator foi implementado ainda.

## EveryTune local

Referência lida em `../EveryTune`: `README.md`, `pyproject.toml`, `requirements.txt`, `DESIGN.md`, `everytune/app.py`, `everytune/storage.py` e `everytune/sources/custom.py`.

O projeto usa Python, FastAPI, Uvicorn, HTTPX, BeautifulSoup e SQLite. Serve uma interface local pelo navegador, consulta fontes e possui conectores declarativos GET/POST com seletores HTML. A interface atual usa também Bend na geração de alguns artefatos. Não é necessário importar essa cadeia de build para reproduzir o fluxo de consulta em um projeto menor. Não modificar o EveryTune.

## VSTHouse: observações diretas

| Requisição/elemento | Observado | Limite da evidência |
| --- | --- | --- |
| `https://vsthouse.org/` | Falha de resolução DNS no ambiente local; timeout pela ferramenta web | Não prova indisponibilidade em outras redes |
| `https://vsthouse.ru/` | GET retornou o catálogo HTML; páginas indexadas de `.org` já apontavam links para `.ru` | Não foi verificado um redirecionamento de `.org` para `.ru`; não presumir equivalência permanente |
| Formulário da home | `method=get`, `action=/search/`, campo `q`, `maxlength=30`, campo oculto `t=0`; botão com nome `sfSbm` | Limite visual não comprova limite do servidor; a consulta de teste funcionou sem `sfSbm` |
| Busca `GET /search/?q=Reaper&t=0` | HTTP 302 para o mesmo endereço com `&_ck=1`; cookie `ucz_h`; cliente com cookies e redirecionamentos obteve HTML com título `Reaper - Поиск` | Sessão e comportamento podem mudar; não há evidência de API pública |
| Resultado de busca | `.eBlock`, título em `.eTitle a`; resposta informou itens 1–100 de 319 para a consulta de teste | Quantidades são uma observação datada, não uma constante do conector |
| Paginação de busca | Links `.swchItem`; próximo `.swchItem-next`, URL `//vsthouse.ru/search/?q=Reaper&t=0&p=2;md=` | Preservar a URL fornecida; não confundir com paginação da home |
| Paginação da home | Link `/?page2`; há também manipulador JavaScript `spages` | GET de `/?page2` respondeu HTTP 200; o conteúdo da segunda página não foi comparado item a item |
| Página de detalhe | Um item público em `/load/.../14-1-0-41731` continha `a.sprite[href="/load/0-0-0-41731-20"]` com título de download | Apenas um item de detalhe foi inspecionado; não generalizar para todos os itens |
| Download intermediário | GET `/load/0-0-0-41731-20` retornou HTTP 301 para `/_ld/417/41731_Krosper-Hard_Fa.torrent` | A rota altera cookies/contadores do site; resolver apenas ao solicitar download |
| Arquivo de destino | HEAD no destino retornou HTTP 200, `application/octet-stream`, 27.838 bytes | Não foi baixado nem validado o conteúdo; extensão e cabeçalhos não comprovam integridade, licença ou segurança |
| Recursos alheios ao catálogo | HTML inclui scripts de publicidade e serviços externos | Não executar scripts nem servir HTML da origem dentro do app |

Há também um formulário Yandex na home. Ele usa um serviço terceiro e não deve substituir a busca nativa no aplicativo self-hosted.

A [FAQ](https://vsthouse.org/faq), disponível pela indexação web, recomenda palavras completas. Isso é orientação publicada pelo site; não foram feitos testes comparativos de radical, acentuação, ordenação ou operadores. Para preservar o comportamento, encaminhar o texto digitado sem reescrever termos ou inventar filtros de relevância.

## Robots, termos e disponibilidade

O GET direto de [robots.txt](https://vsthouse.ru/robots.txt) retornou, entre outras linhas:

```text
User-agent: *
Allow: /*?page
Disallow: /*?
Disallow: /search/
```

Isso declara uma restrição à consulta automatizada da busca. O [RFC 9309, seção 1](https://www.rfc-editor.org/rfc/rfc9309.html#section-1) esclarece que regras de robots não constituem autorização de acesso. Também não são uma licença para copiar ou distribuir arquivos. A política proposta do aplicativo é respeitar essas regras e mostrar a razão quando uma fonte não puder ser consultada. A busca interna do VSTHouse não pode ser prometida como operacional sob essa política enquanto a restrição persistir; precisa de permissão apropriada do operador ou de uma alternativa autorizada.

As [regras publicadas](https://vsthouse.org/index/0-2) reservam ao operador a possibilidade de restringir acesso e alterar/remover conteúdo. O [rodapé](https://vsthouse.ru/) pede link ativo para o original ao copiar material. Não foi identificada autorização expressa para este agregador. Não se afirma que algum download específico seja autorizado ou ilícito; disponibilidade pública e nome do arquivo não resolvem essa questão.

## O que falta verificar antes de habilitar o conector

- Acesso automatizado permitido para a busca escolhida.
- Segunda página real da busca, consulta vazia e busca sem resultados, com fixtures de teste.
- Estrutura visual em navegador: nesta etapa foi inspecionado HTML/HTTP, não a aparência renderizada.
- Variações de detalhes/downloads: arquivo direto, link externo, link expirado, login ou CAPTCHA. Não criar suporte fictício para fluxos não observados.
- Campos de categoria e imagem e sua consistência entre busca, listagem e detalhe.

Self-hosted elimina a dependência de uma plataforma de hospedagem para rodar a aplicação. Consultas ao vivo e arquivos externos continuam dependendo da rede e dos sites de origem.

## Verificação após implementação — mesma data

- Aparência renderizada inspecionada em navegador: barra superior escura, marca centralizada, painel branco, campo de busca e lista de resultados. O app mantém essa organização geral com tipografia própria; não copia o logotipo/imagens nem promete equivalência pixel a pixel.
- Links de navegação da home identificados: VSTi `/load/2`, VST `/load/10`, samples/presets `/load/25`, aplicativos `/load/13`. O HTML usa HTTP nesses links; os mesmos caminhos em HTTPS foram testados pelo conector e retornaram 10 registros extraídos por seção.
- A home retornou 10 registros. Seguir seu próximo link produziu outros 10 e alterou o primeiro título, confirmando navegação real além da primeira página.
- A busca `Reaper` pelo app resultou em mensagem de restrição de robots; não foi enviada à rota de busca pelo conector. O formulário/resultados documentados acima foram investigados pontualmente antes da implementação, não usados como autorização para consultas contínuas.
- A inspeção de arquivos de um item recente pelo app retornou zero links e aviso de restrição de robots. Isso é uma limitação real da fonte sob a política aprovada; não é um teste de download bem-sucedido.
- Parsing de busca/paginação, resolução de arquivo/torrent, falhas de fontes, POST, limites e validação de URLs foram exercitados com HTTP simulado. Essas verificações não demonstram funcionamento universal em sites reais.
- Nenhum arquivo torrent/instalador teve seu conteúdo baixado. Docker não está instalado no ambiente; Dockerfile/Compose foram preparados, sem execução de contêiner.

## Revisão da política e investigação REA — 8 de novembro de 2026

O usuário solicitou rever o bloqueio local para permitir a pesquisa pública. A configuração agora oferece `respect_robots` por fonte, padrão verdadeiro para fontes novas. A fonte VSTHouse está explicitamente configurada com falso. As constatações anteriores sobre robots continuam válidas; o que mudou é a política do aplicativo, não o arquivo do site nem uma permissão concedida pelo operador.

Uma consulta HTTP direta a `https://vsthouse.ru/search/?q=Reaper&t=0`, com cookies de sessão e redirecionamentos normais, retornou 302 e depois 200, sem login ou CAPTCHA nessa observação. O HTML retornado tinha 50 links de título em `.eBlock .eTitle a` e um link de próxima página com `p=2;md=`. Essa contagem é uma observação datada e pode variar.

Foi produzida uma captura HAR mínima em `artifacts/vsthouse-search.har`, sem cookies, conteúdo HTML ou cabeçalhos de autenticação. Ela registra URLs, status e redirecionamento observados pelo cliente HTTPX; não é uma captura da aba do usuário, e tempos não foram medidos. O REA analisou offline seus dois registros usando `inspect_web_network_capture`, evidência `ev_a8db883ea92ea6f005508aad031cdaf21c16a5ef310022c03056409e0513f9aa`, SHA-256 `9a8fa27a3bf1d6b199ba27fc543a2fd5e442f504b641b2be32ee463415404b48`. O parsing de títulos foi verificado separadamente no HTML em memória, não inferido da captura sem corpo.

A sessão REA confirmou Ghidra 12.1.4 disponível. Não houve decompilação: este fluxo apresenta HTML/HTTP, não um binário nativo do servidor. Não foi escolhido um executável local sem relação com a busca para simular o uso do Ghidra.

Não foram removidos limites de taxa/tamanho/tempo, validação HTTPS/DNS público, allowlist de hosts nem verificações de redirecionamento. Não há contorno de autenticação ou CAPTCHA, nem garantia de que o servidor sempre aceitará consultas.

Validação ao vivo pelo endpoint local após a alteração: `Reaper` retornou status `ok` com 50 itens; a segunda página também retornou 50 itens e seu primeiro URL diferiu da primeira. São contagens das páginas carregadas, não comprovação do total de registros existentes na origem. Os testes de regressão mantêm a política restritiva quando `respect_robots=true` e verificam que desativá-la não libera redirecionamentos para IP privado.
