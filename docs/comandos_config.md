# Comandos, configurações e rotas do etilômetro

> Fontes: firmware v6.4.8 (`objects/telemetry/protocol/index.h`, `device/settings/index.h`,
> `device/company/index.h`, `objects/server/*`), PPTC 0001-01 §2, `Notion/PROTOCOL.pdf` (protocolo antigo, 2025),
> `Tester/AGENTS.md` (comportamento medido na bancada). Para operar pela USB use o **Sighir Tester AI**
> (`Tester/tools/sighir.py`) — ele já trata ruído, retentativas e as armadilhas abaixo.

## 1. Enquadramento

- Serial **115200 bps**, linhas terminadas em `\r\n`. Eventos e respostas: `$<conteúdo>!`.
- A mesma lógica atende a **porta do rastreador** (UART2) e a **USB** (quem falou por último "ganha" a porta).
- Pela rota HTTP `/CONFIG` (POST) o corpo é injetado como se fosse um comando serial.

## 2. O parser: casamento por *pedaço*, em cadeia, nesta ordem

`Protocol::check()` usa `contains()` e para no primeiro que casar:

`D:` → `F:` → `updt` → `ETRS` → `firmware` → `ETBL02` → `ETBL01` → `erase_sensor` → `erase` → `ETACK` →
`ETKA` → `TST_TEMP` → `TST_SENS` → `TST_PRESS` → `endTravel` → `last_analog` → `analog` → `sensor_id` →
`cf_coefs` → `coefs` → `calibrate`

Consequências:
- `ID:chave$` funciona porque contém `D:`; `CF:chave$valor!` porque contém `F:` (forma antiga do PROTOCOL.pdf).
- **Nunca mande texto livre na serial**: qualquer string contendo `updt`, `erase`, `ETRS`, `firmware`…
  dispara a ação (update, **reset de fábrica**, reboot).
- Durante um teste o parser não roda (o aparelho só emite eventos) — espere o resultado.
- A resposta pode vir colada num evento assíncrono (ex.: `$ETEV17!` da resposta ao `$ETKA!`): pegue o
  último token `$…!` que não seja `$ETEVnn!`.

## 3. Comandos

**Do rastreador (operação — PPTC §2.1, modo MIX 2.0):**

| Comando | Efeito | Resposta |
|---|---|---|
| `$ETAT01!` | chave no 1º estágio (ignição) — pede teste se bloqueado e fora de viagem | `$ETATACK!` |
| `$ETEV31!` | igual ao `$ETAT01!`, só com `vehicle_type=1` (carro) | `$ETATACK!` |
| `$ETEV03!` | veículo em movimento (caminhão: inicia viagem e habilita randômico) | `$ETEVACK!` |
| `$ETEV04!` | ignição desligada: encerra viagem, inicia tempo de manobra | `$ETEVACK!` |
| `$ETACK!` / `$ETKA!` | keep-alive | `$ETKAACK!` (o `$ETKA!` também devolve `$ETEV17!`) |
| `$ETBL01!` | **desbloqueio remoto** sem teste (apaga o display) | `$ETBL010000!` + `$ETEV01!` (o `$ETKAACK!` do PPTC não chega na prática: confirme pelo `$ETEV01!`) |
| `$ETBL02!` | **bloqueio remoto** | `$ETBL020000!` + `$ETEV02!` |
| `endTravel` | encerra a viagem à força (bloqueado, randômico parado) | `OFF` |
| `$ETRS!` | reinicia | — |

**Consulta/manutenção (qualquer modo):**

| Comando | Efeito | Resposta |
|---|---|---|
| `D:chave$` (ou `ID:chave$`) | lê uma configuração do NVS | `$valor!` ou `ERROR` |
| `F:chave$valor!` (ou `CF:…`) | grava configuração e salva (a maioria só vale após reiniciar) | `OK` |
| `firmware` (ou `$firmware!`) | versão | `v6.4.8` (texto cru) — sem resposta válida = firmware muito antigo |
| `sensor_id` | relê o ID na EEPROM do sensor | `ETL…` |
| `analog` / `last_analog` | leitura bruta atual / do último teste | inteiro |
| `coefs` / `cf_coefs$…!` | lê / grava coeficientes (metrologia) | JSON / `success`/`error` |
| `erase_sensor` | **apaga a EEPROM do sensor** (irreversível) | `success`/`error` |
| `erase` (`$erase!`) | **reset de fábrica** das configurações + reinício (novo `esp_id`!) | — |
| `TST_PRESS` / `TST_TEMP` / `TST_SENS` | diagnóstico (até ~10 s) | `pressworking` / `tempworking` / `$ETEV20!` (ou `$ERROR!`/`ERROR`/`$ETEV24!`) |
| `calibrate` | teste em modo coleta (não bloqueia, sem eventos) | dados |
| `updt` (`__updt__`) | OTA pela serial (chunks base64 `$…!`) | `_STARTING_UPDATE_` … `written` |

Flags de bancada (via `F:`): `press$1` simula sopro, `testalc$1` força álcool, `presstream$1` transmite a
pressão a 10 Hz. **Desligue antes de devolver o aparelho.**

## 4. Configurações (NVS "preferences")

Padrões de `Settings::reset()` (reset de fábrica) e, entre parênteses, os de **primeira configuração**
`Company::configParams()` (aplicados quando `company ≠ sighir`, prevalecem na fábrica):

