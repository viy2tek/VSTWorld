# Idiomas e tradução de conteúdo

Disponíveis a partir da beta 0.3.0-beta.1.

## Idioma da interface

O seletor no cabeçalho oferece **Português**, **English** e **Español**. A preferência é salva neste navegador, neste endereço. Sem preferência salva, o app usa um desses idiomas conforme o navegador e recorre ao português quando não reconhece o idioma.

As traduções fixas ficam em `static/locales.json`, servidas pelo próprio app. Não usam IA nem tradutor online. Trocar o idioma não recarrega a página, não altera o texto pesquisado e não apaga campos de fontes em edição. Nomes de produtos, nomes das fontes, conteúdo extraído e código/configuração não são traduzidos por esse mecanismo. Mensagens desconhecidas retornadas pela fonte ou servidor podem permanecer no idioma original.

## Traduzir uma ficha

1. Abra um item e expanda **Traduzir informações**.
2. Escolha português, inglês ou espanhol e o tradutor: **LibreTranslate local** ou **Ollama local**.
3. Clique em **Traduzir**. Não há tradução automática ao pesquisar ou abrir o item.
4. Use **Ver original** para comparar. Reaplicar a mesma tradução nesta página usa a resposta já recebida; recarregar a página perde esse resultado em memória.

São traduzidos rótulos e valores técnicos elegíveis, títulos de seções de instalação, etapas, listas e rótulos dos links das instruções. O título do produto, versão, desenvolvedora, distribuidora, URLs, imagens, arquivos e vídeos permanecem na estrutura original. URLs e nomes de arquivos presentes nos próprios parágrafos, números e alguns identificadores técnicos recebem tokens protegidos antes do envio.

A resposta deve manter a quantidade de trechos e todos os tokens protegidos. Se perder, duplicar ou alterar um token, introduzir dígitos não protegidos, vier incompleta ou falhar, o conjunto é descartado; a interface mantém o original. Isso não comprova a qualidade linguística nem impede toda alteração de sentido. Traduções são identificadas como automáticas e precisam ser conferidas, especialmente nas instruções de instalação.

## Configurar LibreTranslate local

O LibreTranslate é um serviço separado, gratuito para hospedar, sem chave de API nesta configuração. Usa recursos da sua máquina e baixa modelos na primeira inicialização. Não faz parte do executável do VSTWorld.

Para o executável Windows ou execução Python, instale o Docker e execute:

```powershell
docker run -d --name vstworld-translator -p 127.0.0.1:5000:5000 -e LT_HOST=0.0.0.0 -e LT_LOAD_ONLY=ru,en,pt,es -v vstworld-translation:/home/libretranslate/.local libretranslate/libretranslate:latest
```

Espere o carregamento dos modelos; acompanhe com `docker logs -f vstworld-translator`. Depois, escolha **LibreTranslate local** na ficha. Para iniciar novamente após parar o container, use `docker start vstworld-translator`.

Se o VSTWorld também roda via Compose, use o perfil opcional que compartilha a rede do aplicativo:

```sh
docker compose --profile translate up -d --build
docker compose logs -f libretranslate
```

O app consulta somente `http://127.0.0.1:5000/translate`, no computador ou na rede compartilhada dos containers. A origem do texto é detectada pelo tradutor. É preciso ter modelos para os idiomas envolvidos; disponibilizar um idioma não comprova a qualidade da tradução. Se o serviço ou um par de idiomas falhar, o original é preservado. Os tokens técnicos são separados localmente e reinseridos, sem passar pelo modelo de tradução; isso pode reduzir o contexto linguístico de uma frase.

Referências: [instalação e argumentos](https://docs.libretranslate.com/guides/installation/), [API de tradução](https://docs.libretranslate.com/api/operations/translate/), [idiomas e modelos](https://docs.libretranslate.com/guides/supported_languages/) e [volume dos modelos no Compose oficial](https://github.com/LibreTranslate/LibreTranslate/blob/main/docker-compose.yml). A imagem `latest` pode mudar; fixe uma versão validada no seu ambiente para instalações reproduzíveis. O serviço tem licença própria, separada da MIT do VSTWorld.

## Configurar Ollama local

Siga o [guia de IA local](LOCAL_AI.md). Em **Configurar tradutores opcionais**, informe o nome do modelo instalado; o padrão é `qwen3.5:4b`. O aplicativo não instala modelo nem inicia o Ollama automaticamente.

O texto vai apenas para `http://127.0.0.1:11434`. Modelos com identificadores de nuvem ou metadados de backend remoto são recusados neste modo. Nenhuma chave de API de tradução é necessária. Não há fallback para serviços online. Respostas usam esquema JSON e validação, seguindo a [documentação de saídas estruturadas do Ollama](https://docs.ollama.com/capabilities/structured-outputs). A inferência pode ser lenta ou exigir memória adicional, dependendo do modelo e da máquina.

## Limites e verificação

- Até 160 trechos e 16.000 caracteres elegíveis por ficha; textos maiores geram mensagem, sem truncamento silencioso.
- Até 210 segundos por operação, com limites de resposta e requisições em lotes. Apenas uma geração local por vez, compartilhada com a identificação por IA.
- Testes simulam LibreTranslate e Ollama para validar fluxo, idiomas, contagem de trechos, tokens, dados preservados, modelos remotos, redirecionamentos e falhas. Não há integração com tradutor online nesta versão.
- Docker/LibreTranslate e modelos Ollama reais não foram executados nesta preparação; qualidade, desempenho e compatibilidade dos modelos ainda precisam de teste no ambiente do usuário. Não há suporte a legendas de vídeos ou texto dentro de screenshots.
