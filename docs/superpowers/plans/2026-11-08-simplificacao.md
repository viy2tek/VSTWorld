# Simplificação do catálogo — plano de implementação

Requisitos: solicitação detalhada do usuário de cadastro por link, detalhes internos sem marketing, galeria/vídeos e ordenação honesta. Execução autorizada diretamente.

- [x] Inspecionar Omnivocal e Waves, campos técnicos, instalação, vídeo e galeria. Documentar evidência e limites.
- [x] Implementar detecção por URL, validando formulário, resultados e candidatos a downloads. Não salvar automaticamente uma inferência não validada.
- [x] Extrair detalhes em módulo separado, com dados estruturados, sem servir HTML remoto.
- [x] Adicionar APIs de detecção/detalhes e referências opacas para imagens públicas; limitar tipos, tamanho e redirecionamentos.
- [x] Simplificar cadastro; recolher todos os campos técnicos em avançado. Preservar editor existente e proteção contra perda de alterações.
- [x] Exibir somente títulos nos resultados e abrir detalhes internos. Ordenação por datas só com datas verificáveis e alcance explícito.
- [x] Testar contratos HTTP simulados, interface, busca/detalhes reais, tamanho original das imagens e vídeo sob demanda. Documentar o que ficou não verificado.

Arquitetura: manter FastAPI, HTTPX, BeautifulSoup, JSON e frontend estático. Sem nova dependência, banco ou LLM externo. Uma tarefa independente para extração de detalhes e outra para detecção; integração/API/UI pelo agente principal.

Verificação final: 56 testes Python, regressões JS de paginação/ordenação e editor, compileall, checagens de sintaxe JS e pip check passaram. Omnivocal e Waves testados ao vivo; identificação por domínio e salvamento com Avançadas fechadas conferidos no navegador. A galeria exibiu 568×703 contra miniatura de 121×150 e o iframe do vídeo só surgiu após clique. Docker não disponível; sem execução de contêiner.

Revisão independente corrigida com regressões: MIME de imagem validado pelo tipo base em respostas de sucesso; visualizador sem extensão resolvido pelo Content-Type; atualização não tratada como publicação. Descoberta limitada a HTML reconhecível com verificações explícitas, sem alegar compatibilidade universal.
