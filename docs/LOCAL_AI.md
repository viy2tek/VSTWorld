# IA local opcional

O aplicativo funciona sem Ollama, modelo ou configuração de IA. A detecção normal continua disponível. `vstworld.local_ai.detect_with_ai` só consulta o Ollama quando chamada explicitamente. Não instala programas, não baixa modelos e não salva fontes automaticamente.

## Configurar no Windows

1. Instale o [Ollama para Windows](https://ollama.com/download/windows).
2. Desative recursos de nuvem nas variáveis de ambiente da sua conta. No PowerShell:

   ```powershell
   [Environment]::SetEnvironmentVariable('OLLAMA_NO_CLOUD', '1', 'User')
   ```

3. Encerre o Ollama pelo ícone na bandeja e abra novamente pelo menu Iniciar. A variável precisa estar presente no processo do servidor, não apenas no aplicativo VSTWorld. Veja a [configuração oficial do Ollama](https://docs.ollama.com/faq#how-do-i-disable-ollamas-cloud-features).
4. Em um novo terminal, baixe o modelo local escolhido por você:

   ```powershell
   ollama pull qwen3.5:4b
   ollama list
   ```

Esse download é uma ação manual opcional e precisa de internet e espaço em disco. O módulo nunca executa esse comando. Não use um nome com `cloud`. Um computador sem recursos suficientes pode exceder o tempo de espera; o aplicativo informa que não conseguiu verificar a fonte.

5. Abra **Fontes → IA local opcional**, informe o nome instalado no campo **Modelo instalado**, cole o site no campo principal e clique em **Identificar com IA local**. A fonte só é preparada se passar pelas verificações; para persistir, revise e clique em **Salvar fonte**. **Identificar site** continua funcionando sem IA.

## Docker opcional, inicialmente por CPU

O Ollama instalado no host não está em `127.0.0.1` dentro do contêiner. Por isso o Compose oferece um perfil opt-in que compartilha o espaço de rede do app e mantém a API de IA no loopback, sem publicar a porta 11434:

```sh
docker compose --profile ai up --build -d
docker compose --profile ai exec ollama ollama pull qwen3.5:4b
```

Sem `--profile ai`, o serviço não inicia e não baixa a imagem nem o modelo. Os modelos ficam no volume `model-data`; `docker compose down -v` apaga também esse volume. O perfil usa a imagem oficial `ollama/ollama:latest`, cujo conteúdo pode mudar; produção pode fixar uma versão/digest após validá-la. Não configura aceleração de GPU. Esta composição foi preparada com base nas documentações de [Docker network_mode service](https://docs.docker.com/reference/compose-file/services/#network_mode) e [Ollama Docker](https://docs.ollama.com/docker), mas não foi executada neste computador.

## O que é verificado

O endereço do servidor é fixo: `http://127.0.0.1:11434`. Não se aceitam servidor remoto, redirecionamentos ou proxies de ambiente. Antes de enviar HTML, o módulo consulta `/api/show`, exige metadados de arquitetura local e bloqueia `remote_host` e `remote_model`. A [especificação oficial da API](https://github.com/ollama/ollama/blob/main/docs/openapi.yaml) descreve esses metadados e o formato JSON Schema de `/api/generate`.

A IA recebe um trecho de HTML com até 16 mil caracteres, sem scripts, estilos, campos de formulário ou formulários de login reconhecidos. O HTML é tratado como conteúdo não confiável. A resposta só pode conter seletores CSS declarativos, com tamanho limitado e schema estrito. A IA não executa código, ferramentas ou JavaScript; não escolhe URL, domínio, método HTTP, parâmetros de busca ou adaptadores.

As páginas passam pelas regras existentes de HTTPS público, DNS seguro, domínios permitidos e robots.txt. O formulário de busca é reconhecido pela inspeção nativa. A IA propõe seletores de listagem; um título observado alimenta uma busca real; uma página de detalhe é selecionada de um resultado real dessa busca. A IA então sugere seletores de descrição e download. Os seletores precisam corresponder ao HTML observado e passam novamente pela detecção nativa.

Uma fonte nova só é devolvida se as verificações de busca e link de download estiverem confirmadas. “Download verificado” significa que um link permitido foi observado no HTML: o arquivo não foi baixado, sua segurança não foi analisada e sua disponibilidade não foi comprovada. Se a fonte já existe, sua configuração personalizada é preservada e a IA não é chamada.

Há apenas uma inspeção com IA por vez, no máximo duas gerações, respostas de até 256 KiB e um limite total de 210 segundos, incluindo a espera na fila. A consulta individual ao Ollama tem limite de 75 segundos e conexão de 3 segundos. Os limites das consultas aos sites continuam os do catálogo.

## Limites e testes

É necessário haver formulário nativo identificável e uma listagem com título e link já presentes na página inicial. Sites com busca apenas por JavaScript, autenticação, captcha, formulário ambíguo ou resultados vazios podem exigir integração manual. Não há tentativa de contornar restrições. Seletores opcionais de paginação e descrição só são aceitos com evidência no HTML consultado; a próxima página não é requisitada.

Os testes em `tests/test_local_ai.py` usam `httpx.MockTransport`: verificam fluxo, respostas inválidas, indisponibilidade e bloqueios sem consultar um servidor ou modelo real. Esses testes não medem a qualidade de inferência, consumo de memória ou desempenho do `qwen3.5:4b` em hardware real.
