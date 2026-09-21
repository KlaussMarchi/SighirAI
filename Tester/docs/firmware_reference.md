# Referência de Firmware do Etilômetro Sighir

> Fonte: leitura completa de `hardware/Main` (firmware ESP32, Arduino/C++).
> Consolidado aqui porque o Sighir Tester AI **não tem acesso permanente** àquela pasta.
> Este é o mapa canônico do protocolo serial, eventos, telemetria e funcionamento.

---

## 1. Plataforma e Hardware

- **MCU**: ESP32. Loop principal = `device.tasks.handle()` (`Main.ino`).
- **Versão de firmware**: **hardcoded** em `Main.ino` → `Device device{"v6.4.0"}`. O comando `$firmware!` devolve essa string.
- **Display**: TFT com touch (interface de menus, teclado, loading, sons/buzzer).
- **Sensores**:
  - **Álcool**: célula aquecida lida por ADC **ADS1115** (I2C 0x48, pino ADC 1; SDA=18, SCL=19). Filtro IIR em `smooth()`. Valor "analog" bruto.
  - **EEPROM do cartucho** (I2C **0x50**): guarda `sensor_id` (bytes 0–19, 1º char forçado p/ 'E' → `ETL...`) e coeficientes de calibração JSON (bytes 19–170: `c1..c4`, `zero`, `timestamp`) + contador de **blows** (vida útil do sensor).
  - **DHT22** (pino 32): temperatura e umidade.
  - **Pressão**: detecção de sopro (`blower`).
- **Relé de bloqueio**: pino **2** (`digitalWrite(relay, LOW)` no block/unblock).
- **Tipos de veículo**: `TRUCK_TYPE=0` (padrão), `CAR_TYPE=1` (setting `vehicle_type`).

> ⚠️ **Build atual está em modo DEBUG** (`Main.ino setup()`): `alcohol.debug=true`,
> `alcohol.bypass=true`, `pressure.debug=false`, `test.alcohol_debug=false`.
> Em debug: `get()` do álcool retorna fixo **23000** (bypass) e `sensor_id` retorna
> valores fixos (`ETL2608402025435219` no protocolo / `ETL3550904305917103` no setup).

---

## 2. Camada Serial (`objects/telemetry/serial/index.h`)

- **Duas UARTs**, ambas 115200 8N1, auto-seleção pela que tiver dados:
  - **Porta 1** = `Serial` (USB) — é por onde o **Tester AI** fala com o device.
  - **Porta 2** = `Serial2` (rastreador/telemetria) — RX=**33**, TX=**26**.
- Mensagens terminadas em `\r\n`. Tamanho: mín 2, **máx 256 bytes**.
- Logs internos no USB: `port changed to 1/2`, etc. → são **ruído**, descartar (a CLI já faz).
- `expect(cmd, target, timeout)` envia e espera substring — padrão de I/O do firmware.

---

## 3. Protocolo Serial — Comandos que o DEVICE RECEBE

Parser em `objects/telemetry/protocol/index.h` (`Protocol::check()`), por `contains()`.
**Atenção ao matching por substring**: `ID:` casa `"D:"`, `CF:` casa `"F:"`.

