# Revisão da beta 0.2.0-beta.1 — 2026-11-09

Publicação do redesign e dos recursos que estavam na branch de desenvolvimento.

- Catálogo, cadastro de fontes e detalhes reorganizados; estilos locais compartilhados, foco por teclado e layouts adaptáveis. [Decisões e verificação visual](REDESIGN.md).
- Nove campos de filtro e ordenação por datas verificáveis, com alcance explícito nos itens carregados; subconjunto de filtros enviado à busca do Plugins4Free. [Cobertura](FILTERS.md).
- VSTHouse e Plugins4Free incluídos; Musicmakers permanece candidata desativada. Demais sites não são anunciados como integrados. [Inspeção das fontes](FREE_SOURCES_INSPECTION.md).
- IA local opcional, sem modelo instalado ou consultado automaticamente; sem dependência de IA na busca normal. [Configuração](LOCAL_AI.md).
- Versão pública usa `%LOCALAPPDATA%/VSTWorld/sources.json`, preservando o JSON da beta anterior. Configurações de builds antigas `-dev` continuam em pasta separada. Fontes novas não são inseridas no JSON pessoal automaticamente; podem ser adicionadas pelas fontes prontas.
- Executável único Windows x64, sem instalador; servidor local abre o navegador e deve permanecer em execução. Checksums acompanham o release.

## Evidência local desta preparação

103 testes Python e quatro scripts JavaScript passaram com a versão `0.2.0-beta.1`. Executável reconstruído e teste de inicialização, rotas, configuração e persistência passou em duas execuções com dados temporários. A revisão visual anterior cobre 1280×900, 768×1024, 390×844 e 320×740; busca e links de download de exemplo foram verificados sem baixar produtos.

O workflow Checks executa testes no Windows e Linux e produz/testa o executável no Windows. A publicação exige verificar seu resultado para o mesmo commit antes de disponibilizar os arquivos.

## Limites mantidos

Sem atualização automática, assinatura digital, autenticação ou cliente torrent. Mantenha uma instância por arquivo de configuração. Dados ausentes não são inferidos e a extração depende dos sites. Ollama real, Docker e dispositivos móveis físicos não foram testados nesta preparação. Os avisos das dependências estão no pacote; eles não constituem licença própria para o código do aplicativo.
