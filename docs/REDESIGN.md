# Interface — redesign de 9 de novembro de 2026

## Auditoria e alcance

Revisados os três HTML, os três CSS, scripts de busca/filtros/fontes/detalhes e testes de interface.

| Página | Problema observado | Decisão |
| --- | --- | --- |
| Catálogo | Marca duplicada, breadcrumb sem ação, filtros e explicações antes dos resultados | Cabeçalho único, busca primeiro; fontes, filtros e categorias recolhidos |
| Resultados | Ordenação distante do título; pouco destaque ao título clicável | Ordenação no cabeçalho; linha inteira do título clicável |
| Fontes | Mensagens longe do endereço; fontes prontas pouco visíveis | Feedback dentro do editor, fontes prontas fora das avançadas; parâmetros e IA recolhidos |
| Item | Downloads após ficha, instalação e mídia | Downloads ao lado da ficha no desktop e antes dela no celular |
| Todas | Escalas, cores e tamanhos inconsistentes; foco incompleto | Tokens compartilhados, controles de 44 px, foco visível incluindo selects e textareas |

Não há mudanças de rotas, APIs, conectores, dados persistidos ou dependências. IDs e associação do botão Salvar ao formulário foram preservados. Avisos e ajuda continuam acessíveis por seções expansíveis.

## Direção e sistema visual

- Manter nome e marca em vermelho discreto/azul petróleo. Base quase branca, grafite e um azul de ação; sem gradientes, sombras decorativas ou animações de entrada.
- Fonte local Segoe UI/system-ui; base 16 px, apoio 13–14 px, título fluido 30–44 px. Sem CDN.
- Ritmo em múltiplos de 4/8 px, conteúdo limitado a 1120 px, instruções limitadas a 72 caracteres por linha.
- Superfícies planas, divisórias leves e raio de 6 px. Botões primários para pesquisar, aplicar e salvar; ações auxiliares discretas.
- Navegação única Catálogo/Fontes com página atual indicada. Retorno contextual nos detalhes conserva a busca pela URL existente.
- Filtros ativos continuam contados com painel recolhido; fontes mostram quantidade selecionada. Notas técnicas por fonte ficam sob “Sobre esta fonte”.
- Três colunas de filtros no desktop, duas no tablet, uma no celular. Editor em duas colunas apenas quando há espaço. Downloads deixam de ser fixados no mobile.

Uma troca apenas de cores manteria a hierarquia anterior. Uma nova biblioteca visual ou um menu global lateral acrescentaria manutenção sem beneficiar estes três fluxos. Foi adotada a reorganização do HTML e dos estilos existentes.

## Verificação

Os 103 testes Python e os quatro scripts de interface passaram. O resumo de filtros ganhou verificação de contagem e limpeza. O executável Windows passou pelo teste de inicialização e persistência em duas execuções.

Revisão visual no navegador em 1280×900, 768×1024, 390×844 e 320×740: catálogo vazio/preenchido, fontes selecionadas, filtros e edição/avançadas. Medidas de largura não mostraram overflow horizontal nos exemplos inspecionados. Selecionar uma fonte leva o foco ao campo do endereço, útil no celular. Salvamento verificado em uma cópia separada da configuração, sem mudar as fontes pessoais.

Busca real Plugins4Free por `piano`: 80 itens; Windows/64 bits/VST mais desenvolvedora `4Front`: três de 43 itens carregados. Detalhe `4Front E-Piano`: ficha, imagem ampliável, botão de vídeo e três links de download exibidos; nenhum produto baixado. Player externo não foi reproduzido. Exemplos ao vivo dependem da disponibilidade das fontes; não comprovam todos os produtos do catálogo, nem validação em hardware móvel real.
