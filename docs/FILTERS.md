# Filtros de pesquisa

Disponíveis na beta 0.2.0-beta.1: sistema (Windows/macOS/Linux), formato (família VST, VST2, VST3, AU, AAX, Kontakt), arquitetura (32/64 bits), tipo (instrumentos, efeitos, samples/bibliotecas, presets, softwares/DAWs), desenvolvedora, versão e intervalo de publicação ou atualização da página. A ordenação também distingue publicação de atualização.

Os resultados continuam mostrando somente títulos. Campos de filtro são extraídos de rótulos técnicos e tokens explícitos do título; informações ausentes ficam desconhecidas. O prefixo comercial do título não vira desenvolvedora. `VST` sem número não é convertido em VST2. `Win64 + OSX` não comprova macOS 64 bits. Data de lançamento do produto não vira data de publicação/atualização.

## Alcance

Todos os controles refinam os **itens carregados**. Não existe varredura ou índice global. Itens sem informação necessária para um filtro ativo ficam de fora e a interface informa quantos podem depender de mais dados. Campo conhecido e incompatível é diferente de campo desconhecido.

Na busca de texto da configuração incluída do Plugins4Free, parte dos filtros também é enviada ao servidor da origem:

| Controle | Parâmetro observado |
|---|---|
| Windows | `os[]=win32&os[]=win64` |
| Windows 32/64 | `os[]=win32` ou `os[]=win64` |
| macOS | `os[]=allmacos` |
| Linux | `os[]=linux` |
| Família VST / VST2 / VST3 | `fmt[]=vst`; a distinção 2/3 continua local e exige evidência |
| AU / AAX | `fmt[]=au` / `fmt[]=aax` |

Arquitetura sem Windows, tipo, Kontakt, desenvolvedora, versão, datas e ordenação permanecem locais. A arquitetura de uma variante Windows não é transferida para macOS/Linux. Navegação por seções refina apenas os itens dessas páginas, sem presumir os parâmetros da busca de texto. Para reenviar os controles à origem, clique em **Pesquisar com estes filtros**. Alterar um campo já refina a lista atual imediatamente.

Verificação real em 2026-11-09: o HTML/JS de `https://plugins4free.com/search?term=piano` declara `toggleSearchOs`, `toggleSearchFmt` e os parâmetros `os[]`/`fmt[]`. Sem `ajax=1`, a resposta é HTML compatível com o catálogo. A amostra sem filtro retornou 80 cartões; Linux retornou 1 (`PIANO S`); Windows 64 + VST retornou 43. No aplicativo, acrescentar desenvolvedora `4Front` mostrou 3 dos 43 itens. As contagens são observações pontuais, não tamanhos fixos do catálogo. Nenhum comportamento equivalente foi presumido no VSTHouse.

## Ler fichas e voltar dos detalhes

**Ler fichas dos itens carregados** consulta detalhes, até três pedidos de cada vez, respeitando os intervalos de cada fonte. Não consulta downloads nem baixa produtos. A leitura mostra progresso, pode ser interrompida e só tenta novamente fichas ainda não confirmadas. Campos conhecidos na listagem não são apagados quando a ficha os omite. Não lê páginas seguintes automaticamente; use a paginação para ampliar a amostra.

Fontes selecionadas, filtros, consulta/seção e ordenação ficam na URL. Abrir um item e voltar preserva os controles, mas refaz a consulta; fichas lidas apenas na página anterior não são persistidas e podem precisar ser lidas novamente. Não foi acrescentado cache ou banco de dados.

Se a origem não informar publicação ou atualização de modo verificável, essas ordenações ficam indisponíveis. Um intervalo exige datas confirmadas e não substitui a ausência de dados por datas de lançamento.

## Testes

`tests/test_filtering.py` cobre normalização, ausência de dados, relações plataforma/arquitetura, parâmetros enviados e vínculo dos filtros com a paginação. `tests/ui-filters.cjs` cobre correspondência, datas válidas e preservação da URL. `tests/ui-filter-loader.cjs` cobre limite da fila, cancelamento e preservação de fatos. Os demais testes de API, paginação e editor continuam em execução.