| Comando enviado | Efeito | Resposta |
|---|---|---|
| `ID:<key>$` | Lê uma setting | `$<value>!` (ou `ERROR`) |
| `CF:<key>$<value>!` | Grava setting + salva | `OK` (ou `NONE`) |
| `$firmware!` | Versão | `v6.4.0` (vazio/estranho = firmware muito antigo) |
| `$ETKA!` | Keep-alive | evento `$ETKAACK!` + resposta `$ETEV17!` |
| `$ETACK!` (`ETACK`) | Sync alternativo | `$ETKAACK!` |
| `$ETRS!` | Reinicia o device | (reinicia) |
| `$erase!` | Reset de fábrica das settings + reinicia | mostra "config de fábrica" |
| `$ETBL01!` (`ETBL01`) | **Desbloqueia** veículo | `$ETKAACK!`, desliga display |
| `$ETBL02!` (`ETBL02`) | **Bloqueia** veículo | `$ETKAACK!`, desliga display |
| `__updt__` (`updt`) | **OTA via USB** (update local) | `_STARTING_UPDATE_` |
| `TST_PRESS` | Diagnóstico de pressão/sopro | `pressworking` / `$ERROR!` |
| `TST_TEMP` | Diagnóstico de temperatura | `tempworking` / `ERROR` |
| `TST_SENS` | Diagnóstico do sensor de álcool | `$ETEV20!` / `$ETEV24!` |
| `endTravel` | Força fim de viagem (`forceDriving(false)`) | `OFF` |
| `analog` | Leitura atual do sensor | valor inteiro |
| `last_analog` | Última leitura do último teste | valor inteiro |
| `sensor_id` | ID do cartucho | `ETL...` |
| `coefs` | Coeficientes de calibração armazenados | JSON dos coefs |
| `cf_coefs` (`...$<json>!`) | Grava coefs na EEPROM do cartucho | `success` / `error` |
| `calibrate` | Roda teste em modo calibração | (executa) |

Chaves especiais no `CF:` → `press`=liga debug de pressão; `testalc`=liga debug de álcool.

> ⚠️ **Durante um teste o parser não roda.** `Test::compute()` só chama `server.handle()`/sensores;
> `telemetry.handle()` (que chama `Protocol::check()`) fica parado. O device **emite** eventos mas
> **não responde a comandos** até o teste terminar.
>
> ⚠️ **`$erase!` é reset de fábrica completo** (`Settings::reset()`): além de regenerar o `esp_id`,
> devolve `telemetry` para **2 (Suntech)**, `wifi=false`, `company=sighir`, `vehicle_type=0`, ssid/passwd
> de fábrica. Um device MIX/Entrack **vira Suntech** depois do erase — reconfigure.

### OTA via USB (`Updater::local()`)
1. Device recebe `__updt__` → responde `_STARTING_UPDATE_`.
2. Recebe firmware em **chunks base64** delimitados por `$...!`; a cada chunk grava e responde `written`.
3. Timeout de 10 s sem dados encerra; ao concluir, `ESP.restart()`.
(Equivale ao `python tools/sighir.py flash`. **One-shot do servidor**: o `/update` zera `need_update`.)

---

## 4. Códigos de Evento — o DEVICE EMITE (`$ETEVxx!`)

Emitidos por `telemetry.event(...)` (vão para o serial **e** para os logs). `$ETEV30` e
`$ETEV36`/`$ETEV40` carregam **payload** colado antes do `!`.

