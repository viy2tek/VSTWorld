# Revisão da primeira beta — 2026-11-08

Escopo: aplicativo pessoal self-hosted, um processo local, JSON gravável, uma fonte incluída. A revisão acompanhou busca → resultados → detalhes → imagens/downloads e cadastro → validação → gravação → troca do catálogo. Não é uma auditoria externa de segurança.

## Correções e preparação realizadas

- Marca VSTWorld em telas, títulos, API, módulo Python, executável e Docker. VSTHouse permanece como nome e ID da fonte real, para preservar as configurações.
- Cópia validada da configuração do executável anterior para a pasta VSTWorld. Não sobrescreve o destino nem remove o original. Testes cobrem migração, destino existente e JSON inválido.
- Variáveis VSTWORLD_* documentadas, mantendo alternativas VSTHOUSE_* para instalações antigas.
- Versão na API de saúde e na documentação; build reproduzível por script com dependências fixadas.
- Teste do executável verifica arquivos estáticos, uma única fonte incluída, edição e persistência após reinício, em pasta temporária.
- CI para testes em Windows/Linux e empacotamento Windows; resultado remoto deve ser consultado no GitHub antes de marcar a versão como verificada nesse ambiente.
- Avisos de dependências incluídos no pacote e checksum SHA-256 publicado junto do binário.

## Evidência local

- 62 testes Python e dois testes JavaScript passaram após a mudança de nome.
- Executável iniciou duas vezes, serviu a interface e preservou uma alteração do JSON entre execuções.
- Consulta real por Omnivocal retornou 13 títulos nesta observação. O primeiro item mostrou nove campos técnicos, instalação, duas screenshots, vídeo e um link de torrent identificado por metadados. Não foi baixado nem executado o produto.
- Sem suposições de datas: as opções de ordenação permanecem desativadas quando a origem não informa datas com significado verificável.

## Limites e melhorias seguintes

Não encontrei um novo bloqueador reproduzível nos fluxos revisados. Permanecem limites explícitos da beta:

- Deve haver apenas um processo usando o mesmo JSON. A detecção de revisão protege edições dentro da aplicação, mas não é um bloqueio entre processos. Abrir várias instâncias pode causar concorrência. Melhorar isso antes de distribuir para mais usuários é a primeira sugestão do roadmap.
- Busca ao voltar dos detalhes é refeita e a seleção personalizada de fontes/ordem não é persistida. Referências de detalhes expiram ou deixam de valer após reinício/troca de fontes.
- A identificação de fontes não é universal. Layouts, bloqueios e hospedeiros podem mudar; o comportamento da origem permanece fora do controle do aplicativo.
- Não há tradução automática, certificação dos arquivos, atualização automática, autenticação nem assinatura digital do executável.
- O código do projeto ainda não recebeu uma licença de redistribuição escolhida pelo proprietário. Publicar o repositório não torna as licenças das dependências uma licença do aplicativo.

Não executei Docker neste computador, nem fiz teste em uma segunda máquina Windows ou auditoria completa de acessibilidade. Novas fontes foram apenas registradas para pesquisa posterior no [roadmap](ROADMAP.md).