| Chave | Padrão | Significado |
|---|---|---|
| `esp_id` | `MIC…` gerado | identidade (Wi-Fi `SIGHIR - MICxxxx`) |
| `sensor_id` | `None` → ID da EEPROM | sensor instalado |
| `telemetry` | **2** Suntech (**0** MIX) | 0 MIX · 2 Suntech · 5 MIX 2.0 · 6 Entrack (lido no boot) |
| `vehicle_type` | 0 caminhão | 0 caminhão · 1 carro |
| `max_postpone` | 3 (3) | adiamentos por teste (0 vira 1 se randômico ativo) |
| `postpone_time` | 5 (5) min | tempo liberado ao adiar |
| `maneuver_time` | 5 (**1**) min | tempo de manobra |
| `enable_random` | true (1) | testes randômicos |
| `number_of_tests` | 1 (1) | randômicos por viagem |
| `time_of_travel` | 10 (5) min | duração média da viagem (sorteio do randômico) |
| `rand_ppn_time` | 5 (2) min | adiamento do randômico |
| `rand_min_time` | 2 (5) min | mínimo antes do 1º randômico |
| `camera` | 5 s | espera da câmera |
| `bypass` | false | contrassenha aceita "5" (só bancada) |
| `blowProb` | 0.1 | tolerância do detector de sopro (s) |
| `valet` | (ausente) | habilita o botão de modo manobrista |
| `wifi` | false | liga AP+Wi-Fi (necessário para OTA/check-update) |
| `ssid` / `passwd` | `Etilometro` / `12345678` | rede Wi-Fi da base (cliente) |
| `server` | `https://sighir.com:8000/` | servidor |
| `company` | `sighir` | ≠ sighir → aplica `configParams` e reinicia |
| `brightness` / `volume` | 127 / 255 | tela / buzzer |
| `lang` | `PT` | PT/EN/ES |
| `reset` | 0 | contador de boots incompletos (≥ 5 → "Alimentação Indevida") |
| `last_alcohol`, `last_analog`, `temp_debug`, `presstream` | — | diagnóstico |

⚠ `erase` (reset de fábrica) volta **tudo** ao padrão: **telemetria vira 2 (Suntech)**, Wi-Fi desliga,
novo `esp_id` — um aparelho MiX/Entrack precisa ser reconfigurado depois. O servidor guarda uma cópia
parcial em `Device.default_settings` (quase sempre vazia): **não há como ler a configuração real de um
aparelho remotamente**; só na tela INFO ou pela USB.

## 5. Wi-Fi, rotas HTTP e atualização

- Com `wifi=true` o aparelho sobe um **AP próprio `SIGHIR - MICxxxx`** (senha `12345678`, IP
  **192.168.1.2**) e tenta conectar como cliente na rede `ssid/passwd` (2,4 GHz). O AP e o cliente dividem
  o rádio: o canal do AP precisa bater com o do roteador — **"Reestabelecer Conexão"** cicla os canais
  1→6→3→11→2. Após 5 min com o display apagado o Wi-Fi dorme (economia).
- Rotas (`http://192.168.1.2/…`): `GET /CHECK` (temperatura, umidade, analog, filtrado, pressão),
  `/TEST`, `/NPTEST` (teste sem soprar — bancada), `/ALCTEST` (força positivo — bancada), `/WIFI`,
  `/SENSOR`, `/RESET`, `/ERASE_SETTINGS`, `/STATUS`, `/INFO` (empresa, placa, IDs e **10 eventos do log
  interno — consumidos na leitura**), `/CLEAN`, `/ALL_CONFIGS`, `/SEND_ALC`, `/update`;
  `POST /WIFI_SETUP` (`$ssid:senha!`), `POST /CONFIG` (comando), `POST /SET_ALL_CONFIGS` (JSON).
  É o que o **app Sighir Monitor** usa.
- **Check-update** (a cada ~30 min, com Wi-Fi): `GET api/v2/devices/check-update/?id=&sensor_id=&firmware=`
  — é **o único momento em que o servidor aprende a versão** (`Device.software_version`, padrão `1.0.0` =
  nunca reportou). Flash por USB não atualiza o campo.
- **Configuração remota** (menu CONFIG 2 ou portal "Configurar Parâmetros"): `POST checkSettings/` →
  mescla chaves nas configurações → `$ETEV07!`. Mensagens: "Dispositivo Configurado", "sem necessidade de
  configuração", "Erro ao Configurar", "sem resposta do servidor", "chaves inválidas".
- **OTA por Wi-Fi**: `POST update/` com o `esp_id` → grava → `$ETEV10!` → reinicia. Só baixa se
  `Device.need_update = true` no servidor; o servidor zera o flag ao servir (**one-shot**).
- **OTA pela USB**: Tester `flash` (~4 min, re-arma `need_update` antes). Grava em partição separada: um
  soluço de USB não inutiliza o aparelho.
- Log interno: `/logs.txt` (LittleFS, ~5 KB, fila) com os eventos emitidos.

## 6. Mensagens de controle que não são eventos

`$ETBL010000!`/`$ETBL020000!` (ordem ao rastreador), `$NOBLOW!` (sopro interrompido), `$ETACK!`
(keep-alive), `$ETKAACK!`/`$ETATACK!`/`$ETEVACK!` (ACKs), `ON`/`OFF` (viagem forçada), `CMD;<id>;04;0x`
(Suntech), `AT+…` (Entrack), `pressworking`, `tempworking`, `success`, `error`, `written`,
`_STARTING_UPDATE_`. O servidor não grava essas mensagens desde 07/04/2026.

Tabela completa de eventos `$ETEVnn!` (significado, linha do firmware, o que chega por telemetria):
`firmware_reference.md` §2 e PPTC `Notion/main.pdf` §2.3.