| Código | Significado |
|---|---|
| `$ETEV01!` | Veículo **desbloqueado** |
| `$ETEV02!` | Veículo **bloqueado** |
| `$ETEV05!` | Sopro recebido — **analisando** (~20 s) |
| `$ETEV06!` | Falha no teste de comunicação serial |
| `$ETEV07!` | Device **configurado remotamente** (settings aplicadas via servidor) |
| `$ETEV08!` | Telemetria/boot **online** (fim do setup da telemetria) |
| `$ETEV09!` | Sensor de álcool **inicializado** |
| `$ETEV10!` | **Atualização de firmware (WiFi OTA) concluída** |
| `$ETEV11!` | **Sem sopro inicial** (não soprou) |
| `$ETEV12!` | **Teste aleatório disparado** |
| `$ETEV15!` | Teste **adiado** (postpone normal) |
| `$ETEV16!` | Teste **concluído** (normal) |
| `$ETEV17!` | Resposta de keep-alive / **manobra iniciada** |
| `$ETEV18!` | **Tempo de manobra esgotado** |
| `$ETEV20!` | Sensor de álcool **OK** / aviso de sensor expirando |
| `$ETEV21!` | Sensor **expirado** (blows esgotados / perigo) |
| `$ETEV22!` | **Valet ativado** (desativado = `!ETEV23$`, invertido de propósito) |
| `$ETEV24!` | **Falha** do sensor de álcool / EEPROM |
| `$ETEV25!` | Teste **aleatório concluído** |
| `$ETEV26!` | **Contrassenha aceita** (liberação) |
| `$ETEV27!` | Sensor de temperatura defeituoso **ou** temp alta (>52 °C) |
| `$ETEV28!` | Temperatura **severa** (>60 °C) |
| `$ETEV29!` | Teste OK — **SEM álcool** |
| `$ETEV30<mgL>!` | **Álcool DETECTADO** — valor em mg/L (ponto removido, ex.: `$ETEV30015!` = 0,015) |
| `$ETEV32!` | Valet — desbloqueio (pode ligar o veículo) |
| `$ETEV33!` | Teste aleatório **abandonado** (não soprou) |
| `$ETEV34!` | Teste aleatório **adiado** |
| `$ETEV35!` | **Dirigindo com álcool / sem contrassenha** — alerta de motorista |
| `$ETEV36<id>!` | Novo `sensor_id` detectado/trocado |
| `$ETEV40<n>!` | Tentativa de contrassenha (valor digitado) |
| `$NOBLOW!` | Parou de soprar no meio do teste |
| `$ERROR!` / `ERROR` | Falha genérica de diagnóstico |

**ACKs**: `$ETKAACK!` (keep-alive), `$ETEVACK!` (evento), `$ETBLACK!` (bloqueio), `$ETATACK!` (início de teste).
**Bloqueio bruto p/ rastreador**: `$ETBL010000!` (unblock) / `$ETBL020000!` (block).

---

## 5. Telemetria (rastreadores) — `objects/telemetry/`

Setting `telemetry` (byte) seleciona o modo no boot:

| Valor | Modo | Observações |
|---|---|---|
| 0 | `MIX_TEL` (MIX) | request `$ETACK!` a cada 5 min |
| 1 | `AUTO_TEL` | (constante reservada) |
| **2** | `SUNTECH_TEL` (**default**) | pacotes `STT;...`, request `SttReq` a cada 2 s |
| 5 | `MIX_TEL_NEW` (MIX 2.0) | suporta carro (`ETEV31`) e caminhão (`ETEV03`); timeout 70 s |
| 6 | `ENTRACK_TEL` (Entrack) | comandos `AT+...` |

**Disparo de teste pela telemetria**: ignição ligada com veículo bloqueado ⇒ `test.start()`.

- **MIX / MIX2**: `$ETAT01!` (ETAT01) → `$ETATACK!` + ignição ON (inicia teste). `ETEV04` → `$ETEVACK!` + ignição OFF. MIX2 carro: `ETEV31`→ ON; caminhão: `ETEV03`→ driving=true.
- **Suntech**: lê pacote `STT;...` (campo de chave/ignição na posição 7 do bloco de status); `id` no campo 1. Bloqueio: `CMD;<id>;04;01`; desbloqueio: `CMD;<id>;04;02`.
- **Entrack**: setup `AT+QACC?`/`AT+ID?`; ignição via acelerômetro (`+QACC:high/low`); bloqueio `AT+GPIOVALUE=0,1`, desbloqueio `=0,0`.

`telemetry.working()` = recebeu algo há < 15 s.

---

## 6. Servidor WiFi embarcado (`objects/server/`)

- **AP+STA**. SSID do AP = `SIGHIR - <7 primeiros chars do esp_id>` (ou `SIGHIR ADMIN` se `esp_id == admin_sighir`). Senha `12345678`. IP estático **192.168.1.2**. Porta **80**.
- Liga só se setting `wifi` habilitado. Tenta canais 1→6→3→11→2.

**Rotas HTTP** (todas `Access-Control-Allow-Origin: *`):

