# Histórico

## 0.2.0-dev — experimental, não publicada

- Interface reorganizada: busca em primeiro plano, filtros/categorias recolhidos, cadastro com feedback contextual e downloads próximos ao título do item.
- Estilos compartilhados, foco por teclado, controles maiores e layouts adaptados para celular e tablet, sem novas dependências.

- Filtros de sistema, formato, arquitetura, tipo, desenvolvedora, versão e datas, com alcance explícito nos resultados carregados.
- Sistema/formato do Plugins4Free enviados à busca nativa; paginação vinculada aos filtros.
- Leitura opcional e interrompível de fichas para completar dados, mantendo títulos como única informação da listagem.
- Filtros, seleção de fontes e ordenação preservados na URL ao navegar entre resultados e detalhes.
- IA local opcional acionada por botão, instruções de Ollama e perfil Docker opt-in; sem dependência de modelo para buscas normais.
- Plugins4Free: busca, seções, detalhes e adaptador de download JSON/CSRF com validação de cabeçalhos.
- Fontes prontas no editor; Musicmakers disponível apenas como candidata desativada com limitações explícitas.
- Dados do executável experimental em pasta separada, copiando a configuração estável apenas na primeira execução.
- Identificação de campos por tipo, rótulos e contexto, sem depender apenas de uma lista de nomes.
- Captura de filtros selecionados, opções marcadas, controles associados e botão de envio.
- Avisos de formulários ambíguos ou ainda não representáveis; nomes repetidos não são descartados silenciosamente.
- Musicmakers: formulário e resposta da busca observados, sem validar integração de downloads ou paginação.

## 0.1.0-beta.1 — 2026-11-08

- Primeira beta pública com o nome VSTWorld, independente da VSTHouse.
- Executável Windows x64 único, abertura automática no navegador e configurações persistentes.
- Migração da pasta de dados da versão local anterior, sem sobrescrever as fontes do VSTWorld.
- VSTHouse como única fonte incluída: pesquisa ao vivo, seções e paginação da origem.
- Resultados somente com títulos; detalhes internos com ficha técnica, instruções, galeria, vídeos e links identificados.
- Cadastro por URL com identificação assistida e configurações técnicas recolhidas.
- Testes em CI e teste de inicialização/persistência do executável.

Novas fontes serão avaliadas separadamente após esta versão. Não há índice offline, cliente torrent, autenticação ou atualização automática.
