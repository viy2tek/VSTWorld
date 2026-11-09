# VSTWorld — desenho mínimo para revisão

## Objetivo e escopo

Aplicativo self-hosted, para uso pessoal, com consulta unificada a fontes configuradas e acesso aos links/arquivos disponibilizados por elas. Interface em português, campo de pesquisa dominante, resultados em lista, navegação e paginação. Reproduzir a lógica da busca nativa encaminhando a consulta, sem simular relevância local. Aproximar a organização visual da origem após conferir a aparência renderizada.

Não incluir autenticação multiusuário, administração elaborada, streaming, fila de torrents, cache avançado nem espelhamento dos arquivos. O aplicativo não executa instaladores. Um `.torrent` é exibido como torrent e depende de um cliente externo para obter seu conteúdo.

## Abordagens

1. **Consultas ao vivo:** Python/FastAPI, HTML/CSS/JS local, conectores declarativos em JSON, paginação por fonte. Menor implementação, preserva a busca da origem, depende da disponibilidade e permissões de cada site. **Escolhida pelo usuário.**
2. **Índice SQLite:** importar metadados e pesquisar localmente. Permite consultas offline aos registros importados, mas exige atualização do catálogo e deixa de reproduzir a busca original. Não selecionada.

## Decisões propostas de implementação

- Um processo Python serve a API e a interface. Python acompanha a arquitetura observada no EveryTune; interface estática evita outra cadeia de compilação. Bibliotecas propostas: FastAPI/Uvicorn, HTTPX e BeautifulSoup. Não copiar o sistema inteiro do EveryTune.
- Sem banco de dados nesta versão: JSON persiste a definição das fontes; os resultados existem durante a consulta. SQLite só será necessário se houver pedido de biblioteca/histórico persistente. Sem Postgres.
- `sources.json`: identificador, nome, habilitação, URL/base e domínios permitidos, método/parâmetros de busca, seletores de resultado/título/link, próximo link e seletor de download no detalhe. Novos sites com HTML compatível entram por configuração; sites com protocolos diferentes exigem um conector específico. Não prometer compatibilidade universal.
- Busca concorrente com limite pequeno, timeout, limite de tamanho de resposta e intervalo por fonte. Falha numa origem não apaga os resultados das outras. Exibir origem, erro e estado explicitamente.
- Paginação independente por fonte, seguindo o link real extraído. Não inventar total global, ordenação global nem deduplicação por títulos parecidos. Cada item mantém atribuição e link para a página original.
- O detalhe apresenta somente dados extraídos e links de download identificados. Não incorporar scripts, anúncios, pop-ups, iframes ou HTML remoto. Texto via `textContent`; URLs com esquemas e domínios validados.
- Resolver rota intermediária somente quando o usuário solicitar arquivos; identificar extensão/metadados como informados pela origem. Somente destino final de arquivo, torrent ou magnet pode aparecer como download. Uma página externa ainda não resolvida deve aparecer como limitação, nunca como download direto: ela pode reintroduzir anúncios. Sem proxy de arquivos nem cliente BitTorrent, conforme a opção “link ou arquivo” do pedido.
- Respeitar `robots.txt`, inclusive redirecionamentos; não contornar login, CAPTCHA ou bloqueios. No estado observado, a busca VSTHouse declara restrição a automação. O app precisa apresentar esse bloqueio honestamente; a integração interna operacional exige resolver essa restrição com o operador. Um atalho para a busca original não conta como cumprir a busca interna.
- A API aceita identificadores configurados e referências de resultados, não uma URL arbitrária enviada pelo navegador. Validar destinos públicos e cada redirecionamento para evitar acesso à rede interna; limitar requisições e tratar DNS/timeout. A configuração local é confiável, o conteúdo remoto não.
- Logs detalhados no desenvolvimento, sem cookies ou segredos. Servidor local em `127.0.0.1`; Compose publica a porta no loopback. Para servidor remoto, documentar acesso por túnel/rede privada ou reverse proxy protegido, pois não haverá autenticação própria.
- Dockerfile e Compose com configuração montada como somente leitura. Nenhuma dependência de SaaS em execução. Acesso à internet continua necessário para consultar fontes.

## Arquivos e alcance

Pacote Python com servidor, cliente HTTP e conector HTML; interface em `static/`; `sources.json`; Dockerfile/Compose; dependências fixadas; testes de parsing, paginação, falhas isoladas e validação de URLs; README de execução Windows/Linux/Docker; relatório de inspeção e limites. Projeto novo, sem callers existentes, migração de dados ou alterações no EveryTune. Não usar Bend nesta versão.

## Verificação necessária

Fixtures mínimas derivadas da estrutura realmente observada, testes de busca e próxima página com HTTP simulado e checagem do fluxo API/interface. Validar estado vazio, falha de fonte, conteúdo malicioso e destino privado. Verificar a UI em navegador quando disponível e executar Docker se o ambiente dispuser de daemon. Separar claramente testes simulados de verificações ao vivo.

## Limite que afeta a entrega

A inspeção confirmou formulário, resultados e rota de um torrent no domínio `.ru`; `.org` falhou no ambiente. Falta verificar a aparência renderizada e os demais fluxos. Além disso, a restrição de automação impede prometer agora uma busca VSTHouse interna funcional respeitando a política proposta. Não entregar um conector bloqueado como se satisfizesse integralmente o pedido. Ver detalhes e referências em `docs/INSPECAO.md`.

Desenho aprovado pelo usuário em 08/11/2026 (“vamos em frente”). A implementação e os limites verificados estão no README e no relatório de inspeção.