| Rota | Método | Ação |
|---|---|---|
| `/CHECK` | GET | JSON: `temperature, humidity, analog, filtered, pressure` |
| `/TEST` | GET | Roda teste |
| `/NPTEST` | GET | Teste com debug de pressão (não precisa soprar) |
| `/ALCTEST` | GET | Teste forçando álcool |
| `/WIFI` | GET | Status WiFi `$0/1!` |
| `/SENSOR` | GET | `sensor_id` |
| `/RESET` | GET | Reinicia |
| `/ERASE_SETTINGS` | GET | Reset de fábrica |
| `/STATUS` | GET | `OK` |
| `/INFO` | GET | JSON de logs (company, esp_id, sensor_id, event) |
| `/CLEAN` | GET | Limpa logs |
| `/ALL_CONFIGS` | GET | Todas as settings |
| `/SEND_ALC` | GET | Info do modelo do último teste |
| `/update` | GET | Dispara OTA por WiFi |
| `/WIFI_SETUP` | POST | Define ssid/passwd (corpo `$ssid:passwd!`) |
| `/CONFIG` | POST | **Injeta um comando serial** (corpo = comando) e devolve a resposta |
| `/SET_ALL_CONFIGS` | POST | Define várias settings (JSON) |

**API na nuvem** (`server` base, default `https://sighir.com:8000/`):
- `GET api/v2/devices/check-update/?id=&sensor_id=&firmware=` → `true` se há update.
- `POST checkSettings/ {esp_id}` → config remota (aplica e emite `$ETEV07!`).
- `POST update/ {esp_id}` → binário do firmware em stream (**one-shot**: zera `need_update`).

---

## 7. Settings (NVS "preferences", `device/settings/index.h`)

Defaults de fábrica (`Settings::reset()`):

| Chave | Default | Significado |
|---|---|---|
| `esp_id` | `generateID()` → `MIC...` | ID nativo (12 dígitos + contrassenha). Cadastro exige `MIC...` |
| `sensor_id` | `None` | ID do cartucho (`ETL...`), atualizado da EEPROM |
| `server` | `https://sighir.com:8000/` | Base da API |
| `company` | `sighir` | Empresa/logo |
| `telemetry` | `2` | Modo de telemetria (Suntech) |
| `last_alcohol` / `last_analog` | `0.0` / `0` | Último resultado |
| `max_postpone` | `3` | Máx. de adiamentos |
| `postpone_time` | `5` | Tempo de adiamento (min) |
| `maneuver_time` | `5` | Tempo de manobra (min) |
| `ssid` / `passwd` | `Etilometro` / `12345678` | WiFi STA |
| `time_of_travel` | `10` | — |
| `number_of_tests` | `1` | — |
| `rand_ppn_time` / `rand_min_time` | `5` / `2` | Teste aleatório |
| `enable_random` | `true` | Liga teste aleatório |
| `brightness` / `volume` | `127` / `255` | Display/buzzer |
| `vehicle_type` | `0` | 0=caminhão, 1=carro |
| `camera` | `5` | Tempo de câmera (s) |
| `bypass` | `false` | Bypass de contrassenha |
| `blowProb` | `0.1` | Probabilidade de sopro aleatório |
| `temp_debug` | `false` | Debug do DHT |
| `lang` | `PT` | Idioma |
| `wifi` | `false` | Liga servidor WiFi |
| `reset` | `0` | Contador de boots (ver §9) |

(`valet`, `press`, `testalc` existem via uso/CF mas não estão nos defaults.)

`generateID()` (`globals/functions.h`): `MIC` + 12 dígitos aleatórios + contrassenha
calculada de 4 dígitos (`parsePassword`).

---

## 8. Fluxo de Teste de Álcool (`objects/test/index.h`)

