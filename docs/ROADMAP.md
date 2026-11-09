# Depois da primeira beta

Esta lista registra candidatos e melhorias. A versão 0.1.0-beta.1 publicada continua somente com VSTHouse. O desenvolvimento 0.2.0-dev já inclui Plugins4Free e uma candidata Musicmakers desativada; as demais não são anunciadas como suportadas.

## Fontes experimentais

Inspeção atualizada em 2026-11-09:

| Fonte | Evidência observada | Próxima verificação |
|---|---|---|
| [Musicmakers](https://musicmakers.ru/) | Formulário POST identificado, detalhes públicos inspecionados; configuração experimental desativada. | Restrições de robots em pesquisa/download/redirecionamento; não promover a fonte completa. [Inspeção](MUSICMAKERS_INSPECTION.md). |
| [4download](https://4download.net/) | Busca POST, segunda página por formulário GET e detalhes inspecionados via HTTP normal. | Downloads usam página intermediária com fragmentos/JS e espelhos externos; sem arquivo direto confirmado. [Inspeção](MUSICMAKERS_INSPECTION.md). |
| [VSTWarehouse](https://vstwarehouse.com/) | Busca, paginação e ficha públicas funcionaram. | Botão de download depende de modal/EDD; nenhum arquivo direto validado. [Inspeção](FREE_SOURCES_INSPECTION.md). |
| [Plugins4Free](https://plugins4free.com/) | Integrada: busca HTML, seções, detalhes e três arquivos resolvidos por JSON + HEAD, sem baixar corpos. | Monitorar mudanças no fluxo CSRF e no layout. [Inspeção](FREE_SOURCES_INSPECTION.md). |
| [KVR Audio](https://www.kvraudio.com/) | Candidato indicado pelo Similarweb; fonte ainda não inspecionada. | Verificar acesso permitido e se serve como catálogo de metadados/links oficiais. |
| VSTon / vstion.site | Redirecionamento e detalhe público inspecionados; robots restringe busca/downloads. | Acesso permitido e política da origem antes de qualquer integração. |
| PositiveRecords | Falha de validação TLS nos domínios consultados. | Aguardar certificado/cadeia verificável; não desativar validação TLS. |

O [Similarweb consultado](https://www.similarweb.com/website/vsthouse.ru/competitors/) mostrava estimativas referentes a setembro de 2026. Também listava vston.ru, vst-store.com, positiverecords.ru, plugincrack.com, guitarist1.ru, splice.com e audioz.download. Similaridade de audiência não comprova compatibilidade, autorização ou qualidade; esses nomes são apenas pistas de pesquisa, sem adaptadores implementados.

Para aprovar cada fonte: registrar requisição real, parâmetros, codificação, resultados, paginação, limites, datas e semântica dos downloads; criar uma fixture reduzida e um teste; medir latência; testar falhas; documentar login/bloqueios e termos. Evitar adicionar dezenas de fontes não verificadas que atrasem a busca e retornem links incorretos.

## Melhorias sugeridas antes de ampliar o catálogo

1. Impedir múltiplas instâncias do executável usando o mesmo JSON e permitir encerrar o app pela interface. Hoje deve-se manter uma janela aberta e fechá-la ao terminar.
2. Exportar/importar fontes pela interface com validação. Hoje o backup é a cópia do JSON documentada no README.
3. Preservar seleção de fontes e ordenação ao voltar dos detalhes. Hoje a URL preserva a consulta ou seção, e a busca é refeita.
4. Deduplicação entre fontes, depois de observar identificadores reais. Nome parecido e mesma versão não bastam para comprovar que são o mesmo arquivo.
5. Favoritos, se houver demanda; exigiriam referências persistentes, pois as referências atuais expiram.

Sem necessidade nesta beta: autenticação de múltiplos usuários, streaming, índice offline, cache complexo ou infraestrutura adicional.
