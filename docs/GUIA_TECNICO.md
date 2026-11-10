# Guia técnico do VSTWorld

[Voltar ao README](../README.md)

Referência para configuração manual, operação em servidor e limites da extração. Para começar pelo executável, use o README.

## Docker e acesso remoto

Requer Docker Engine 28+ (ou Docker Desktop com essa versão do Engine) e Compose instalados:

```sh
docker compose up --build -d
docker compose logs -f
docker compose down
```

Abra `http://127.0.0.1:8787`. O editor **Fontes** salva em `/data/sources.json`, persistido no volume nomeado `source-data`. Na primeira execução, o arquivo é inicializado a partir do `sources.json` incluído no build; reinícios e novos builds preservam a configuração do volume. Depois dessa inicialização, editar o JSON da pasta do projeto não altera o volume: use o editor. Para iniciar com um JSON próprio, ajuste o arquivo antes do primeiro `docker compose up --build`.

Para copiar a configuração persistida para backup, use `docker compose cp vstworld:/data/sources.json ./sources-backup.json`. `docker compose down` preserva o volume; `down -v` apaga as fontes salvas. O processo roda como usuário sem privilégios, com sistema de arquivos somente para leitura, exceto o volume de configuração. Dependências estão fixadas em `requirements.txt`; a imagem base acompanha a série Python 3.14 e pode variar entre builds.

Para usar em servidor remoto sem abrir uma porta pública:

```sh
ssh -L 8787:127.0.0.1:8787 usuario@seu-servidor
```

Depois abra `http://127.0.0.1:8787` no computador cliente. Alternativamente, use um reverse proxy com HTTPS e controle de acesso; configure o hostname exato em `VSTWORLD_ALLOWED_HOSTS` e preserve o cabeçalho Host. **O app não tem autenticação própria.** O Compose publica somente no loopback. `--host 0.0.0.0` é usado dentro do contêiner; fora dele, muda a exposição de rede e deve ser usado apenas no ambiente pretendido.

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

## Configurar fontes em detalhe

