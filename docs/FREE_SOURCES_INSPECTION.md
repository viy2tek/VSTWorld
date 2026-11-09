# Inspeção de fontes gratuitas

Data: 09/11/2026 (UTC). Inspeção HTTP pública com `User-Agent: VSTWorld`, `Accept-Encoding: identity`, intervalo de pelo menos um segundo nas verificações pelo Catalog. Nenhum login, CAPTCHA, binário, torrent ou instalador foi usado. Após autorização da coordenação, um POST de resolução foi feito para obter JSON; somente HEAD consultou o arquivo resultante, sem leitura do corpo binário.

## Plugins4Free: compatível com catálogo após ajuste mínimo

- Origem: https://plugins4free.com/ — GET 200 HTML.
- Política: https://plugins4free.com/robots.txt — 200 `text/plain`, `User-agent: *` e `Disallow:` vazio. Configuração proposta mantém `respect_robots=true`.
- Busca: https://plugins4free.com/search?term=piano — GET 200 `text/html`, 80 resultados. A página de busca não tem formulário HTML; o campo `#searchInput` e o JavaScript documentam `term`. Não exige execução do JavaScript: a mesma URL já entrega cards no HTML. Parâmetro `ajax=1` produz JSON com `html` e `count`, mas não é necessário nem deve ser usado nesta integração. GET `/search/` redireciona para `/search`.
- Cards: `a.plugin-card`; título `.plugin-name`; resumo `.plugin-fx`; a URL está no próprio card. O parser atual apenas busca links descendentes e extrai zero resultados. Ajuste exato: quando `link_selector == ':scope'`, usar o próprio `node`; conservar o comportamento dos demais seletores.
- Paginação: a busca observada retorna os 80 resultados em um único HTML, sem próximo link, cursor ou parâmetro de paginação anunciado. `next_selector=null`; não inventar parâmetros. Isso não garante que a fonte nunca mude ou limite buscas mais amplas.
- Seções anunciadas pela navegação e verificadas por HTTP: `/newplugins` 200, `/hosts` 200. Depois do ajuste `:scope`, o Catalog real extraiu dez itens em cada seção: primeiro `Inner Pitch FE` em Recentes, `AirRack` em Hosts; nenhum próximo link extraído pela configuração.
- Ficha: https://plugins4free.com/plugin/970 — GET 200. `h1.plugin-title`; conteúdo `.plugin-detail`; texto `#VSTDescription`; sistema/formato em `.label-group`; imagem `img.plugin-main-img`; vídeo em `.video-container iframe`. O extrator atual identifica o título, um metadado de formato e um vídeo; não identifica a imagem principal, sistema, versão ou instalação neste layout.
- Downloads (primeira inspeção): os três controles `a.download-item` têm `href="#"` e `onclick="startDownload(...)"`. A função pública usa POST `/download` com JSON (`plugin_id`, `filename`) e token CSRF para obter `data.url`. Antes da resolução, HEAD do destino literalmente anunciado (`/plugin/970#`) confirmou 200 `text/html`, corpo não lido. Isso é página, não arquivo. Isso confirma que o `href` sozinho não resolve o arquivo; nenhum endereço deve ser inferido do nome.
- Resolução autorizada, testada sem baixar: GET da ficha na mesma sessão `httpx` recebe cookies `XSRF-TOKEN` e `plugins4free-session`. **Não há meta CSRF**; o token está no script literal `'X-CSRF-TOKEN': '...'`. Os controles declaram `startDownload(event, 970, '4Front_E-Piano_x64.zip')`. POST `https://plugins4free.com/download` com JSON `{"plugin_id":970,"filename":"4Front_E-Piano_x64.zip"}`, cabeçalhos `X-CSRF-TOKEN` extraído e `Accept: application/json`, retornou 200 `application/json`, `{"url":"https://plugins4free.com/get_plug/4Front_E-Piano_x64.zip"}`. Nenhum script foi executado.
- HEAD de https://plugins4free.com/get_plug/4Front_E-Piano_x64.zip, com robots aplicado e `headers_only=True`, retornou 200 `application/zip`, `Content-Length: 25013956`, sem `Content-Disposition`. Mesmo domínio permitido. **Um arquivo foi identificado por cabeçalhos; zero bytes de seu corpo foram lidos**. Não chamar GET de arquivo no teste.
- Mudança mínima adicional: adaptador explícito Plugins4Free, acionado somente na fonte configurada; selecione `a.download-item[onclick]`, valide sintaxe estrita dos argumentos literais, obtenha token literal da ficha, envie POST JSON na mesma sessão e passe a URL do JSON por `Catalog.url`/allowlist antes da verificação HEAD já existente. Não avaliar JavaScript, construir URL presumida de arquivo ou aceitar domínios novos automaticamente. Preservar política robots, limite de corpo JSON, timeouts, intervalo e notices de erro.

