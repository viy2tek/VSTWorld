# Detecção por URL

`vstworld.discovery.detect_source(url, existing_sources, transport=None)` inspeciona HTML público e devolve uma proposta de fonte, verificações e uma explicação em português. Não salva nem altera `sources.json`.

A URL precisa ser HTTPS pública. A inspeção reutiliza `Catalog.fetch`, incluindo limite de resposta, tempo limite, transporte com validação de DNS, restrição dos redirecionamentos aos hosts permitidos e política de robots. Para um domínio novo, apenas o host exato informado entra na lista permitida e `respect_robots` começa como verdadeiro. Links externos encontrados no HTML nunca ampliam essa lista. Para uma fonte já cadastrada, preserva ID, seletores, hosts, nome, opções e política existentes.

Uma URL de detalhes também serve: a inspeção começa na raiz do mesmo domínio e depois consulta a página fornecida. Procura um formulário nativo GET ou POST com campo de pesquisa reconhecível e preserva campos ocultos. Não envia formulários com senha, upload ou outros campos editáveis, nem formulários externos. Usa parte de um título realmente observado para executar uma pesquisa não vazia e confere se um título compatível apareceu na resposta.

Há reconhecimento limitado de blocos uCoz (`.eBlock` / `.eTitle a`) e WordPress (`article` / `h2 a`), somente quando essas estruturas existem no HTML consultado. Os seletores de download também dependem de links observados. Não há promessa de compatibilidade universal: páginas que exigem JavaScript, login, CAPTCHA ou outro layout podem resultar em `source: null` e verificações explicando a lacuna. Uma proposta parcial pode ser devolvida quando há evidência dos seletores mas a busca não pôde ser confirmada; o resultado informa isso.

Os estados têm alcance limitado: `verified` confirma o fato descrito na mensagem, `unverified` indica ausência de evidência, e `blocked` indica uma consulta interrompida ou recusada. Confirmar o link de download significa apenas observar seu href no HTML e validar seu destino permitido; nenhum instalador, torrent ou outro arquivo é consultado. A paginação só é confirmada como link observado; a próxima página não é percorrida. Datas e conteúdo completo não são inferidos por esta rotina.

## Inspeção real

Em 08/11/2026, a inspeção pública de `https://vsthouse.ru/` recebeu HTTP 200 e observou o formulário `GET /search/`, campo `q` com limite de 30 caracteres e campo oculto `t=0`. Encontrou `.eBlock` com `.eTitle a`. A pesquisa real por `Steinberg - Yamaha` trouxe títulos compatíveis. A página de detalhes de Yamaha Omnivocal recebeu HTTP 200 e continha `a.sprite` com href `/load/0-0-0-41735-20`.

Essas consultas usaram a fonte VSTHouse já cadastrada, que tem `respect_robots=false` por opção existente. Essa exceção não é copiada para novos domínios. Não foi observado link seguro de próxima página nessa busca. O destino do download não foi requisitado; disponibilidade, conteúdo e segurança do arquivo permanecem sem verificação.

## Verificação local

`python -m unittest tests.test_discovery` cobre formulário nativo, GET/POST, uCoz/WordPress, URL de detalhes, preservação de configurações, robots, links externos, formulário com senha, paginação, pesquisa sem resultado compatível e ausência de download. Os testes usam transporte HTTP simulado; a inspeção real acima é uma observação pontual, sujeita a mudanças do site.
