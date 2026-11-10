# Desktop Windows

Bandeja e nome local disponíveis a partir da beta 0.3.0-beta.1.

## Nome local e porta

O servidor continua vinculado a `127.0.0.1`. O aplicativo aceita `localhost`, o IP e `vstworld.local`, além dos hosts configurados explicitamente. A verificação de Host e a proteção de requisições de outra origem continuam ativas.

Para usar o nome neste computador, o arquivo `C:\Windows\System32\drivers\etc\hosts` deve conter:

```text
127.0.0.1 vstworld.local
```

Isso não registra um domínio público nem configura outros dispositivos. O executável não altera esse arquivo automaticamente. O launcher só prefere o nome quando a resolução IPv4 retorna exatamente `127.0.0.1`; em caso de falha ou outro destino, usa o IP local.

O executável tenta a porta HTTP 80, omitida em `http://vstworld.local`. Se estiver ocupada, escolhe uma porta livre e inclui o número na URL. `--port` continua permitindo uma escolha explícita. A execução pelo código e o Docker mantêm a porta padrão 8787.

## Bandeja e encerramento

O build Windows usa o subsistema GUI, sem janela de console. O ícone W na bandeja oferece **Abrir VSTWorld** e **Encerrar**. O Windows pode colocá-lo no grupo de ícones ocultos junto ao relógio. Fechar o navegador não encerra o app.

Os logs de desenvolvimento vão para `vstworld.log`, junto do JSON selecionado, com rotação de dois arquivos de até 1 MB. Falhas de inicialização são registradas e exibem uma mensagem nativa, em vez de deixar o processo sem interface. Mantenha uma instância por configuração; ainda não existe bloqueio de instâncias duplicadas.

A bandeja usa [pystray](https://pystray.readthedocs.io/en/latest/usage.html) e Pillow, dependências apenas do empacotamento desktop. O loop da bandeja fica na thread principal e o servidor numa thread separada. Encerrar solicita a parada do servidor e remove o ícone. A execução pelo código e o Docker não importam essas bibliotecas.

## Evidência de verificação

- 106 testes Python passaram, incluindo destino do nome local, Host permitido, rejeição de outro Host e ciclo de abertura/encerramento da bandeja com implementação simulada.
- Executável real iniciou duas vezes com dados temporários, serviu a interface e preservou configuração; cabeçalho PE confirmado como GUI.
- Instância real consultada em `http://vstworld.local/api/health` na porta 80, vinculada somente ao loopback; mesma origem aceita nas requisições POST.
- A configuração existente manteve VSTHouse e Plugins4Free. A aba do navegador abriu o novo nome com sucesso.

O menu foi exercitado pelos testes; o posicionamento visual dos ícones depende do Windows. O release 0.3.0-beta.1 inclui essas mudanças; o arquivo do release anterior é preservado.