`artifacts/free-sources.json` contém uma definição completa validada por `Source.model_validate`, com `model_dump`, `download_adapter="plugins4free"` e `download_selector="a.download-item[onclick]"`; é proposta para busca, detalhes e resolução verificada de arquivos. O suporte `:scope` já foi verificado na busca real; a integração de arquivos usa o adaptador explícito de downloads testado abaixo. A fixture `tests/fixtures/plugins4free.html` é sintética e cobre cards-âncora e downloads JS que só podem aparecer como arquivos após resolução e verificação de cabeçalhos.

## VST Warehouse: catálogo acessível, downloads não compatíveis

- O navegador de pesquisa retornou 403, porém HTTP normal com o mesmo User-Agent do app retornou 200; isso não exigiu bypass, login ou navegador furtivo.
- https://vstwarehouse.com/robots.txt — 200 texto, bloqueia somente `/wp-admin/` e permite `/wp-admin/admin-ajax.php`. Busca e fichas públicas permitidas.
- Formulário real: GET `https://vstwarehouse.com/`, parâmetro `s`.
- https://vstwarehouse.com/?s=piano — 200 HTML, dez `article` por página; títulos `.entry-title a`. Próxima página `a.next.page-numbers` aponta para https://vstwarehouse.com/page/2/?s=piano; GET confirmado 200, outros dez artigos, primeiro `PSP PianoVerb`.
- Ficha https://vstwarehouse.com/d/zvenigorod-toy-ussr-piano/ — 200 HTML, título `h1.entry-title`, descrição `.entry-content [itemprop="description"]`.
- O botão `a.edd-free-download` tem href `#edd-free-download-modal`, não URL de arquivo. Não existe modal com esse ID no HTML recebido; a página carrega integração Easy Digital Downloads. Não submetemos formulários nem acionamos checkout. Não há arquivo diretamente anunciado para validar por HEAD; o fragmento aponta novamente à página HTML.
- Não incluída em `free-sources.json`: nenhum download direto foi validado e não se deve inventar resolver EDD ou introduzir cadastro/checkout neste trabalho. Poderia futuramente ser uma fonte apenas de catálogo, com essa limitação visível.

## Verificação e limites

Foram utilizados os modelos e o transporte público existentes, sem editar código compartilhado. A tentativa inicial real de `Catalog.search('plugins4free', 'piano')` retornou zero itens exclusivamente pelo card ser a própria âncora. Ficha e downloads foram testados com referência ao item público real: título `4Front E-Piano`, um metadado, um vídeo, zero imagens e zero arquivos; aviso existente de ausência de links. Após o ajuste `:scope`, o Catalog real confirmou 80 itens para `piano`, primeiro `4Front E-Piano`, sem próxima página. A resolução posterior de um arquivo por POST JSON + HEAD foi confirmada acima.

Não é necessário adicionar suporte AJAX de busca, executar JS, hosts externos, dependências ou IA. Somente o POST JSON de resolução de download observado é necessário para links integrados. Melhorias futuras de detalhes (metadados rotulados sem dois-pontos adjacentes e imagem principal fora de galeria) exigem evidência e testes separados se forem incluídas no escopo. Este documento não valida licença ou segurança de cada produto e não afirma que gratuitos significam livres de restrições.

Verificação da fixture sintética: dois cards com link no próprio nó e três botões JS; definição de Source carregada e seletores conferidos por asserts.

## Verificação final do adaptador integrado

Após o suporte `:scope` e `download_adapter="plugins4free"`, execução real pelo mesmo `Catalog` confirmou busca `piano` com 80 itens, detalhe do primeiro (`4Front E-Piano`) e três arquivos válidos por POST JSON seguido de HEAD, sem notices: `4Front_E-Piano_win.zip`, `4Front_E-Piano_x64.zip` e `4fepiano-osx.zip`, todos sob `https://plugins4free.com/get_plug/`. O resultado foi conferido por asserts (80 itens, três arquivos, URLs na rota observada). Nenhum corpo de arquivo foi lido. Nenhuma fonte VST Warehouse foi adicionada.