1. `start()`: prepara display, ignição, telas; checa sensor e blows.
2. `process()`: carrega câmera/calibração; se calibração falha → `TEST_CALIBRATION_FAIL` (refaz em modo turbo). Espera sopro.
3. `compute()`:
   - Sem 1º sopro → `$ETEV11!` (oferece tentar de novo; em aleatório `$ETEV33!` se desistir).
   - Parou de soprar < 1,8 s → `$NOBLOW!`, reaquece, refaz.
   - Sopro OK → `$ETEV05!`, analisa ~20 s (loader), envia `model.getInfo()`.
4. Resultado via `analyze(analog) = a·b^(c·x+d)` (clamp [0; 2,5] mg/L). Com coefs: detecta se `mgl > 0,020`.
   - **Sem álcool**: `$ETEV29!`, status `TEST_OK` → desbloqueia, incrementa blows.
   - **Com álcool**: `$ETEV30<mgL>!`, status `TEST_ALCOHOL` → bloqueia, pede contrassenha (`Pass`).
5. Fim do teste: `$ETEV16!` (normal) ou `$ETEV25!` (aleatório).

**Status de teste** (`constants.h`): `TEST_OK=0`, `TEST_POSTPONED=1`, `TEST_BLOW_TIMEOUT=2`, `TEST_ALCOHOL=3`, `TEST_STARTED=4`, `TEST_CALIBRATION_FAIL=5`.

**Contrassenha** (`objects/test/pass/index.h`): gerada (4 dígitos), validada por `check()`; cada tentativa emite `$ETEV40<n>!`; aceita → `$ETEV26!` + desbloqueia. `bypass`: aceita valor `5`.

---

## 9. Boot, Reset e Proteções

- **Boot** (`Device::setup`): importa settings → `checkSystem` (incrementa contador `reset`) → display/logo → sensores → telemetria (emite `$ETEV08!`) → veículo → teste → servidor (se `wifi`, conecta e checa update). Ao final zera `reset`.
- **`checkSystem`**: se `reset >= 5` (muitos reinícios), assume **alimentação indevida**: baixa brilho, desliga WiFi, desbloqueia veículo e mostra *"Alimentação Indevida / Verifique a Bateria do Veículo"*.
- **`handleRestart`**: reinício automático após **3 dias** ligado **E** 3 h sem ignição **E** 3 h sem valet **E** veículo desligado.
- **`reset()`**: mostra "reiniciando" + `ESP.restart()`.

---

## 10. Mapa de arquivos (em `hardware/Main`)

```
Main.ino                              # versão firmware + setup (flags debug)
device/index.h                        # classe Device (orquestra tudo) + boot
device/settings/index.h               # NVS "preferences" + defaults
device/tasks/index.h                  # loop principal + checkSystem + handleRestart
globals/constants.h                   # TODAS as constantes (telemetry/status/buzzer/cores)
globals/functions.h                   # generateID, base64Decode, parsePassword, mapFloat
objects/telemetry/protocol/index.h    # *** parser de comandos serial ***
objects/telemetry/serial/index.h      # UART dupla, listen/expect/clear
objects/telemetry/index.h             # roteia p/ modo de telemetria + event()
objects/telemetry/modes/{suntech,mix,mix2,entrack}/index.h
objects/diagnostic/index.h            # TST_PRESS/TST_TEMP/TST_SENS, serial test
objects/test/index.h                  # fluxo completo do teste de álcool
objects/test/pass/index.h             # contrassenha
objects/test/{randomic,postpone,screens,model}/
objects/sensors/alcohol/index.h       # ADS1115, smooth(), analyze()
objects/sensors/alcohol/storage/index.h  # EEPROM cartucho: sensor_id + coefs + blows
objects/sensors/{dht,pressure}/index.h
objects/vehicle/index.h               # block/unblock (relé pino 2), forceDriving
objects/vehicle/{ignition,maneuver,valet,camera,driver}/index.h
objects/server/index.h                # AP+STA, HTTP
objects/server/routes/index.h         # rotas HTTP
objects/server/updater/index.h        # OTA WiFi (download) + OTA USB (local)
objects/logs/index.h                  # buffer de eventos
```