Abra **Fontes** no menu ou [o editor local](http://127.0.0.1:8787/sources). Clique em **Adicionar fonte**, cole o link e use **Identificar site**. A inspeção tenta encontrar o formulário de busca, resultados, próxima página e links de download. Revise as verificações e clique em **Salvar fonte**. Ela não salva silenciosamente uma configuração estimada nem afirma ter validado um arquivo apenas por encontrar um link.

A identificação automática inicial suporta estruturas HTML uCoz e WordPress observadas. Não é um navegador com execução de JavaScript nem suporte universal a qualquer site. Sites desconhecidos, campos ausentes e bloqueios recebem uma explicação. Uma fonte já cadastrada preserva seus parâmetros e política de robots; resultados da inspeção parcial não substituem suas configurações silenciosamente. [Método, testes e limites da identificação](DISCOVERY.md).

Todos os campos técnicos, o teste manual e o editor JSON ficam em **Configurações avançadas**, recolhidas por padrão. Para colar uma definição completa, use **Aplicar JSON ao formulário** e depois **Salvar fonte**. Nome, habilitação, parâmetros, seletores, paginação, detalhes e datas continuam editáveis; o salvamento dispensa reiniciar.

O teste consulta a fonte com a definição atual e mostra até cinco títulos extraídos e se existe próxima página; não salva nem comprova que os downloads funcionam. Para testar a navegação, informe o identificador de uma seção. Para verificar downloads, salve a fonte e abra um resultado no catálogo. A opção **Aplicar as regras de robots.txt no app** controla a política local por fonte. Validação de destinos, intervalo mínimo e limites de resposta permanecem ativos em ambos os modos. Desmarcar não contorna login, CAPTCHA, HTTP 403/429 ou outros controles do servidor.

Salvar grava o JSON atomicamente e aplica as fontes imediatamente. Edições de outra aba são detectadas pela revisão do arquivo: recarregue antes de tentar salvar novamente. As outras abas do catálogo precisam ser recarregadas; referências antigas de arquivos/paginação expiram após a troca de configuração. Consultas em andamento podem terminar com a configuração anterior. Rode apenas um processo/worker do app para manter a aplicação imediata consistente.

Fora do Docker, o arquivo continua sendo `sources.json` na pasta do projeto (ou o caminho de `--sources`/`VSTWORLD_SOURCES`). A pasta precisa permitir escrita para o salvamento atômico. Também é possível editar esse arquivo manualmente e reiniciar. Não há credenciais nem autenticação de administração; mantenha o app no loopback ou protegido pelo acesso do servidor.

Não é necessário alterar código para sites com resultados HTML e links compatíveis. **Inspecione primeiro** o formulário/requisição real, resultados, paginação, detalhes, download, robots e termos. Não invente seletores a partir da aparência ou do nome do site.

Exemplo **fictício**, para mostrar o formato; não é um conector funcional para `example.com`:

```json
{
  "id": "minha-fonte",
  "name": "Minha fonte",
  "enabled": false,
  "base_url": "https://example.com/",
  "hosts": ["example.com", "downloads.example.com"],
  "search_path": "/pesquisa",
  "method": "GET",
  "query_param": "q",
  "params": {},
  "max_query": 200,
  "item_selector": ".resultado",
  "title_selector": "h2 a",
  "description_selector": ".resumo",
  "next_selector": "a.proxima",
  "download_selector": "a.download",
  "interval": 1.0,
  "sections": [{"id": "recentes", "name": "Recentes", "path": "/"}],
  "note": "Preencha somente depois de inspecionar a fonte."
}
```

| Campo | Comportamento |
| --- | --- |
| `id`, `name`, `enabled` | Identificador único, nome e habilitação. Até 30 fontes. Desativadas não são consultadas. |
| `respect_robots` | Booleano, padrão `true`. Quando falso, não consulta nem aplica regras de robots no app. VSTHouse está configurado como falso por solicitação expressa do usuário. |
| `base_url`, `hosts` | HTTPS, porta 443, sem credenciais; domínios exatos em minúsculas. Inclua hosts legítimos de arquivos/redirecionamentos; não há wildcard. Destinos privados são recusados mesmo na allowlist. |
| `search_path`, `method`, `query_param`, `params` | GET por query string ou POST de formulário (`application/x-www-form-urlencoded`). Sem JSON POST, JavaScript remoto ou autenticação de origem. |
| `max_query` | Limite da fonte; consultas longas geram mensagem, sem truncamento silencioso. |
| `item_selector` | Seleciona cada registro; até 100 por página. |
| `title_selector`, `link_selector` | Seletores relativos a cada registro. Por padrão, o título é o próprio link com `href`; use `link_selector` quando estiverem separados. Texto é extraído sem HTML. |
| `description_selector` | Opcional, relativo ao registro. Não injeta imagens, scripts ou iframes. |
| `detail_selector` | Opcional, região de conteúdo no detalhe. Por padrão, procura `.eText`, `articleBody`, `.entry-content` ou `article`. A extração de fatos/instruções exige estruturas reconhecíveis; não exibe texto promocional como fallback. |
| `published_selector`, `modified_selector` | Opcionais, relativos ao resultado, com data ISO em `datetime`, `content` ou texto. Informe somente quando a semântica da data estiver verificada. Por padrão, usa marcação específica de publicação/atualização, nunca um `time` genérico. |
| `next_selector` | Primeiro link com `href` para a próxima página. Segue sua URL exata por GET, inclusive após busca POST. Paginação por formulário/JavaScript exige adaptar o conector. |
| `download_selector` | Links no detalhe que apontam ao download, rota intermediária ou magnet. Até 10 candidatos; cada destino HTTP é verificado, sem baixar o corpo do arquivo. |
| `interval`, `sections`, `note` | Intervalo mínimo em segundos por fonte; navegação por páginas conhecidas; nota exibida na interface. Crawl-delay válido da origem também é considerado. |

Seletores são validados na inicialização; configuração inválida impede a abertura com uma mensagem de validação no terminal. O JSON não executa scripts. Sites com API JSON, login, CAPTCHA, conteúdo gerado apenas por JavaScript ou protocolos diferentes precisam de conectores específicos; cadastrar o domínio sozinho não basta.

## Organização e limites

- `vstworld/config.py`: formato e validação das fontes.
- `vstworld/http.py`: HTTPS público; valida DNS e fixa o IP validado na conexão, mantendo Host/TLS.
- `vstworld/catalog.py`: robots, limites, parsing, navegação e identificação de downloads.
- `vstworld/app.py`: API e arquivos estáticos; `static/`: interface.
- `tests/`: contratos HTTP com respostas simuladas, configuração e API.

Sem SQLite nesta versão porque não há índice, favoritos ou histórico persistente. Cada consulta vai às origens. Não há deduplicação por títulos parecidos, ordenação entre sites nem download em lote.

Até quatro operações simultâneas, timeout de 40 segundos por página/60 por inspeção de arquivos e limite de 2 MB de HTML por resposta. Referências de resultados/páginas duram uma hora, até 2.000 em memória, e são perdidas ao reiniciar; nesse caso, refaça a pesquisa. Só as regras de robots são mantidas por cinco minutos, não o catálogo. Logs de desenvolvimento são detalhados, sem query strings, cookies ou cabeçalhos HTTP. O processo não usa proxies de ambiente para consultar fontes.

Mudanças em layout, domínio, cookies, anti-bot e formato de download podem quebrar seletores e exigir manutenção. Zero registros extraíveis não prova ausência de conteúdo. Links são externos, podem expirar e o navegador faz sua própria conexão ao abri-los; o app não controla publicidade ou segurança fora da interface local. Self-hosted não significa busca offline: sites e rede continuam necessários.

## Detalhes, screenshots e vídeos

A extração reconhece rótulos técnicos em russo, inglês e português, evita duplicação e preserva valores e instruções da fonte. Só blocos identificados como instalação são incluídos. Se não reconhecer um campo ou uma seção, informa a ausência em vez de copiar todo o artigo. Não traduz automaticamente os textos nem garante que uma instrução esteja correta. [Páginas e estruturas verificadas](DETAIL_INSPECTION.md).

Screenshots são carregadas por referências internas, com transporte HTTPS público e limite de 8 MB por imagem. HTML do hospedeiro é analisado somente no servidor, até 2 MB; nunca é servido como imagem ao navegador. Ao ampliar, o app procura o arquivo real nos links/metadados da página do hospedeiro, inclusive links sem extensão. Não transforma automaticamente `/thumb/` em `/big/`: usa o endereço realmente observado. Exibe as dimensões recebidas e, se o original falhar, mantém a miniatura com aviso, sem alegar alta resolução. Alguns hospedeiros podem estar bloqueados ou exigir um fluxo não suportado.

Vídeos do YouTube só geram um iframe após clicar em **Reproduzir**. O player usa `youtube-nocookie.com` e uma política de referrer específica para permitir a identificação do incorporador. O player depende do YouTube, pode ter publicidade própria e pode recusar vídeos/embeds; a remoção dos anúncios da página de origem não altera o player oficial. Referências: [incorporação e modo de privacidade](https://support.google.com/youtube/answer/171780) e [parâmetros do player](https://developers.google.com/youtube/player_parameters).

## Fontes das decisões

- [FastAPI: contêineres](https://fastapi.tiangolo.com/deployment/docker/): servidor Python empacotado numa imagem própria, sem exigir plataforma de hospedagem específica.
- [HTTPX: transportes](https://www.python-httpx.org/advanced/transports/): transporte customizado para conexão controlada e MockTransport para testes sem consultar sites reais.
- [Docker: publicação de portas](https://docs.docker.com/engine/network/port-publishing/): vínculo explícito em `127.0.0.1` para acesso local.
- [RFC 9309](https://www.rfc-editor.org/rfc/rfc9309.html): regras de robots, correspondência e distinção entre regras para crawlers e autorização de acesso. A política de aplicação dessas regras é configurável por fonte; essa configuração não é uma declaração sobre a legalidade de cada uso.
- [Regras do VSTHouse](https://vsthouse.org/index/0-2), [FAQ](https://vsthouse.org/faq) e [robots consultado](https://vsthouse.ru/robots.txt): restrições, orientação de pesquisa e atribuição. Conteúdo publicamente acessível não comprova licença para reutilização ou distribuição; não foi identificada autorização expressa para este agregador.

O código fornece links, sem espelhar os arquivos. Isso reduz armazenamento e transferência no servidor local, mas mantém dependência das origens e não resolve por si só licenças ou termos. A interface usa marca e organização próprias; as fontes são apresentadas com atribuição ao original.
