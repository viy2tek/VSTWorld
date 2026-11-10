# Revisão da beta 0.3.0-beta.1 — 2026-11-09

## O que mudou

- Executável Windows com ícone na bandeja e ações Abrir/Encerrar, sem console na barra de tarefas. Logs rotativos em arquivo. [Desktop](DESKTOP.md).
- Porta HTTP 80 preferida no desktop, com escolha de outra porta quando ocupada. Nome `vstworld.local` aceito e preferido somente quando resolve para `127.0.0.1`; o app não altera hosts automaticamente nem expõe o servidor na rede.
- Interface em português, inglês e espanhol com preferência no navegador, troca sem recarregar a página e conteúdo original protegido da tradução fixa.
- Tradução explícita das fichas por Ollama local ou API DeepL opcional, com identificação de tradução automática, retorno ao original, proteção de tokens técnicos e validação antes de aplicar. [Tradução](TRANSLATION.md).
- Licença MIT do aplicativo incluída no executável e na imagem Docker, separada das licenças das dependências.

VSTHouse e Plugins4Free continuam como fontes incluídas; Musicmakers permanece candidata desativada. Não foram acrescentadas outras fontes nesta versão.

## Atualização e configuração

Encerre a versão anterior pela bandeja (ou feche o console de versões antigas) e abra o novo executável. Configurações da beta pública continuam em `%LOCALAPPDATA%/VSTWorld/sources.json` e não são sobrescritas. Um atalho com `--sources` continua usando o JSON escolhido. Configurações de builds antigas `-dev` permanecem separadas.

O nome local exige mapeamento no arquivo de hosts do computador. Sem ele, o app funciona pelo IP de loopback. Interface multilíngue não precisa de IA ou conta externa. Para traduzir as fichas, configure um dos tradutores opcionais; não existe envio automático ao DeepL nem instalação automática de modelo.

## Evidência de verificação

- 115 testes Python e seis scripts JavaScript cobrem aplicação, busca, filtros, configuração, tradução, idiomas e ciclo da bandeja.
- Executável Windows foi reconstruído e passou por duas inicializações com dados temporários, rotas e persistência após reinício. O teste inclui os recursos de idiomas e o endpoint de configuração dos tradutores.
- Interface conferida em inglês e espanhol no navegador, preservando texto pesquisado e campos de fonte em edição; ficha real Omnivocal do VSTHouse consultada sem baixar o produto. Controles de tradução e mensagens de serviço não configurado foram exercitados.
- Layout da ficha verificado em largura de 390 px, sem overflow horizontal no exemplo. A validação móvel é por emulação.
- O workflow Checks do GitHub deve passar para o mesmo commit antes da publicação dos arquivos: testes em Windows/Linux e empacotamento/teste do executável no Windows.

## Limites

Não foi medida a qualidade de traduções com um modelo Ollama real ou uma conta DeepL real; os provedores foram simulados nos testes. Chaves reais não foram enviadas nem incluídas no repositório. Docker e dispositivos móveis físicos não foram executados nesta preparação.

O executável não tem assinatura digital ou atualização automática. Mantenha uma instância por configuração. Conteúdo desconhecido da fonte pode continuar no idioma original; tradução não cobre legendas ou texto dentro de imagens. Datas, links e licenças dos produtos dependem das fontes. A publicação mantém o release 0.2.0-beta.1 intacto.
