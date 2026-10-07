# Testes das IAs (Tester, Server, Helper)

Como provar que as três IAs funcionam — depois de mudar código, depois de uma migração do servidor
(`migracao_servidor.md`) ou antes de entregar uma versão. Rode da raiz do repositório.

## 1. Automático (`docs/tools/testar.py`)

| Nível | Comando | O que cobre | Grava? |
|---|---|---|---|
| rápido | `python docs/tools/testar.py` | suítes offline: Notion (`test_notion_sync`), contrato (`test_contrato`), Scanner (`test_scan`), Helper (`test_helper`), Tester (`test_cli`: register/install com API falsa) + `boot.py status` das 3 IAs | não |
| api | `python docs/tools/testar.py --api` | + produção **só leitura**: logs chegando por telemetria (MiX/Suntech/Entrack; zero em telemetria com ≥ 3 veículos ativos na semana = serviço de integração parado), serviços satélites do servidor por SSH (`api`, `mix`, `telemetry-panel`), contrato (`verificar` e `diferenca`), Helper `veiculo`/`device`/`patch` sem `--sim`, Tester `server-device` e prévias do `install`, resumo da frota. Usa como referência uma instalação Suntech real com módulo | não |
| completo | `python docs/tools/testar.py --completo` | + check **seco** do Scanner (`scan.py` sem `--write`; 3–4 min na 1ª do dia) | não |
| bancada | `python docs/tools/testar.py --bancada` | + aparelho na USB: `init`, `firmware`, `settings`, `telemetry` (só mostra), lista de testes | não |

Gravação real verificada em 07/10/2026 (aparelho de estoque da Sighir na placa `BANCADA`): `install`,
`edit --desinstalar`, `edit --modulo` (cria módulo em `/telemetries` com chip) e `--modulo none` —
tudo conferido e devolvido ao estado original.

Saída: uma linha por etapa (`ok`/`FALHA` + fim da saída da etapa que falhou) e `n/n etapas passaram`.
Código 1 = algo falhou. Referência em 07/10/2026: 17/17 com `--api`.

Cada suíte também roda sozinha (na pasta da IA): `python tools/test_cli.py` (Tester),
`python scanner/test_scan.py` (Server, de dentro de `scanner/`), `python tools/test_helper.py` (Helper),
`python docs/tools/test_contrato.py`, `python docs/tools/test_notion_sync.py`.

## 2. O que os automáticos não cobrem

- Gravação de verdade no servidor (`register`, `install --yes`, `Helper patch --sim`, `scan.py --write`).
- Gravação no aparelho (telemetria, configurações, bloqueio, testes de sopro/álcool, flash).
- Por isso existe o roteiro abaixo: **só com o ok do usuário**, um passo de cada vez, conferindo o esperado.

## 3. Roteiro de bancada e gravação (manual, com o usuário)

Use um aparelho **da Sighir** na bancada (não de cliente). Anote o `esp_id` e o estado inicial (`status`,
`settings`, `telemetry`, `server-device`) para devolver tudo como estava no fim. Comandos na pasta `Tester/`.

| # | Passo | Comando | Esperado |
|---|---|---|---|
| 1 | Sessão | `python tools/sighir.py init` | firmware classificado (`ok` ≥ 6.4.0), `esp_id` `MIC…`, `sensor_id` `ETL…` |
| 2 | Configuração ida e volta | `settings --set <chave>=<novo>` → `settings <chave>` → `settings --set <chave>=<original>` | valor lido = valor gravado; volta ao original |
| 3 | Telemetria ida e volta | `telemetry suntech` → `telemetry` → `telemetry <original>` | grava, reinicia e confere o modo; volta ao original |
| 4 | Bloqueio | `block` → `unblock` | confirma por `$ETEV02!` e `$ETEV01!` |
| 5 | Testes do protocolo | `test sensor`, `test temp`, `test blow` (e `test alcohol` com solução) | cada um conclui com o evento esperado do `protocol.json` |
| 6 | Recuperação | `recover` | reinicia e ressincroniza |
| 7 | Servidor: consulta | `server-device <MIC>` e `python ../Helper/tools/helper.py device <MIC>` | mesmo cadastro nos dois (empresa, módulo, placa) |
| 8 | Servidor: cadastro | só se o aparelho **não** estiver cadastrado: `register --company <value> --modulo <ID ou none> --chip <N ou N/A>` | `POST /telemetries` (se módulo novo) e `POST /devices` ok; `server-device` mostra `telemetry` = módulo |
| 9 | Servidor: instalação | `install <MIC> --placa <placa de teste> --telemetria <t> [--modulo …] --observacao "teste de bancada"` (prévia) → mesmo comando com `--yes` | prévia sem bloqueio; com `--yes`: "gravada e conferida" (placa, telemetria, módulo e `etilometers/`) |
| 9b | Servidor: edição | `edit <MIC> --company <outra> --desinstalar --modulo <ID>` (prévia) → com `--yes` | prévia só com os campos pedidos; com `--yes`: "alterado e conferido" |
| 10 | Conferência cruzada | `python ../Helper/tools/helper.py veiculo <placa>` | a instalação aparece com telemetria e módulo |
| 11 | Firmware (quando for o caso) | `flash` em background com `flash.log` + `progresso` a cada 20 s | uma porcentagem nova a cada ~20 s mostrada ao usuário; no fim `flash concluído` e a versão nova (`firmware`) |
| 11b | Duplicidade | `register` de um aparelho já cadastrado (ou `onde <MIC>`) | código 4, onde está (empresa, placa, série, módulo) e as opções numeradas; nada gravado |
| 12 | Devolver | desfazer o passo 9 (instalação de teste: combine com o usuário — `Helper patch devices <MIC> is_operating=false` ou reinstalar na placa original com `--forcar`) e conferir o estado anotado | igual ao início |

Placa de teste: combine com o usuário (o servidor cria o `Vehicle` e ele fica no banco). O passo 9 é o que
confirma, na primeira vez, a gravação do `install` no modelo de 24/09/2026 (ver `migracao_servidor.md`).

## 4. Server e Helper com gravação (manual)

- **Scanner**: `cd Server/scanner && python scan.py` (seco) → conferir a lista `mudanças` placa por placa →
  só então "iniciar check" (`--write`). Vários `[SILÊNCIO]` com a mesma data de início = suspeite do servidor
  (`Server/README.md`), não grave antes de entender.
- **Helper**: `patch devices <MIC> nickname=<x>` sem `--sim` (mostra antes → depois), com `--sim` grava e
  confere; desfaça com o valor original.
