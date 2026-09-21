# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## O que este diretório é

`SighirAI/Server/` contém só `docs/`, e `docs/` é **workspace de análise + cópias de referência** —
quatro coisas com donos diferentes:

| Caminho | O que é | Mexer aqui? |
|---|---|---|
| `docs/etilometro-server-v2/` | Clone git **real** do repo Django de produção (`jean-vr/etilometro-server-v2`, branch `main`) | Sim — **leia o `CLAUDE.md` dele antes**, tem toda a arquitetura do servidor |
| `docs/ServerAnalysis/` | Notebooks pandas sobre o snapshot do banco | Sim — é o único trabalho que nasce aqui |
| `docs/hardware/Main/` | Snapshot do firmware ESP (`v6.4.6`), sem `.git` | Não — só leitura |
| `docs/files/` | PDFs de protocolo/instalação/manuais, exports CSV/XLSX, screenshots | Não — insumo |

Git: o git root é `/home/klauss/Projects` (repo **sem nenhum commit**) e `SighirAI/Server/` inteiro
aparece como untracked. A única história versionada é a de `etilometro-server-v2`, que tem `.git`
próprio. Não há build, lint nem suite de testes neste nível — não invente comandos.

## Comandos

```bash
# atualizar o snapshot do banco (a chave está em etilometro-server-v2/doc/pwdsighir.pem)
scp -i pwdsighir.pem ubuntu@52.91.100.216:/home/ubuntu/v2/api/db.sqlite3 ServerAnalysis/files/db.sqlite3

pdftotext -f 1 -l 5 files/PROTOCOL.pdf -      # pdftotext instalado; CLI sqlite3 NÃO
```

Notebooks: rode sempre **a partir de `ServerAnalysis/`**, todos os caminhos são relativos ao cwd.
`pandas`, `numpy`, `matplotlib`, `scipy`, `openpyxl` e `requests` existem no python3 do sistema
(3.12); **`reportlab` não** — `3 - Report.ipynb` precisa dele instalado antes de rodar.

Testes e servidor local: dentro de `docs/etilometro-server-v2/` (Django, `libs.txt`, `manage.py test`).
O `CLAUDE.md` de lá é a fonte para isso.

## ServerAnalysis — o pipeline

Notebooks numerados que trocam arquivos, não estado:

```
files/db.sqlite3 ──1 - Format──▶ files/DataBase.csv ──2 - Analysis──▶ output/general.csv + relations.csv
                                                    └─3 - Report───▶ output/report.pdf
files/db.sqlite3 ──Logs───────▶ output/remove.csv          (logs candidatos a expurgo)
DataBase.csv + files/Detailed Event Report.csv ──MIX──▶ placas na MiX ausentes no Sighir
```

- `1 - Format` e `Logs` **compartilham as ~20 primeiras células** (mesma extração e normalização de
  `device`/`etilometro`). Mexeu numa, replique na outra ou elas divergem em silêncio.
- **Armadilha de caminho:** `1 - Format` grava em `files/DataBase.csv`, mas `3 - Report` e `MIX` leem
  `'DataBase.csv'` na raiz de `ServerAnalysis/`. Copie o arquivo ou ajuste a célula antes de rodar.
- `3 - Report.ipynb`: a empresa é a constante `EMPRESA` na célula 0 (`None` = relatório geral); a classe
  `ReportGenerator` vive **inline** na célula 1 — o `report_generator.py` sumiu, sobrou só o `.pyc`.
- `.gitignore` local ignora `*.csv` e `files/` — nem o snapshot nem os exports são versionados.

## O snapshot do banco

`ServerAnalysis/files/db.sqlite3` (~148 MB, atualizado em **2026-08-24**): 230.241 logs, 253 devices,
141 etilômetros. É cópia local — escrever aqui **não** afeta produção, e ler daqui envelhece rápido;
para dado corrente use a API (`https://sighir.com:8000/api/v2/`, JWT em `POST /api/v2/token/`).

Sem CLI `sqlite3`, use Python:

```bash
python3 -c "
import sqlite3
c = sqlite3.connect('ServerAnalysis/files/db.sqlite3')
print(c.execute('select id, vehicle_plate, device_id from Etilometros_etilometro limit 5').fetchall())
"
```

O mínimo de domínio para consultar sem errar de tabela (o resto está no `CLAUDE.md` do server):

```
Company (PK = CNPJ) └─ Device (PK = "MIC…", o hardware) └─ Etilometro (PK = UUID, a INSTALAÇÃO) └─ Log
```

`Device` é hardware, `Etilometro` é a instalação device↔placa — coisas diferentes, rotas diferentes
(`devices/` vs `etilometers/`, grafia com um "e"). `vehicle_plate` não tem unique, deduplique na mão.
`vehicle_type`: 0 = Caminhão, 1 = Carro. `Log.event` guarda a string do protocolo serial
(`$ETEV01!`), cujos significados estão em `files/Sighir_Protocol.pdf` e a gramática dos comandos em
`files/PROTOCOL.pdf`.

## files/ — os exports não compartilham dialeto

| Arquivo | Origem | Sep | Detalhe |
|---|---|---|---|
| `DataBase.csv` | saída do `1 - Format` | `,` | um device por linha, decimal `.` (cópia idêntica à de `ServerAnalysis/files/`) |
| `Detailed Event Report.csv` | MiX | `,` | 249k linhas, BOM, decimal com **vírgula** entre aspas, data `dd/mm/yyyy` |
| `Monitoramento_Inicio_a_Fim*.csv` | painel Sighir | `;` | BOM, data `dd/mm/yyyy, HH:MM:SS`, eventos em português |
| `Relatorio_Sensores*.xlsx` | painel Sighir | — | abas Resumo / Sensores / Firmware |
| `Relatorio_Operacional_*.xlsx` | painel Sighir | — | abas Resumo / Eventos de Alerta |

## Relação com `../Tester/`

`../Tester/docs/server/` e `../Tester/docs/hardware/` são as **mesmas** cópias de referência, porém
**mais antigas** (firmware v6.4.0 contra v6.4.6 aqui; sem `Anomaly`, `permissions.py`, `CONFORMIDADE.md`).
Para código, prefira o que está aqui. O que continua valendo de lá é a prosa já consolidada:
`../Tester/docs/server_reference.md`, `firmware_reference.md` e `server/README.md` (infra AWS, SSH,
port forwarding) — sabendo que descrevem o servidor num estado anterior.

## Escaneamento de anomalias (Sighir Scanner AI)

Quando o usuário pedir varredura em linguagem natural — *"inicie o escaneamento"*, *"roda a
varredura"*, *"escaneia os logs"* — rode o scanner. **Vale em qualquer sessão sob
`SighirAI/Server/`**, não precisa de comando nem de flag.

```bash
cd scanner
python3 scan.py                  # modo seco: mostra o que sairia, NÃO escreve
python3 scan.py --write          # escreve de verdade na tabela anomalies
python3 scan.py --show RJX6I60   # mostra o desc que sairia para uma placa
python3 test_scan.py             # 10 checagens das regras e da reconciliação
```

**Modo seco é o padrão.** `--write` é a única forma de tocar a tabela.

Regras, limiares, formato do `desc` e limitações conhecidas estão no `README.md` da raiz —
leia antes de mudar qualquer limiar. Os limiares são constantes no topo da classe `Scanner`
(`SILENCE`, `SENSOR_DAYS`, `SENSOR_BAD`, `FLOOD`, `POSTPONE`, `NOBLOW`, `MIN_TRIES`); mudar um
deles é mudar a regra, então diga ao usuário o impacto em número de alertas antes de mudar.

`scanner/state.json` e `scanner/logs.json` são estado de execução (janela incremental e cache
dos logs da janela). Apagar os dois força uma varredura completa de 3 meses na próxima
execução — é a forma de resetar, e é seguro.

**Só a tabela `anomalies` pode ser escrita.** `api.py::send()` bloqueia com `PermissionError`
qualquer escrita em outra rota; não contorne esse guard.
