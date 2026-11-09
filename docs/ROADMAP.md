# Depois da primeira beta

Esta lista registra candidatos e melhorias. Não confirma suporte e não adiciona fontes à configuração da versão 0.1.0-beta.1.

## Fontes experimentais

Inspeção preliminar em 2026-11-08:

| Fonte | Evidência observada | Próxima verificação |
|---|---|---|
| [Musicmakers](https://musicmakers.ru/) | A página inicial apresenta busca, categorias de plugins/samples e links de itens. | Método e parâmetros do formulário, paginação, detalhes, política de acesso e destinos de downloads. Nenhum adaptador validado. |
| [4download](https://4download.net/) | O acesso pelo navegador de pesquisa falhou. | Verificar disponibilidade e estrutura real; não presumir parâmetros ou domínio alternativo. |
| [VSTWarehouse](https://vstwarehouse.com/) | Candidato indicado pelo Similarweb; fonte ainda não inspecionada. | Busca e links oficiais, licença e atribuição. |
| [Plugins4Free](https://plugins4free.com/) | Candidato indicado pelo Similarweb; fonte ainda não inspecionada. | Busca, paginação, ficha técnica e destinos de download. |
| [KVR Audio](https://www.kvraudio.com/) | Candidato indicado pelo Similarweb; fonte ainda não inspecionada. | Verificar acesso permitido e se serve como catálogo de metadados/links oficiais. |

O [Similarweb consultado](https://www.similarweb.com/website/vsthouse.ru/competitors/) mostrava estimativas referentes a setembro de 2026. Também listava vston.ru, vst-store.com, positiverecords.ru, plugincrack.com, guitarist1.ru, splice.com e audioz.download. Similaridade de audiência não comprova compatibilidade, autorização ou qualidade; esses nomes são apenas pistas de pesquisa, sem adaptadores implementados.

Para aprovar cada fonte: registrar requisição real, parâmetros, codificação, resultados, paginação, limites, datas e semântica dos downloads; criar uma fixture reduzida e um teste; medir latência; testar falhas; documentar login/bloqueios e termos. Evitar adicionar dezenas de fontes não verificadas que atrasem a busca e retornem links incorretos.

## Melhorias sugeridas antes de ampliar o catálogo

1. Impedir múltiplas instâncias do executável usando o mesmo JSON e permitir encerrar o app pela interface. Hoje deve-se manter uma janela aberta e fechá-la ao terminar.
2. Exportar/importar fontes pela interface com validação. Hoje o backup é a cópia do JSON documentada no README.
3. Preservar seleção de fontes e ordenação ao voltar dos detalhes. Hoje a URL preserva a consulta ou seção, e a busca é refeita.
4. Deduplicação entre fontes, depois de observar identificadores reais. Nome parecido e mesma versão não bastam para comprovar que são o mesmo arquivo.
5. Favoritos, se houver demanda; exigiriam referências persistentes, pois as referências atuais expiram.

Sem necessidade nesta beta: autenticação de múltiplos usuários, streaming, índice offline, cache complexo ou infraestrutura adicional.
