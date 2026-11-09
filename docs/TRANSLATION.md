# Idiomas e tradução de conteúdo

Disponíveis no código em desenvolvimento e no novo build local; o release público 0.2.0-beta.1 ainda não foi atualizado.

## Idioma da interface

O seletor no cabeçalho oferece **Português**, **English** e **Español**. A preferência é salva neste navegador, neste endereço. Sem preferência salva, o app usa um desses idiomas conforme o navegador e recorre ao português quando não reconhece o idioma.

As traduções fixas ficam em `static/locales.json`, servidas pelo próprio app. Não usam IA nem tradutor online. Trocar o idioma não recarrega a página, não altera o texto pesquisado e não apaga campos de fontes em edição. Nomes de produtos, nomes das fontes, conteúdo extraído e código/configuração não são traduzidos por esse mecanismo. Mensagens desconhecidas retornadas pela fonte ou servidor podem permanecer no idioma original.

## Traduzir uma ficha

1. Abra um item e expanda **Traduzir informações**.
2. Escolha português, inglês ou espanhol e um tradutor.
3. Clique em **Traduzir**. Não há tradução automática ao pesquisar ou abrir o item.
4. Use **Ver original** para comparar. Reaplicar a mesma tradução nesta página usa a resposta já recebida; recarregar a página perde esse resultado em memória.

São traduzidos rótulos e valores técnicos elegíveis, títulos de seções de instalação, etapas, listas e rótulos dos links das instruções. O título do produto, versão, desenvolvedora, distribuidora, URLs, imagens, arquivos e vídeos permanecem na estrutura original. URLs e nomes de arquivos presentes nos próprios parágrafos, números e alguns identificadores técnicos recebem tokens protegidos antes do envio.

A resposta deve manter a quantidade de trechos e todos os tokens protegidos. Se perder, duplicar ou alterar um token, introduzir dígitos não protegidos, vier incompleta ou falhar, o conjunto é descartado; a interface mantém o original. Isso não comprova a qualidade linguística nem impede toda alteração de sentido. Traduções são identificadas como automáticas e precisam ser conferidas, especialmente nas instruções de instalação.

## Local — Ollama

Siga o [guia de IA local](LOCAL_AI.md). Em **Configurar tradutores opcionais**, informe o nome do modelo instalado; o padrão é `qwen3.5:4b`. O aplicativo não instala modelo nem inicia o Ollama automaticamente.

O texto vai apenas para `http://127.0.0.1:11434`. Modelos com identificadores de nuvem ou metadados de backend remoto são recusados neste modo. Respostas usam esquema JSON e validação, seguindo a [documentação de saídas estruturadas do Ollama](https://docs.ollama.com/capabilities/structured-outputs). A inferência pode ser lenta ou exigir memória adicional, dependendo do modelo e da máquina.

## Online — DeepL

É opcional e requer uma **chave da API DeepL**. Uma assinatura comum do tradutor web não substitui a chave da API. Endpoints Free/Pro e autenticação seguem a [documentação oficial](https://developers.deepl.com/docs/getting-started/auth).

No Windows, crie a variável de ambiente da sua conta `VSTWORLD_DEEPL_API_KEY` com a chave e reabra o aplicativo a partir de um processo que receba essa variável. Pelo código, também é possível defini-la apenas no ambiente do terminal antes de iniciar o servidor. Não coloque a chave em `sources.json`, no código da interface ou em arquivos públicos.

No Docker Compose, a variável é repassada ao contêiner. Configure-a no ambiente do Compose ou num arquivo `.env` local, ignorado pelo Git, e recrie o contêiner:

```sh
docker compose up -d --build --force-recreate
```

O servidor escolhe `api-free.deepl.com` para chaves terminadas em `:fx` e `api.deepl.com` para as demais. Não aceita um endpoint arbitrário fornecido pelo navegador. A chave permanece no servidor, nunca é devolvida à interface e não é usada como parte da URL. O pedido segue a [API oficial de tradução de texto](https://developers.deepl.com/api-reference/translate/request-translation).

Escolher **Online — DeepL** mostra um aviso antes do botão: ao clicar em Traduzir, os trechos textuais elegíveis são enviados ao DeepL. O campo de título do item e os arquivos/imagens não são enviados para tradução. Podem existir limites e cobranças na conta do provedor; falhar após um pedido não garante ausência de consumo. Sem chave, a opção explica o que falta e não faz um pedido online. Não há troca automática do modo local para online.

## Limites e verificação

- Até 160 trechos e 16.000 caracteres elegíveis por ficha; textos maiores geram mensagem, sem truncamento silencioso.
- Até 210 segundos por operação, com limites de resposta e requisições em lotes. Apenas uma geração local por vez, compartilhada com a identificação por IA.
- Testes simulam Ollama e DeepL para validar fluxo, idiomas, contagem de trechos, tokens, dados preservados, quotas, chave ausente, modelos remotos, redirecionamentos e falhas. Nenhuma chave real ou texto de usuário foi enviado ao DeepL nesta verificação.
- Não foi executado um modelo Ollama real para medir a qualidade das traduções. Não há suporte a legendas de vídeos ou texto dentro de screenshots.
