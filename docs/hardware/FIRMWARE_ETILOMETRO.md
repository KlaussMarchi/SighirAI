# Firmware do Etilômetro Veicular Sighir — Documentação Completa e Comentada

> Firmware **v6.4.8.t1** — ESP32 (placa de display WT32-SC01), Arduino framework.
> Diretório: `hardware/Main/`. Sketch de entrada: `Main.ino`.
>
> Este documento percorre **todo** o código-fonte do firmware, arquivo por arquivo, classe por classe,
> método por método, explicando o que cada trecho faz, por que existe, como conversa com o resto do
> sistema e quais são as armadilhas conhecidas. Ao final há tabelas de referência (pinos, parâmetros
> persistidos, eventos de telemetria, comandos seriais, rotas HTTP, sons, cores) e uma seção de
> observações/bugs latentes encontrados durante a leitura.

---

## Sumário

1. [Visão geral do produto e do hardware](#1-visão-geral-do-produto-e-do-hardware)
2. [Arquitetura do código](#2-arquitetura-do-código)
3. [Sequência de boot e loop principal](#3-sequência-de-boot-e-loop-principal)
4. [`Main.ino`](#4-mainino)
5. [`device/` — o objeto raiz e seus auxiliares](#5-device--o-objeto-raiz-e-seus-auxiliares)
6. [`globals/` — constantes e funções livres](#6-globals--constantes-e-funções-livres)
7. [`utils/` — estruturas utilitárias](#7-utils--estruturas-utilitárias)
8. [`objects/sensors/` — sensores](#8-objectssensors--sensores)
9. [`objects/test/` — o teste de alcoolemia](#9-objectstest--o-teste-de-alcoolemia)
10. [`objects/vehicle/` — veículo, ignição, bloqueio](#10-objectsvehicle--veículo-ignição-bloqueio)
11. [`objects/telemetry/` — rastreadores e protocolo serial](#11-objectstelemetry--rastreadores-e-protocolo-serial)
12. [`objects/server/` — Wi-Fi, HTTP, OTA, economia de energia](#12-objectsserver--wi-fi-http-ota-economia-de-energia)
13. [`objects/display/` — LCD, toque, som, interface e menu](#13-objectsdisplay--lcd-toque-som-interface-e-menu)
14. [`objects/diagnostic/` e `objects/logs/`](#14-objectsdiagnostic-e-objectslogs)
15. [Fluxo completo de um teste (ponta a ponta)](#15-fluxo-completo-de-um-teste-ponta-a-ponta)
16. [Tabelas de referência](#16-tabelas-de-referência)
17. [Observações, dívidas técnicas e bugs latentes](#17-observações-dívidas-técnicas-e-bugs-latentes)

---

## 1. Visão geral do produto e do hardware

O etilômetro veicular Sighir é um dispositivo embarcado que **impede a partida/uso do veículo até que
o motorista sopre no sensor e o teste de alcoolemia dê negativo**. Ele:

- lê um **sensor eletroquímico/semicondutor de álcool** através de um ADC externo ADS1115 (I²C), com
  um **aquecedor** controlado por GPIO e uma **EEPROM I²C** no próprio módulo do sensor que guarda o
  ID do sensor, os coeficientes de calibração e o contador de sopros;
- detecta o **sopro** com uma célula de carga/sensor de pressão lida por um **HX711** e classificada
  por uma **floresta aleatória (random forest)** embarcada;
- decide "tem álcool / não tem álcool" com **outra random forest** que olha para a forma da curva do
  sensor durante ~23 s de análise, e converte o valor analógico em **mg/L** pela curva exponencial
  `f(x) = a·b^(c·x+d)` gravada na EEPROM;
- **bloqueia/desbloqueia o veículo** via rastreador (Suntech, Entrack, MIX 1.0 e MIX 2.0) por uma
  UART secundária, e recebe do rastreador o estado da **ignição**;
- tem uma **tela touch 3.5"** (LovyanGFX, placa WT32-SC01) com menu, teclado virtual, barras de
  progresso e telas de alerta, além de um **buzzer** PWM;
- mede **temperatura/umidade** (DHT22) para alertar sobre condições ruins de operação;
- sobe um **ponto de acesso Wi-Fi + cliente Wi-Fi** com um servidor HTTP para configuração pelo app
  desktop (Tauri) e faz **atualização OTA** (por HTTP ou por chunks base64 na serial);
- implementa **testes aleatórios durante a viagem**, **adiamento de teste**, **tempo de manobra**,
  **modo manobrista (valet)**, **contrassenha de liberação** e **espera de câmera**;
- persiste configurações em NVS (`Preferences`) e logs em LittleFS.

### 1.1 Mapa de pinos (ESP32)

| Função | Pino(s) | Onde é definido |
|---|---|---|
| I²C do sensor de álcool (ADS1115 + EEPROM) | SDA **18**, SCL **19** | `objects/sensors/alcohol/index.h` |
| Canal do ADS1115 usado | AIN**1** (`pin = 1`) | idem |
| Aquecedor do sensor | GPIO **0** (ativo em **LOW**) | `objects/sensors/alcohol/heater/index.h` |
| HX711 (pressão) | DOUT **4**, SCK **5** | `objects/sensors/pressure/index.h` |
| DHT22 | GPIO **32** | `objects/sensors/dht/index.h` |
| Buzzer (LEDC canal 0, 8 bits) | GPIO **25** | `objects/display/sound/index.h` |
| Relé de bloqueio | GPIO **2** | `objects/vehicle/index.h` |
| UART2 do rastreador | RX **33**, TX **26** | `objects/telemetry/index.h` |
| UART0 (USB / app desktop) | padrão | `Main.ino`, `NextSerial` |
| Display + touch | autodetect LovyanGFX (`LGFX_WT32_SC01`) | `objects/display/index.h` |

### 1.2 Endereços I²C

| Dispositivo | Endereço |
|---|---|
| ADS1115 | `0x48` (`storage.sensor_addr`) |
| EEPROM do sensor | `0x50` (`storage.eeprom_addr`) |

### 1.3 Bibliotecas externas

`Adafruit_ADS1X15`, `HX711`, `DHT`, `LovyanGFX` (+ `LGFX_AUTODETECT`), `ArduinoJson` (v6,
`StaticJsonDocument`), `Preferences` (NVS), `LittleFS`, `WiFi`/`WebServer`/`HTTPClient`, `Update`
(OTA), `esp_wifi.h`, `esp_pm.h`.

---

## 2. Arquitetura do código

### 2.1 Header-only, "pasta = módulo"

Não há `.cpp`. Cada módulo é uma pasta com um `index.h` e, opcionalmente, subpastas com seus próprios
`index.h`. O include graph segue a árvore de diretórios: `device/index.h` inclui tudo.

### 2.2 O padrão `template <typename Parent>` + ponteiro `device`

Quase toda classe é um template com um único parâmetro `Parent` e guarda um `Parent* device`
injetado pelo construtor. Na prática `Parent` é sempre `Device`. O motivo é evitar dependência
circular de tipos: `Device` contém `Sensors<Device>`, e `Sensors<Device>` precisa chamar
`device->display...`, `device->telemetry...` etc. Como o template só é instanciado depois que
`Device` está completo, tudo compila sem forward declarations nem singletons.

Consequência prática: **qualquer objeto consegue alcançar qualquer outro** via
`device->x.y.z`. O código usa isso intensamente (ex.: `Calibration` chama
`device->display.interface.loading`, `device->test.postpone`, `device->server.handle()`).

Exceção: `Blower<Pressure>` recebe o **`Pressure`** como pai (não o `Device`) e o chama de
`pressure`. E classes "folha" sem dependências (`Ignition`, `EEPROM`, `Temperature`, `Humidity`,
`AlcoholModel`, `BlowerModel`, `DisplayFont`, `Settings`, `Notes`, utilitários) não são templates.

### 2.3 Árvore de objetos (instanciada uma vez em `Main.ino`)

```
Device device{"v6.4.8.t1"}
├── settings : Settings                 (Json<2048> persistido em NVS "preferences")
├── id       : Text<20>                 (esp_id, ex. "MIC123456789012NNNN")
├── diagnostic : Diagnostic<Device>
├── telemetry  : Telemetry<Device>
│   ├── serial   : NextSerial<256>      (UART2 ⇄ rastreador, ou UART0 ⇄ desktop)
│   ├── protocol : Protocol<Device>     (comandos "universais": D:, F:, updt, erase, coefs…)
│   ├── suntech / entrack / mix / mix2  (modos de rastreador)
│   ├── last_cmd : Text<256>, response : Text<64>
├── server : EspServer<Device>
│   ├── routes  : ServerRoutes<Device>  (rotas HTTP em WebServer:80)
│   ├── sleeper : ServerSleeper<Device> (light-sleep + downclock)
│   └── updater : Updater<Device>       (OTA HTTP, OTA serial, checkSettings)
├── vehicle : Vehicle<Device>
│   ├── ignition : Ignition
│   ├── driver   : Driver<Device>       (vazio)
│   ├── maneuver : ManeuverTime<Device>
│   ├── valet    : Valet<Device>
│   └── camera   : Camera<Device>
├── sensors : Sensors<Device>
│   ├── alcohol : AlcoholSensor<Device>
│   │   ├── ads : Adafruit_ADS1115, eeprom : EEPROM
│   │   ├── heater      : Heater<Device>
│   │   ├── calibration : Calibration<Device>   (Array<20> data)
│   │   ├── storage     : Storage<Device>       (id, coefs a,b,c,d, zero, blows)
│   │   │   └── blows   : Blows<Device>
│   │   └── screens     : StorageScreens<Device>
│   ├── pressure : Pressure<Device>
│   │   └── blower : Blower<Pressure>  (+ BlowerModel: RF de 55 árvores)
│   └── dht : sensorDHT<Device>
│       ├── temperature : Temperature
│       └── humidity    : Humidity
├── display : Display<Device>
│   ├── lcd : LGFX
│   ├── brightness, sound, touch
│   └── interface : Interface<Device>
│       ├── loading  : LoadingWindow<Device>
│       ├── menu     : Menu<Device>
│       ├── inputs   : Inputs<Device>
│       ├── keyboard : Keyboard<Device>
│       └── font     : DisplayFont
├── company : Company<Device>
├── tasks   : Tasks<Device>
├── test    : Test<Device>
│   ├── screens  : TestScreens<Device>
│   ├── randomic : Randomic<Device>  (+ RandomicScreens, Travels)
│   ├── postpone : Postpone<Device>
│   ├── pass     : Pass<Device>
│   └── model    : AlcoholModel      (RF de 544 árvores)
└── logs : Logs<Device>  (Notes "/logs.txt" em LittleFS)
```

### 2.4 Estilo de concorrência: **cooperativo e bloqueante**

Não há RTOS tasks nem interrupções próprias. Tudo roda no `loop()` do Arduino. As telas de espera
são **loops bloqueantes** (`while(...)`) que, para não matar o resto do sistema, chamam manualmente
`device->server.handle()`, `device->sensors.warm()`, `device->telemetry.handle()` etc. dentro do
loop. A função `Device::await(ms)` é a versão "educada" de `delay()`: espera `ms` mantendo o servidor
HTTP e o aquecimento do sensor vivos.

Temporização é feita com dois utilitários: `Time::get()` (ms desde o boot, via `esp_timer`) e
`Listener` (timer de período com `ready()`).

### 2.5 Sistema de idiomas

`device/lang/index.h` declara 191 strings em PT/EN/ES num `struct Languages` instanciado como
`inline Languages lang;`. Qualquer lugar chama `lang.algumaChave.get()`, que consulta
`getLang()` (definida em `Main.ino`, lê `settings["lang"]`) e devolve o texto no idioma corrente.
Por isso `device/lang/index.h` é incluído em quase todos os arquivos.

---

## 3. Sequência de boot e loop principal

### 3.1 `setup()` (em `Main.ino` → `Device::setup()`)

```
Serial.begin(115200); delay(700)
flags de debug = false
device.setup():
  settings.import()                   ← carrega NVS "preferences"; se vazio, grava defaults
  in_setup = true
  tasks.checkSystem(true)             ← incrementa contador "reset"; se ≥5, modo "alimentação indevida"
  sensors.dht.debug = temp_debug
  id = settings["esp_id"]
  display.setup()                     ← LGFX init, brilho, som (3 bipes), turnON
  company.sighir(); await(1000)       ← logo Sighir 1 s
  company.setup()                     ← se settings["company"] ≠ "sighir": grava params padrão e REINICIA
  logs.setup()                        ← monta/formata LittleFS
  telemetry.setup()                   ← Serial2, handshake do rastreador escolhido, evento $ETEV08!
  vehicle.setup()                     ← tipo de veículo, maneuver/valet/camera, ignition off
  sensors.setup()                     ← alcohol (I²C, checa sensor+EEPROM, aquecedor ON, lê EEPROM,
                                         evento $ETEV09<id>!), dht, pressure (HX711 + tara), warm(3000)
  test.setup()                        ← postpone, randomic (viagens do NVS "random")
  tasks.checkSystem(false)            ← se contador ≥5: desbloqueia veículo e mostra alerta 30 s
  company.showVersion(); company.logo(); await(3000)
  server.setup(); if enabled: server.connect(true)   ← AP + STA, rotas HTTP, check-update
  display.turnOFF(); sound.twoBeep()
  in_setup = false
  settings["reset"] = 0; settings.save()             ← boot bem-sucedido zera o contador
```

Dois pontos importantes:

- O contador `reset` só é zerado **no final** do `setup()`. Se o ESP reiniciar 5× antes de completar
  o boot (alimentação instável, brown-out), `checkSystem` assume "Alimentação Indevida", reduz o
  brilho, **desliga o Wi-Fi** (`wifi=false`) e **desbloqueia o veículo** para não deixar o motorista
  preso por defeito elétrico.
- `company.setup()` é o mecanismo de "primeira configuração": um dispositivo novo (ou com NVS
  apagado) recebe os parâmetros de `configParams()` e reinicia.

### 3.2 `loop()` → `Tasks::handle()`

```
display.handle()          ← menu (toque) + auto-desligar tela após 60 s sem toque
server.handle()           ← sleeper + WebServer.handleClient() + checagem de update (a cada 100 ms)
test.handle()             ← randomic.handle() (testes aleatórios durante viagem)
if pressure.streaming: pressure.stream()   ← JSON de pressão a 10 Hz na UART (debug do sopro)
if !menu.active: sensors.handle()          ← DHT + calibração do sensor + aquecedor + checagem I²C
if valet.active: return valet.handle()     ← modo manobrista: só escuta serial e ignição
telemetry.handle()        ← lê UART, protocolo, request periódico ao rastreador, lógica do modo
vehicle.handle()          ← maneuver.handle()
handleRestart()           ← reinicia após 3 dias ligado, se parado há >3 h
```

Note que **o teste em si não é chamado do loop**: ele é disparado de dentro de
`telemetry.handleOperation()` (quando a ignição liga com veículo bloqueado), do menu, de uma rota
HTTP, do teste aleatório ou de um comando serial — e roda bloqueante até terminar.

---

## 4. `Main.ino`

```cpp
#include "device/index.h"
#include "device/lang/index.h"
Device device{"v6.4.8.t1"};

const char* getLang(){ return device.settings.params.template get<const char*>("lang"); }

void setup(){
    Serial.begin(115200);
    delay(700);
    device.sensors.pressure.debug = false;   // true → sopro sempre "detectado", HX711 não inicializa
    device.sensors.dht.debug      = false;   // true → temp 25 °C / umidade 80 % fixos
    device.sensors.alcohol.debug  = false;   // true → ignora EEPROM/checagens, id fixo "ETL3550904305917103"
    device.sensors.alcohol.bypass = false;   // true → ADC devolve 23000 fixo
    device.test.alcohol_debug     = false;   // true → todo teste "detecta álcool"
    device.setup();
}

void loop(){ device.tasks.handle(); }
```

- `Device device{"v6.4.8.t1"}` é a **única instância global**. A string é a versão de firmware,
  mostrada no boot, no menu ID e enviada ao servidor no check-update.
- `getLang()` é declarada `extern` em `device/lang/index.h` e definida aqui porque precisa do
  `device` global.
- As cinco flags de debug são o "painel de simulação" para bancada; algumas também podem ser
  ligadas em runtime via comando serial `F:press$1!` / `F:testalc$1!` ou rotas `/NPTEST`,
  `/ALCTEST`.

---

## 5. `device/` — o objeto raiz e seus auxiliares

### 5.1 `device/index.h` — `class Device`

Membros de estado:

| Campo | Significado |
|---|---|
| `startProg` | `Time::get()` no momento da construção — usado por `Heater` (10 min iniciais sempre ligado) e `Tasks::handleRestart` (3 dias) |
| `firmware` | versão |
| `in_setup` | verdadeiro durante o boot; `Updater::handleCheck` só pergunta "atualizar?" se `in_setup` ou menu ativo |
| `settings` | `Settings` |
| `id` | `Text<20>` com o `esp_id` |

Métodos:

- **`setup()`** — descrito na seção 3.1.
- **`await(timeout)`** — espera cooperativa: roda `server.handle()` e `sensors.warm()` até passar
  `timeout` ms. Usado no lugar de `delay()` em praticamente todo lugar. Efeito colateral importante:
  `sensors.warm()` chama `alcohol.calibration.handle()`, `heater.set(true)`, `pressure.blower.handle()`
  e `alcohol.smooth()` — ou seja, **qualquer `await` mantém a calibração, o filtro e o detector de
  sopro atualizados**.
- **`reset()`** — mostra "Reiniciando", bipe de 1,5 s, `ESP.restart()`.

A ordem da lista de inicialização do construtor (`diagnostic, telemetry, vehicle, sensors, display,
server, test, logs, company, tasks`) não coincide com a ordem de declaração; o compilador segue a
ordem de declaração (aviso `-Wreorder`), sem consequência aqui porque todos só guardam o ponteiro.

### 5.2 `device/settings/index.h` — `class Settings`

Wrapper de `Json<2048>` persistido em NVS no namespace `"preferences"`, chave `"settings"`.

- `import()` — `params.download("preferences")`; se vazio → `erase()` (grava defaults). Imprime o JSON
  na serial.
- `get<T>(key)` — atalho para `params.get<T>`.
- `save()` — serializa para NVS.
- `isEnabled(key)` — interpretação tolerante de booleano: `"false"`→false, `"true"`→true, senão
  `toInt() > 0`. Necessário porque valores chegam ora como bool, ora como string (do app / servidor).
- `erase()` — limpa, `reset()`, salva.
- `reset()` — **valores padrão de fábrica**:

| Chave | Padrão | Usado por |
|---|---|---|
| `esp_id` | `generateID()` | identidade do dispositivo |
| `sensor_id` | `"None"` | atualizado por `Storage::setup` com o ID lido da EEPROM |
| `server` | `https://sighir.com:8000/` | `EspServer::URL` |
| `company` | `sighir` | `Company::check` |
| `telemetry` | `2` (Suntech) | `Telemetry::type` |
| `last_alcohol`, `last_analog` | 0 | (gravados mas não lidos de volta) |
| `max_postpone` | 3 | `Postpone::max_tries` |
| `postpone_time` | 5 min | tempo de adiamento normal |
| `maneuver_time` | 5 min | `ManeuverTime::timeout`, `Travels::timeout` |
| `ssid` / `passwd` | `Etilometro` / `12345678` | rede Wi-Fi STA |
| `time_of_travel` | 10 min | `Travels::baseTime` |
| `number_of_tests` | 1 | `Randomic::max_tests` |
| `rand_ppn_time` | 5 min | adiamento em teste aleatório |
| `rand_min_time` | 2 min | tempo mínimo antes de teste aleatório |
| `enable_random` | true | `Randomic::enabled` |
| `brightness` | 127 | `Brightness` |
| `volume` | 255 | `Sound` |
| `vehicle_type` | 0 (caminhão) | `Vehicle::type` |
| `camera` | 5 s | `Camera::timeout`, `Test::MIN_TIME` |
| `bypass` | false | `Pass::bypass` (contrassenha "5") |
| `blowProb` | 0.1 | `Pressure::blowProb` → tolerância do detector de sopro (s) |
| `temp_debug` | false | `sensorDHT::debug` |
| `presstream` | false | `Pressure::streaming` |
| `lang` | `PT` | idioma |
| `wifi` | false | `EspServer::enabled`, `ServerSleeper` |
| `reset` | 0 | contador de reinícios inesperados |

Chaves lidas em outros lugares mas **sem default aqui**: `valet` (Valet::setup), `comm_type`,
`operation_mode`, `maleta` (só gravadas por `Company::configParams`, nunca lidas).

### 5.3 `device/tasks/index.h` — `class Tasks`

- `handle()` — loop principal (seção 3.2).
- `checkSystem(increment)` — chamado duas vezes no boot:
  1. `increment=true` (início): lê `reset`, incrementa e salva. Se `reset_num ≥ 5`: brilho 40,
     `wifi=false`, salva e retorna.
  2. `increment=false` (após sensores): se `reset_num ≥ 5`: brilho 40, `vehicle.unblock()`, tela
     laranja "reinícios inesperados" + bipe ruim 2 s, depois tela preta "veículo desbloqueado" +
     texto vermelho fixo em português "Alimentação Indevida / Verifique a Bateria do Veículo" por
     30 s.
- `handleRestart()` — reinício preventivo: só se ligado há **≥ 3 dias** (`259200000` ms) **e** último
  evento de ignição há **≥ 3 h** **e** não está dirigindo **e** último uso do valet há ≥ 3 h.

### 5.4 `device/company/index.h` — `class Company`

`name = "sighir"` fixo. Os logos por cliente existem em `assets/logos/*_logo.h`, mas este build só
inclui `sighir_logo.h` e `default_logo.h`.

- `setup()` — se `check()` (settings["company"] == "sighir") → `showVersion()`. Senão: tela branca
  "configurando parâmetros", grava `company`, `configParams()`, salva, espera e **reinicia**.
- `configParams()` — conjunto de parâmetros "de provisionamento" (`comm_type=2`,
  `operation_mode=0`, `vehicle_type=0`, `telemetry=0` (MIX!), `enable_random=1`,
  `max_postpone=3`, `postpone_time=5`, `maneuver_time=1`, `time_of_travel=5`,
  `number_of_tests=1`, `rand_ppn_time=2`, `rand_min_time=5`, `camera=5`, `bypass=0`, `maleta=1`).
  Note que difere dos defaults de `Settings::reset` (ex.: telemetria 0 vs 2, maneuver 1 vs 5).
- `sighir(await)` / `logo()` — desenham JPG fullscreen (`drawJpg`).
- `showVersion()` — tela preta "Etilômetro Veicular" + "Versão: v6.4.8.t1" em vermelho, 3 s.

### 5.5 `device/lang/index.h` — idiomas

```cpp
typedef struct Language { const char *PT, *EN, *ES; const char* get() const; } Lang;
struct Languages { Lang startVehicle = Lang("Ligue o Veículo","Start Vehicle","Encienda el Auto"); ... };
inline Languages lang;
```

`get()` retorna PT se `getLang()` for nulo ou desconhecido. Algumas strings contêm `\r\n` (quebra
de linha respeitada por `Interface::centeredText`) e as `inmetro1..5` formam o aviso legal
"Este dispositivo não se enquadra no âmbito probatório de fiscalização ou qualquer outro tipo de
punição legal — Portaria INMETRO Nº369", exibido na tela de análise.

---

## 6. `globals/` — constantes e funções livres

### 6.1 `globals/constants.h`

| Grupo | Valores |
|---|---|
| Tipo de telemetria | `MIX_TEL 0`, `AUTO_TEL 1` (não usado), `SUNTECH_TEL 2`, `MIX_TEL_NEW 5`, `ENTRACK_TEL 6` |
| Tipo de veículo | `TRUCK_TYPE 0`, `CAR_TYPE 1` |
| Status do teste | `TEST_OK 0`, `TEST_POSTPONED 1`, `TEST_BLOW_TIMEOUT 2`, `TEST_ALCOHOL 3`, `TEST_STARTED 4` (não usado), `TEST_CALIBRATION_FAIL 5` |
| Buzzer (Hz) | `NO_SOUND 0`, `BLOW 2600`, `BAD 500`, `RND 800`, `GOOD 2800`, `SIGNAL 2600` |
| Tipos de `msg()` | `MSG_BLACK 0`, `WHITE 1`, `RED 2`, `GREEN 3`, `ORANGE 4` |
| Páginas do menu | `MENU 0`, `ID 1`, `INFO 2`, `CONFIG 3`, `EXIT 4` |
| Cores RGB565 | `BLUE 0x0c1f`, `GREEN 0x4ecc`, `YELLOW 0x24eb`, `BG_COLOR 0x18e3`, `DARK_GREY 0x2104`, `LIGHT_GREY 0xc5d5` |
| Estado do sensor | `EEPROM_FAIL 1`, `SENSOR_FAIL 2`, `SENSOR_OK 3` (definidos, não usados) |
| Limiares | `HEAT_MIN_TIME 5000`, `MIN_ANALOG 5000`, `ANALOG_INVALID 1000`, `EVENT_MIN_INTERVAL 600000` (10 min) |
| Ambiente | `TEMP_ALERT 52 °C`, `TEMP_DANGER 60 °C`, `HUM_ALERT 95 %` |

### 6.2 `globals/functions.h`

- **`mapFloat(x, Xo, X, Yo, Y)`** — interpolação linear de `[Xo,X]` para `[Yo,Y]` **com clamp** ao
  intervalo `[min(Yo,Y), max(Yo,Y)]`. Usada para percentuais (brilho, volume, calibração).
- **`parsePassword(num)`** — gera a "contrassenha" de 4 dígitos do `esp_id`: `num*2+3`; se
  `>9999` divide por 10; se `<1000` faz `num/2+1784`; `0 → 1784`.
- **`randomIntegers(size, numTries)`** — string de `size` dígitos aleatórios; recursão `numTries`
  vezes só para "embaralhar" mais.
- **`warmRandomSeed()`** — `randomSeed(esp_timer_get_time())` + 30 chamadas descartadas de `rand()`
  e `random()`.
- **`generateID()`** — `"MIC" + 12 dígitos + parsePassword(dígitos[0..3])` → 19 caracteres (cabe
  exatamente em `Text<20>`).
- **`jsonToString` / `stringToJson`** — wrappers de ArduinoJson.
- **`base64Decode(input, output, size)`** — decodificador base64 manual, ignora espaços, para em
  `=`. Usado pelo OTA serial (`Updater::local`).
- **`formatTimeString(ms)`** — `"N seg"`, `"N min"` ou `"N h"`.
- **`roundDecimal(f)`** — arredonda para múltiplo de 10 (usado nos percentuais do menu).

---

## 7. `utils/` — estruturas utilitárias

### 7.1 `utils/text/index.h` — `template<int SIZE> class Text`

String de tamanho fixo em buffer estático (`char buffer[SIZE]`, `limit = SIZE-1`), sem heap. Usada
para comandos seriais, IDs, coeficientes e respostas — evita fragmentação de heap que `String`
causaria em um firmware que roda dias sem reiniciar.

API: construtores de `char`, `const char*`, `String`; `operator+=`; `reset/get/set`; `append`
(ignora se cheio); `concat`; `getFirst(n)`; `indexOf(char|const char*, start)`; `find`;
`contains`; `equals`; `charAt`; `length`; `isEmpty` (só brancos conta como vazio); `substring(start,end)`
(retorna outro `Text<SIZE>`); `strip()` (trim in-place com `memmove`); `replace(key, value)` (via buffer
temporário); `remove(char)`; `toString()`; `toInt()`; `print()`.

### 7.2 `utils/time/index.h` — `class Time`

- `static get()` — `esp_timer_get_time()/1000` → ms desde o boot em `unsigned long` (64-bit µs
  dividido; não sofre o overflow de 49 dias do `millis()` na origem, mas o cast para `unsigned long`
  32-bit ainda dá wrap em ~49,7 dias — irrelevante porque `handleRestart` reinicia em 3 dias).
- `static sleep(ms)` — `delay`.
- `alive()` — segundos desde a construção da instância.
- `static getLeft(t0, timeout)` — texto "Tempo Restante: N min/sec" (**adiciona 2 s** ao restante
  para arredondar para cima), usando um `Text<30>` estático.

### 7.3 `utils/listener/index.h` — `class Listener`

Timer de período em microssegundos (`uint64_t`). `ready(auto_reset=true)`: se passou o período,
retorna true e **avança o início pelo período** (mantém fase, evita drift); se atrasou mais de um
período inteiro, ressincroniza com o agora. `reset()`, `set(ms)`, `get()` (ms decorridos), `getSec()`,
`getMin()`, `passed(t0)`.

Padrão de uso onipresente: `static Listener timer = Listener(1000); if(!timer.ready()) return;`.

### 7.4 `utils/array/index.h` — `template<int SIZE> struct Array`

Buffer circular de `float` com estatística e persistência em NVS.

- Campos: `array[SIZE]`, `index`, `isFull`, `junk` (valor de preenchimento, padrão 0), `timeout`
  (para `ready()`), `startTime`, `mean/std/rel`.
- `append(v)` — grava em `index++`, ao dar a volta seta `isFull`.
- `update()` — recalcula `mean`, `std` (**ddof=1**, divide por `length-1` sempre, mesmo se não
  cheio), `rel`.
- `getRel(mean, std)` — **erro padrão relativo em %**: `std/√N/mean·100`; retorna `9999.9` se não
  cheio ou média zero. É a métrica de "estabilidade" usada pela calibração.
- `stable(limit, calculate)` — `rel ≤ limit`.
- `ready()` — timer interno: true a cada `timeout` ms (usado por `AlcoholModel` para amostrar a
  500 ms).
- `get(i)` — índice negativo conta do fim (`get(-1)` = último **posicional**, não o último
  inserido).
- `getMean(first,last)`, `getStd()`, `getMin()` (retorna `int`!), `getMax()`, `getMedian()`
  (bubble sort em cópia), `getSize()` (conta ≠ junk), `fill`, `reset`, `setJunk`, `setTimeout`,
  `print`.
- `download(folder)` / `save(folder)` — `Preferences` com chaves `"buffer"` (bytes) e `"index"`.
  Usado por `Travels` (namespace `"random"`).

### 7.5 `utils/json/index.h` — `template<int SIZE> class Json`

Wrapper de `StaticJsonDocument<SIZE>`: `print`, `empty`, `parse(char*|String)`, várias sobrecargas
de `set`, `get<T>`, `clear` (garante raiz `{}`), `toString`, e `download(ns)`/`save(ns)` que gravam
a string JSON inteira na chave `"settings"` de um namespace NVS.

### 7.6 `utils/filters/index.h`

- **`Smoother<SIZE>`** — média móvel O(1) (soma corrente). Usado como **tara adaptativa** do
  sensor de pressão (`Blower::tare`, janela 20 = 2 s).
- **`ButterworthFilter`** — passa-baixa Butterworth 2ª ordem por transformação bilinear
  (`setup(cutoff_hz, dt)`, `compute(x)`). **Declarado mas não usado**: os filtros IIR do álcool e
  da pressão têm coeficientes hard-coded (provavelmente gerados por esta mesma fórmula offline).

### 7.7 `utils/notes/index.h` — `class Notes`

Arquivo de texto em LittleFS: `setup()` (monta; se falhar, formata e monta), `length`, `read`,
`append` (println), `write` (sobrescreve), `erase`, `readlines(n)` (primeiras n linhas),
`droplines(n)` (remove as n primeiras copiando o resto para `/temp.txt` e renomeando).

---

## 8. `objects/sensors/` — sensores

### 8.1 `objects/sensors/index.h` — `class Sensors`

Agrega `alcohol`, `pressure`, `dht`.

- `setup()` — `alcohol.setup(); dht.setup(); pressure.setup(); warm(3000);`
- `handle()` — `dht.handle(); alcohol.handle();` (pressão não é lida no loop; só sob demanda).
- `warm(timeout)` — o "coração térmico": em loop `do{...}while` (executa **pelo menos uma vez**
  mesmo com `timeout=0`): `alcohol.calibration.handle()`, `alcohol.heater.set(true)`,
  `pressure.blower.handle()`, `alcohol.smooth()`, `server.handle()`. Chamado por `Device::await`,
  portanto **todo `await` força o aquecedor ligado**.

### 8.2 `objects/sensors/alcohol/index.h` — `class AlcoholSensor`

- `setup()` — `Wire.begin(18,19)`, `ads.begin(0x48)`, `check(true)` (bloqueia até sensor e EEPROM
  responderem), `heater.setup()`, `storage.setup()`, `calibration.setup()`. Em debug força
  `storage.id = "ETL3550904305917103"`. Emite `$ETEV09<sensor_id>!`.
- `handle()` — `calibration.handle(); heater.handle(); check();`.
- **`get()`** — leitura crua: se `bypass` → 23000; se a EEPROM (0x48? não — usa `sensor_addr`, o
  ADS) não responde → -1; `ads.readADC_SingleEnded(1)`; retorna -1 se `≤ ANALOG_INVALID (1000)`.
  Valores típicos: **~20000+ = ar limpo / sensor aquecido ("zero")**; o valor **cai** na presença de
  álcool (o modelo usa `min` da curva).
- **`smooth()`** — filtro IIR de 2ª ordem a 100 ms (Listener estático):
  `Yn = 0.196462·Xn + 0.137177·Xn1 + 1.010643·Yn1 − 0.344283·Yn2` (ganho DC ≈ 1). Se `get()`
  falha, repete `Yn1`. Estado em variáveis `static` da função → **há um único filtro global**.
- `sample(timeout=700)` — roda `smooth()` por `timeout` ms e devolve o último valor.
- **`check(force)`** — a cada 60 s (ou forçado): enquanto o ADS não responder → tela
  `sensorFail()`; enquanto a EEPROM não responder → `eepromFail()`. Emite `$ETEV24!` na primeira
  falha e depois no máximo a cada 10 min. Ao sair de uma falha, apaga a tela.
- `failed()` — versão não-bloqueante para o diagnóstico.
- **`analyze(x)`** — curva de calibração `a·b^(c·x+d)` com os coeficientes da EEPROM; clamp: `>2.5
  → 2.5`, `<0.010 → 0`. Retorna mg/L.

### 8.3 `objects/sensors/alcohol/heater/index.h` — `class Heater`

GPIO 0, **LOW = ligado**.

`handle()` a cada 1 s decide o estado:

| Condição | Ação |
|---|---|
| < 10 min desde o boot | ON |
| display ligado | ON |
| veículo dirigindo | ON |
| < 10 min desde a última mudança de ignição | ON |
| > 24 h desde a última ignição | duty **15 min ON / 60 min OFF** |
| caso contrário (parado entre 10 min e 24 h) | duty **5 min ON / 2 min OFF** |

`setDuty(on, off)` alterna quando o tempo no estado atual excede o período. `toString()` → "ligado
por 3 min". Objetivo: manter o sensor aquecido (pronto para teste rápido) sem drenar a bateria do
veículo parado por dias.

### 8.4 `objects/sensors/alcohol/eeprom/index.h` — `class EEPROM`

Não é a EEPROM do ESP; é um helper I²C genérico. `connect(addr)` = ping; `check(addr, timeout)` =
ping repetido a cada 100 ms; `erase(addr, totalBytes=32768, pageSize=16)` = escreve `0xFF` em
páginas de 16 bytes com endereço de 2 bytes (24Cxx de 32 KB), 10 ms entre páginas. O comentário
explica o `pageSize=16`: nenhuma escrita cruza a fronteira da página física de 64 bytes.

### 8.5 `objects/sensors/alcohol/storage/index.h` — `class Storage`

Camada de acesso à EEPROM do módulo sensor. **Layout de memória** (comentado no código):

| Offset | Conteúdo |
|---|---|
| 0–18 | ID do sensor (19 chars; o byte 0 é forçado para `'E'` na leitura) |
| 19–169 | JSON de coeficientes terminado por `;`: `{"c1":a,"c2":b,"c3":c,"c4":d,"timestamp":"...","zero":N};` |
| 210–219 | contador de sopros `" $NNNN!"` |
| `data_size = 256` | faixa apagada por `erase_sensor` |

- `setup()` — `update()`, imprime tudo. Se `id` válido (≥10 chars) e diferente do `sensor_id`
  salvo → evento **`$ETEV36<id>!`** (troca de sensor) e atualiza settings.
- `update()` — lê ID, lê coefs, recorta entre `{` e `;`, parseia JSON em `a,b,c,d`,
  `has_coefs = todos > 0`, `calibration_date`, `zero` (default 20000), `blows.update()`.
- `writeByte/readByte/read/write` — acesso byte a byte com endereço de 16 bits; cada operação faz
  `device->await(10)`.
- `genCoefs(data)` — recebe o payload do comando serial `cf_coefs` (`$...!`), escreve **a partir
  do offset 0** (o payload traz ID + JSON), tenta até 6 vezes, `setup()` de novo.

### 8.6 `objects/sensors/alcohol/storage/blows/index.h` — `class Blows`

Contador de vida útil do sensor. Limiares: `REMINDER 1750`, `WARNING 2000`, `CAUTION 2250`,
`LAST 2400`, `DANGER 2500` (`deprecated = value > 2500`).

- `update()` — lê `" $NNNN!"` do offset 210.
- `increment()` — grava `value+1`. Chamado **só em `TEST_OK`**.
- `check()` — chamado no início de todo teste: se `≥ 1750`, `stage()` mostra a tela adequada
  (do mais grave ao mais brando, para nenhum valor de borda ficar sem aviso) e emite
  `$ETEV13NNNN!` (ou `$ETEV14NNNN!` se expirado) com **4 dígitos fixos** — a telemetria lê por
  posição. Cada estágio espera 2/4/6/8/10(+30) s com `server.wait()`.

### 8.7 `objects/sensors/alcohol/screens/index.h` — `class StorageScreens`

Duas telas de alerta: `sensorFail()` ("mau contato, verifique conexão") e `eepromFail()` ("sensor sem
EEPROM, manutenção"), 6 s + 3 s.

### 8.8 `objects/sensors/alcohol/calibration/index.h` — `class Calibration`

Aqui "calibração" significa **estabilização do zero do sensor** antes de um teste (não a curva
a,b,c,d). Estado: `Array<20> data` (últimas 20 leituras cruas a cada 500 ms), `newZero`, `percentage`,
`done`, `had_to_wait`, `toleranceTimer` (20 s).

- **`handle()`** — a cada 500 ms, fora do menu, se não (`done` e teste ativo), se não bypass/debug:
  lê `get()`, `data.append`, `data.update()`. Atualiza `newZero` quando a média é estável
  (`mean > 5000 && rel < 0.15 %`) ou muito alta (`> 20000`): **com display ligado usa a média; com
  display desligado usa `mean − 1500`** (compensa o aquecimento extra que o display ligado provoca).
  Depois `percentage = processPercent()` e `stateUpdate()`.
- `processPercent()` — 100 % se `mean > 0.98·zero_da_EEPROM` ou `mean > 0.98·newZero`; senão
  `getPercent(mean)` = `mapFloat(analyze(mean), 0.5→5 %, 0.0→100 %)` — isto é, quão perto de
  "0,00 mg/L" o sensor está lendo.
- `stateUpdate()` — `calibrated = mean > 20000 || (newZero > 5000 && percentage == 100 && rel < 0.20)`.
  Se `!ready()` (ainda dentro do tempo de purga pós-álcool) → `done=false`. Se calibrado → `done=true`
  e reseta o timer de tolerância; se descalibrou, só marca `done=false` após **20 s** contínuos
  (histerese).
- `setDebug(v)` — modo "calibrate" do desktop: liga debug de pressão e álcool, desabilita a
  contrassenha, `bypass=true`; ao desligar restaura.
- **`prepare()`** — imediatamente antes do sopro: amostra 700 ms; válido se `analog > 5000 &&
  newZero > 5000` e (`analog > newZero` ou `|newZero − analog| < 2500`). Se inválido (e não debug)
  → `reset()` e retorna false → `TEST_CALIBRATION_FAIL`. Se válido, `newZero = analog` (o zero do
  teste é a leitura instantânea).
- **`load()`** — tela "Calibrando Sensor" com barra de progresso. Se `done` já → retorna false
  (nada a fazer). Se `!ready()` → `awaitScreen()`. Loop até `done`: mostra `mean − temperatura` em
  vermelho no topo; ao chegar a 100 % muda o título para "Estabilizando" e exige **12 s** em 100 %.
  Timeout de **7 min** → "calibração travada", devolve um adiamento ao usuário (`postpone.index--`)
  e retorna true (= adiar). Toque na tela (se adiamento permitido e sem álcool no último teste) →
  true (= adiar).
- `getWarmTime()` — tempo de purga após teste positivo em função de `last_analog`: `<7000 → 5 min`,
  `<15000 → 4`, `<17000 → 3`, senão 2 min. `getRefreshTime()` = quanto falta desde
  `test.endRequestTime`. `ready()` = sem álcool no último teste ou purga concluída.
- `awaitScreen()` — tela "Aquecimento Necessário" com barra contando a purga (toque adia); ao
  terminar, `had_to_wait = true` e chama `load()`.

### 8.9 `objects/sensors/pressure/index.h` — `class Pressure`

HX711 nos pinos 4/5. `blowProb` (settings, default 0.1) vira `blower.tolerance = 100 ms`.

- `setup()` — lê settings, `scale.begin` (exceto debug), `blower.setTolerance`, `tare()`.
- **`get()`** — a cada 100 ms lê `scale.read()/10000` e aplica IIR 2ª ordem
  `Y0 = 0.016239·X0 + 0.014858·X1 + 1.734903·Y1 − 0.766·Y2` (ganho DC ≈ 1, corte bem baixo —
  suaviza forte). Na primeira leitura "semeia" os estados com o valor lido para não ter transiente.
- `stream()` — se `presstream`, envia JSON `{"time","pressure","blow"}` a 10 Hz na UART do
  rastreador/desktop (ferramenta de coleta de dataset para o modelo de sopro).
- `check(timeout)` — `scale.is_ready()` com espera.
- `warm(timeout)` — roda `blower.handle()` + servidor por `timeout` e `blower.reset()`.
- **`tare(show)`** — se o detector já dizia "soprando" no momento da tara, mostra "Calibrando
  Pressão", roda `sensors.warm()` 1,5 s e se ainda soprando, tenta de novo (recursão). Serve para
  descartar um estado espúrio antes de pedir o sopro.
- `getFirstBreath()` — espera até **25 s** pelo primeiro `blower.state`; bipa quando detecta.

### 8.10 `objects/sensors/pressure/blower/index.h` — `class Blower<Pressure>`

Detector de sopro baseado em ML.

- `update(value)` — mantém `Smoother<20>` como tara (média móvel de 2 s) e um vetor `states[40]`
  com as últimas 40 amostras (4 s a 10 Hz) de `value − tara` (pressão "destendenciada"); chama
  `model.get(states)`.
- `handle()` — a cada 100 ms: em debug `state=true`. Senão `blowing = update(pressure->get())`.
  Se `blowing`: `startBlow = agora`, e após **7 detecções consecutivas** (`CONFIRM`) → `state=true`.
  Se não: `counter=0`; e se passaram mais de `tolerance` ms desde a última detecção → `state=false`.
- `get()` — `handle()` + `state`. `reset()` — zera tudo, `state=false`.

`model.h` — `class BlowerModel`: **random forest com 55 árvores / 26.779 nós** armazenada em
`MODEL_ROOT[55]`, `MODEL_FEATURE[]` (índice do estado 0–39, −1 = folha), `MODEL_VALUE[]` (limiar
ou, na folha, probabilidade), `MODEL_RIGHT[]` (filho direito; o esquerdo é sempre `node+1`).
`get()` percorre cada árvore, soma a probabilidade da folha, divide por 55 e compara com
`THRESHOLD = 0.4125`. Constantes: `STATES 40`, `WINDOW 20`, `CONFIRM 7`, `TOLERANCE 500`.

`blower (bkp)/index.h` é a versão anterior: **k-means de 2 centróides** sobre 5 estados
normalizados (StandardScaler) — mantida como backup, não incluída no build.

### 8.11 `objects/sensors/dht/` — DHT22

- `sensorDHT` (`index.h`): pino 32, `Temperature` e `Humidity` compartilham o `DHT dht`. `setup()`
  faz `dht.begin()` e uma leitura; `update()` força leitura; `handle()` lê (a cada 5 s cada) e roda
  `checkTemperature()` / `checkHumidity()`.
  - `checkTemperature()` — a cada 15 min (ou na 1ª vez), **só com display desligado**: sensor
    quebrado → alerta vermelho "sensor defeituoso" + `$ETEV27!`; `≥ 60 °C` → "temperatura grave" +
    `$ETEV28!`; `≥ 52 °C` → laranja "temperatura alta" + `$ETEV27!`.
  - `checkHumidity()` — a cada 5 min, display desligado, `≥ 95 %` → laranja "umidade alta" e
    `$ETEV41!` no máximo a cada 10 min.
  - `alert(...)` — `interface.alert(..., 10000, turnoff=true)` + evento.
- `Temperature` / `Humidity`: `get()` lê; conta leituras inválidas consecutivas (`index`), `working
  = index < 8`; `handle(force)` só aceita valores válidos (temp `|t|<100`, umidade `0..100`).
  Defaults 25 °C / 80 %. Em debug retornam os defaults.

---

## 9. `objects/test/` — o teste de alcoolemia

### 9.1 `objects/test/index.h` — `class Test` (máquina de estados do teste)

Campos: `lastTime` (fim do último teste), `startRequestTime` (início — usado pela câmera),
`endRequestTime` (fim de teste OK/álcool — usado pela purga), `active`, `had_alcohol`,
`last_analog`, `last_alcohol` (mg/L), `MIN_TIME` (calculado, **não usado**), `alcohol_debug`,
`status`.

- `setup()` — `postpone.setup(); randomic.setup();`
- `handle()` — `randomic.handle()`.
- `reset()` — `active=false; lastTime=agora`.

**`start(turbo=false)`** — `turbo` significa "pular as telas de introdução e câmera" (usado em
re-tentativas, testes aleatórios, menu e comando `calibrate`).

```
menu.reset(); brightness 120; ignition.reset(); startRequestTime=agora; pass.liberated=false; active=true
screens.start()                    ← liga display, "Teste Iniciado"
sensors.alcohol.check()            ← garante ADS+EEPROM
storage.blows.check()              ← avisos de vida útil do sensor
screens.start(); screens.beep()
status = (!turbo && startLoadings()) ? TEST_POSTPONED : process(turbo)
brightness.reset(); await(100)
if calibration.debug: return       ← modo "calibrate" do desktop: só coleta
if OK ou ALCOHOL: evento $ETEV25! (aleatório) ou $ETEV16! (normal); endRequestTime=agora
if CALIBRATION_FAIL: calibration.reset(); tela "recalibrando"; return start(true)   ← re-tenta
if POSTPONED: clicked = postpone.start(); if ignição ligada: return start(clicked)
if OK: blows.increment(); vehicle.unblock(); postpone.reset(); pass.reset()
if ALCOHOL && !driving && pass.enabled: vehicle.block(); pass.start(); if pass.required(): block()
if (ALCOHOL || BLOW_TIMEOUT) && driving && !pass.liberated: $ETEV35!; alertDriver()
display.turnOFF(); active=false
```

- `startLoadings()` — se adiamento permitido, `screens.waitUser()` dá 5 s para tocar e adiar
  ("adiamento de emergência"); senão mostra logo Sighir 1 s e logo do cliente 1 s.
- **`process(turbo)`**:
  1. `!turbo && camera.load()` → toque = `TEST_POSTPONED` (espera a câmera do rastreador ficar
     pronta);
  2. `calibration.load()` → true = `TEST_POSTPONED`;
  3. `!calibration.prepare()` → `TEST_CALIBRATION_FAIL`;
  4. se `!turbo || had_to_wait` → `screens.input()` (60 s "toque para iniciar");
  5. `!compute()` → `TEST_BLOW_TIMEOUT`;
  6. `analog = model.min`; `mgl = analyze(analog)`;
     `detected = has_coefs ? (model.result && mgl > 0.020) : model.result`;
     `had_alcohol = detected || alcohol_debug`; se não detectou, `mgl = 0`;
     se detectou (ou o modelo disse sim) → `calibration.data.reset()` (força reestabilizar);
     `last_alcohol/last_analog`; `show()`; `reset()`; retorna `TEST_ALCOHOL`/`TEST_OK`.
- `show()` — mostra "X.XXX mg/L" com o analógico embaixo por 1,5 s; evento
  **`$ETEV30<mgl sem ponto>!`** (ex.: `0.420` → `$ETEV300420!`) ou `$ETEV29!` (negativo); se
  positivo, tela vermelha "Álcool Detectado" + bipe ruim.
- **`compute()`** — a coleta propriamente dita:
  1. `model.init(newZero)` (1ª amostra = zero), brilho 50, `pressure.tare(true)`, `screens.blow()`;
  2. `getFirstBreath()` (25 s). Sem sopro: "Não soprou", `$ETEV11!`, pergunta "tentar de novo?"
     (sim → recursão `compute()`); não → `$ETEV33!` se aleatório, retorna false;
  3. **Fase de sopro (3 s)**: `model.add(smooth())` (amostra a cada 500 ms), bipe intermitente
     75 ms, checa `blower.get()`; se parou de soprar **antes de 1,8 s** → "não soprou", `$NOBLOW!`,
     `pressure.warm(2000)`, recursão `compute()`;
  4. **Fase de análise**: `$ETEV05!`, som off, tela INMETRO com barra de 25 % da altura
     ("Analisando"); loop `model.add(smooth())` até `model.done` (47 amostras → ~23 s). Barra:
     `(index−7)/40·100`;
  5. `model.update()`; envia o vetor de 47 amostras pela serial (`getInfo()`); retorna true.
- `getTime()` — ms desde `lastTime` se ativo.
- `alertDriver()` — "Motorista não autorizado / estacione o veículo", bipe grave a cada 500 ms
  **até a ignição desligar**, então `block()` e `reset()`.

### 9.2 `objects/test/model/index.h` — `class AlcoholModel`

Classificador "tem álcool?" sobre a **forma da curva** de 47 amostras (`MAX_SAMPLES`) do sensor
tomadas a 500 ms (`data.setTimeout(500)`; `add()` ignora `< ANALOG_INVALID` e respeita `data.ready()`).

`update()` calcula 16 estatísticas: `min, max, mean, std, first, last, median` de `data`;
derivada central `data_diff[x] = (d[x+1] − d[x−1])/2` (bordas com diferença simples) e suas
`min_diff, max_diff, mean_diff, std_diff, first_diff, median_diff`; `decay = first − min`,
`rise = first − max`, `amplitude = max − min`. Depois `result = get()`.

`get()` monta o vetor de **15 features** na ordem `[decay, mean_diff, min, mean, median, last, rise,
std, amplitude, max_diff, min_diff, max, first_diff, median_diff, std_diff]`, aplica
`(x − OFFSET)·GAIN` (StandardScaler exportado: média e 1/desvio) e chama `evaluate_rf(x)` de
`rf_model_data.h`: **random forest de 544 árvores / 42.028 nós** (`tree_roots`, `features`,
`values`, `left_child`, `right_child`), probabilidade média > `BEST_TRESH = 0.7427` → álcool.

`getInfo()` → `"\n[v0,v1,...,]"` (`Text<350>`) para a serial e a rota `/SEND_ALC`.

`lr_old.h` é o modelo anterior (**regressão logística** com 14 features, sigmoid, limiar 0.4256) —
mesmo `#ifndef ALCOHOL_MODEL_H`, então **não pode ser incluído junto**; está fora do build.

### 9.3 `objects/test/postpone/index.h` — `class Postpone`

Adiamento do teste ("preciso mover o veículo agora").

- `setup()` — `max_tries = max_postpone`; se 0 e aleatório habilitado → 1.
- `getTimeout()` — `rand_ppn_time` se em teste aleatório, senão `postpone_time` (min → ms).
- **`start()`** — `vehicle.unblock()`, `forceDriving(true)` (evento `ON`), som off, `index++`,
  `active=true`, tela "Teste Adiado N/M por X min" (`$ETEV34!` aleatório / `$ETEV15!` normal), 3 s,
  "Toque para iniciar" com contagem regressiva (`update()` a cada 45 s via `ready()`). Loop: telemetria
  + `sensors.warm()`; toque central → **true** (usuário quer testar agora); se ignição desligada há
  > 7 s → `block()` e sai; timeout → **false**.
- `allowed()` — `index < max_tries`. `reset()` zera.

### 9.4 `objects/test/pass/index.h` — `class Pass`

Contrassenha para liberar o veículo após teste positivo (um supervisor por telefone dá a senha).

- `start()` — `trichoices("Contrassenha", "Realizar outro teste", "Desligar display")`.
  Opção 1 → `test.start(true)`; 2 → desliga display; 0 → loop `handleStandard()` (ou
  `handleBypass()` se `bypass`).
- `handleStandard()` — gera `generated = 1000 + rand()%9000`, mostra no teclado como título,
  lê o que foi digitado, evento **`$ETEV40<digitado>!`**, `index++`. `check()` OK → `liberate()`.
  Errado → "senha incorreta", até `MAX_TRIES=3` com "tentar de novo?".
- **`check(pass, counter)`** — inverso de `parsePassword`: aceita `counter` tal que
  `(counter−3)/2 == pass`, ou `(counter·10−3)/2 == pass` (caso em que a senha original foi
  truncada por `/10`), ou qualquer `counter·10+i` (i = 1..9) satisfazendo a 1ª fórmula.
- `handleBypass()` — aceita literalmente `5`.
- `liberate()` — `$ETEV26!`, `unblock()`, `driving=true`, `had_alcohol=false`, `postpone.reset()`,
  `liberated=true`.
- `required()` — `test.had_alcohol` (o menu mostra o botão "Desbloquear Veículo" enquanto true).

### 9.5 `objects/test/screens/index.h` — `class TestScreens`

Telas do teste: `start()` (liga display, "Teste Iniciado"), `beep()` (2 bipes), `inmetro()` (aviso
legal com "ATENÇÃO" em vermelho), `input()` (60 s "Clique para iniciar", contagem "Iniciando em NN
seg", `sensors.warm()` no loop, toque encerra), `waitUser()` (5 s para "adiamento de emergência",
retorna true se tocou), `killdriver()`, `blow()` ("Sopre" + 2 bipes), `calibrationFail()`.

### 9.6 `objects/test/randomic/index.h` — `class Randomic`

Testes aleatórios durante a viagem.

- `setup()` — `enabled = enable_random`, `max_tests = number_of_tests`, `travels.setup()`.
- **`handle()`** (do loop): se habilitado e dirigindo: `travels.update()`; se ainda não agendou e a
  viagem "começou" (dirigindo há > 60 s) → `update()`; se monitorando e a viagem "terminou"
  (parado por mais que `maneuver_time`) → `reset()`; se `ignition.getTime() > nextTest` e o sensor
  está calibrado → `start()`.
- `update()` — `index++`; se `index > max_tests` → acabou. Senão sorteia `nextTest` entre
  `minTime` (`rand_min_time`) e `maxTime = mean·index/max_tests` (ou `0,8·mean` no último), e
  **zera o cronômetro da ignição** (`resetTime()`), de modo que o próximo teste conta a partir de
  agora.
- **`start()`** — se não está dirigindo, só desliga display. Volume máximo, `$ETEV12!`,
  `active=true`. Se já em adiamento ou adiamento esgotado → `test()` direto. Senão: `screens.alert()`
  (sequência de bipes/telas), `bichoices("Iniciar Teste", "Adiar")`, espera até 3 min com bipe a
  cada 2 s; metade inferior = adiar; timeout ou adiar → `postpone.start()` e recursão `start()`.
- `test()` — `test.start(true)`, `postpone.reset()`, `active=false`, `update()` (agenda o próximo).
- `toString()` — "Ativo/Desativado – Monitorando/Não iniciado" para o menu.

`travels/index.h` — `class Travels`: histórico de durações de viagem em `Array<10>` persistido em
NVS `"random"`. `baseTime = time_of_travel`, `minTime = rand_min_time`, `timeout = maneuver_time`.
`getMeanTime()` = média das viagens se o buffer estiver cheio (e `baseTime ≠ 5 min`), senão
`baseTime`. `increment()` grava a duração da viagem (≥ minTime) — **nunca é chamado** no código
atual, então a média fica sempre em `baseTime` a menos que o NVS já tenha dados.

`screens/index.h` — `class RandomicScreens`: `bichoices(upper, lower)` (só desenha, amarelo/cinza)
e `alert()` (3 flashes preto/branco "Teste Aleatório" com bipes 800 Hz).

---

## 10. `objects/vehicle/` — veículo, ignição, bloqueio

### 10.1 `objects/vehicle/index.h` — `class Vehicle`

Estado: `driving`, `blocked` (inicia **true**), `turnedON/turnedOFF` (flags de borda setadas pelos
modos de telemetria, zeradas em `reset()`), `type`, `unblockedTime`, `relay = 2`.

- `setup()` — tipo, `blocked=true`, sub-setups, `ignition.set(false); ignition.reset()`.
- **`block()`** — cancela adiamento e manobra, `blocked=true; driving=false`, tela vermelha "Veículo
  Bloqueado" + bipe ruim; Suntech → `CMD;<id>;04;01`; Entrack → `AT+GPIOVALUE=0,1`;
  `digitalWrite(2, LOW)`; eventos `$ETBL020000!` e `$ETEV02!` (400 ms entre cada).
- **`unblock()`** — `unblockedTime=agora`, `blocked=false`, tela verde "Veículo Desbloqueado" + bipe
  bom; Suntech `CMD;<id>;04;02`; Entrack `AT+GPIOVALUE=0,0`; `digitalWrite(2, LOW)`; `$ETBL010000!`
  e `$ETEV01!`.
  > Repare: o relé (GPIO 2) vai para **LOW nos dois casos** — o bloqueio real é feito pelo
  > rastreador via comando, não pelo pino.
- `forceDriving(state)` — usado pelo adiamento e pelo comando `endTravel`: seta
  `blocked/driving/ignition` de uma vez e emite `ON`/`OFF` na serial.
- `update()` → `maneuver.update()`; `handle()` → `maneuver.handle()`; `reset()` zera bordas.

### 10.2 `objects/vehicle/ignition/index.h` — `class Ignition`

`on/off`, `changed` (borda desde o último `reset()`), `startTime` (momento da última mudança).
`set(v)` marca `changed` se diferente e reinicia `startTime`. `getTime()` = tempo no estado atual.
`resetTime()` reinicia o cronômetro sem mudar estado (usado pelo aleatório).

### 10.3 `objects/vehicle/maneuver/index.h` — `class ManeuverTime`

"Tempo de manobra": após desligar a ignição, o veículo fica desbloqueado por `maneuver_time` para
o motorista reposicionar sem novo teste. Com MIX 1.0 força 5 min.

- `update()` (chamado pelos modos de telemetria a cada `handle`): se ativo e ignição ligou →
  `unblock()`; borda de `driving` para true → `vehicleON()` ("Veículo Ligado" 3 s, tela off);
  ignição desligou (com timeout > 0) → `vehicleOFF()` ("Veículo Desligado" 3 s); ignição desligou
  e não bloqueado → `start()`.
- `start()` — `active=true`, reinicia `ignition.startTime`, `$ETEV17!`, `draw()` (tela com "Tempo
  Restante") e reseta o timer de redesenho (10 s).
- `handle()` (do loop): se bloqueado ou dirigindo → desativa; redesenha a cada 10 s (fora do menu);
  se expirou → `end()` ("Tempo Esgotado", `$ETEV18!`), `block()`, tela off. Não age se
  contrassenha pendente ou adiamento ativo.

### 10.4 `objects/vehicle/valet/index.h` — `class Valet`

Modo manobrista: com `settings["valet"]` habilitado, aparece um botão no menu. `start()` alterna
`active`, evento `$ETEV22!` (ligou) ou **`!ETEV23$`** (desligou — delimitadores invertidos, o app
desktop trata). Ao desligar com ignição ligada → `test.start()`; senão bloqueia.

`handle()` substitui o loop principal enquanto ativo: só escuta serial, protocolo e request; se a
ignição ligar → `unblock()` ("aguarde tela verde", `$ETEV32!`, desbloqueia, "ligue o veículo").

### 10.5 `objects/vehicle/camera/index.h` — `class Camera`

Espera a câmera do rastreador ficar pronta antes do teste: `timeout = camera·1000`. `load()`
mostra a tela INMETRO com barra "Aguardando câmera" (30 % da altura) pelo tempo restante desde
`startRequestTime`; toque (se adiamento permitido) → true (adiar).

### 10.6 `objects/vehicle/driver/index.h` — `class Driver`

Esqueleto vazio (`drunk`, `allowed`, `alert(){}`), não usado.

---

## 11. `objects/telemetry/` — rastreadores e protocolo serial

### 11.1 `objects/telemetry/serial/index.h` — `template<int N> class NextSerial`

Abstração da UART com **auto-seleção de porta**: começa em `Serial2` (rastreador, RX 33/TX 26); em
`listen()`, se chegar algo em `Serial` (USB) muda para porta 1, e vice-versa. É assim que o app
desktop "rouba" a conversa ao plugar o USB.

- `listen()` — a cada 100 ms: troca de porta se necessário; lê tudo que houver (até 1 s), com
  `delayMicroseconds(2000)` quando o buffer esvazia (espera o resto do pacote); `clean()` (remove
  `\r\n\t`, descarta se < 2 ou > 256 chars); `available = length > 0`; `lastAckTime`.
- `send(msg, breakLine=true)` — escreve + `\r\n`.
- `expect(cmd, target, timeout)` — envia `cmd` e espera uma linha contendo `target` (handshakes
  Suntech/Entrack).
- `clear`, `read`, `reset`, `print`, `await`.

### 11.2 `objects/telemetry/index.h` — `class Telemetry`

- `setup()` — `type = settings["telemetry"]`, `serial.setup()`, `setup()` do modo escolhido,
  evento **`$ETEV08!`** (boot).
- `handle()` — `serial.listen()`; `handleProtocol()` (modo `.check()` + `protocol.check()` se há
  comando); `handleRequest()` (keep-alive periódico do modo); se `response` preenchida → `event()`;
  guarda `last_cmd`; `handleOperation()` (lógica ignição→teste do modo); `serial.reset()`.
- `event(value, onlyApp=false)` — grava em `logs`, envia pela serial (a menos que `onlyApp`), limpa
  `response`. **É a única saída de eventos `$ETEVxx!`** do firmware.
- `working()` — recebeu algo nos últimos 15 s.
- `toText()` — nome do modo para o menu.

### 11.3 `objects/telemetry/protocol/index.h` — `class Protocol`

Comandos aceitos em qualquer modo, por `contains()` (a **ordem importa**: `erase_sensor` antes de
`erase`, `cf_coefs` antes de `coefs`, `last_analog` antes de `analog`):

| Comando recebido | Ação | Resposta |
|---|---|---|
| `D:<chave>$` | lê `settings[chave]` | `$<valor>!` ou `ERROR` |
| `F:<chave>$<valor>!` | grava setting (`press` → debug pressão, `testalc` → debug álcool) | `OK` |
| `updt` | OTA por serial (`Updater::local`) | `_STARTING_UPDATE_` … |
| `ETRS` | reinicia | — |
| `firmware` | — | versão |
| `ETBL02` | bloqueia + tela off | `$ETKAACK!` |
| `ETBL01` | desbloqueia + tela off | `$ETKAACK!` |
| `erase_sensor` | apaga 256 bytes da EEPROM | `success`/`error` |
| `erase` | reset de fábrica (`settings.erase()`) + reinício | — |
| `ETACK` | — | `$ETKAACK!` |
| `ETKA` | envia `$ETKAACK!` | `$ETEV17!` |
| `TST_TEMP` / `TST_SENS` / `TST_PRESS` | diagnóstico | eventos |
| `endTravel` | `forceDriving(false)` | `OFF` |
| `last_analog` | — | último analógico do teste |
| `analog` | — | leitura crua atual |
| `sensor_id` | relê EEPROM | ID |
| `cf_coefs$...!` | grava ID+coefs na EEPROM | `success`/`error` |
| `coefs` | relê EEPROM | JSON de coefs |
| `calibrate` | `setDebug(true)`; `test.start(true)`; `setDebug(false)` | dados do teste |

Os dois blocos `ETBL01`/`ETBL02` duplicados depois de `ETKA` são **inalcançáveis** (já casaram
acima).

### 11.4 Modos de rastreador (`modes/`)

Todos têm a mesma interface: `setup()` (handshake/tela), `request()` (keep-alive periódico),
`check()` (parse do que chegou → `ignition.set`), `handle()` (**a regra de ouro**):

```
se ignição ligou (borda):  turnedON=true; se bloqueado && !dirigindo → test.start(); driving = !blocked
se ignição desligou && dirigindo: turnedOFF=true; driving=false
vehicle.update(); vehicle.reset()
```

| Modo | `request()` | `check()` | `block/unblock` |
|---|---|---|---|
| **MIX** (0) | `$ETACK!` a cada 5 min | `ETAT01` → ign ON (`$ETATACK!`); `ETEV04` → ign OFF (`$ETEVACK!`) | — (via `$ETBL0x0000!`) |
| **MIX2** (5) | idem | idem + `ETEV31` (carro) → ign ON; `ETEV03` (caminhão) → `driving=true`. Só carro seta `driving` na borda. Extra: se ignição ON há > 70 s sem dirigir e sem teste há > 70 s → "tempo esgotado", `block()` | — |
| **Suntech** (2) | `SttReq` a cada 2 s | espera `expect("SttReq","STT;",20 s)`; parse do relatório `T;...;` por `;`: campo 1 = ID, campo 14 ou 19 (conforme tamanho) char 7 = chave; `Array<4>` de estados com histerese (`>0.9` ON, `<0.1` OFF; pela USB aceita direto) | `CMD;<id>;04;01` / `;04;02` |
| **Entrack** (6) | `AT+QACC?` a cada 2 s | `expect("AT+QACC?","OK")`, `AT+ID?` → ID; configura `AT+ASSISTMASK0900=2`, `AT+LOG=5`, `AT+RELAYMODE=1`; `+QACC:high/low` → `Array<4>` com histerese (`>0.75` / `<0.15`) | `AT+GPIOVALUE=0,1` / `=0,0` |

---

## 12. `objects/server/` — Wi-Fi, HTTP, OTA, economia de energia

### 12.1 `objects/server/index.h` — `class EspServer`

- `setup()` — `enabled = settings["wifi"]`, `URL`, `wifi_ssid/passwd`, `server_ssid = getSSID()`
  (`"SIGHIR - " + 7 primeiros chars do esp_id`, ou `"SIGHIR ADMIN"` se id = `admin_sighir`). Se
  habilitado: `esp_wifi_set_ps(WIFI_PS_NONE)`, potência 19,5 dBm.
- `start()` — AP com IP fixo **192.168.1.2**, SSID `server_ssid`, senha **`12345678`**, canal
  `channel`; `WiFi.begin(ssid, passwd, channel)` (STA); `routes.setup()`; `network.begin()`.
- `enable()` / `disable()` — ligam/desligam AP+STA.
- `set(state)` — grava `wifi` e liga/desliga.
- `handle()` — `sleeper.handle()`; a cada 100 ms, se habilitado e não dormindo:
  `network.handleClient()` + `updater.handleCheck()`.
- `connect(show, tryChannel)` — tela "Conectando à rede" com SSID/senha, 5 s de `sensors.warm`,
  "Conectado"/"Não conectado"; se conectou → `updater.handleCheck(true)`; senão e `tryChannel` →
  `changeChannel()`.
- `changeChannel()` — cicla canais `1 → 6 → 3 → 11 → 2 → 1` (AP e STA compartilham o rádio, então
  o canal do AP tem de bater com o do roteador) e tenta conectar de novo (sem recursão de canal).
- `wait(ms)` — loop de `handle()`.
- `send(text)` — resposta HTTP 200 `text/plain` com CORS `*`.
- `post(route, json, timeout)` / `get(route, timeout)` — `HTTPClient` contra `URL + route`;
  devolvem o corpo ou `"-1"`.

### 12.2 `objects/server/routes/index.h` — `class ServerRoutes`

| Rota | Método | Ação |
|---|---|---|
| `/CHECK` | GET | JSON `{temperature, humidity, analog, filtered, pressure}` |
| `/TEST` | GET | `OK` e `test.start()` |
| `/NPTEST` | GET | teste com pressão em debug (sem soprar) |
| `/ALCTEST` | GET | teste com `alcohol_debug` (resultado positivo forçado) |
| `/WIFI` | GET | `$1!`/`$0!` conectado à STA |
| `/SENSOR` | GET | ID do sensor (relê EEPROM) |
| `/RESET` | GET | reinicia |
| `/ERASE_SETTINGS` | GET | reset de fábrica |
| `/STATUS` | GET | `OK` |
| `/INFO` | GET | JSON `{company, vehicle_plate, esp_id, sensor_id, event}` — `event` = 10 linhas de log **consumidas** (`Logs::get` apaga) |
| `/CLEAN` | GET | apaga logs |
| `/ALL_CONFIGS` | GET | settings inteiro |
| `/SEND_ALC` | GET | vetor de amostras do último teste |
| `/update` | GET | OTA HTTP (`Updater::start`) |
| `/WIFI_SETUP` | POST `$ssid:senha!` | grava e reconecta |
| `/CONFIG` | POST texto | **injeta o corpo como se fosse um comando serial** (`serial.command.set`, `handleProtocol`, `handleOperation`) e devolve `telemetry.response` |
| `/SET_ALL_CONFIGS` | POST JSON | mescla todas as chaves (como string) em settings |

### 12.3 `objects/server/sleeper/index.h` — `class ServerSleeper`

Economia de energia quando o Wi-Fi está habilitado: após **5 min com display desligado**,
`start()` desliga o Wi-Fi e configura `esp_pm` para **80 MHz máx / 10 MHz mín com light-sleep**;
quando o display liga, `end()` volta a 160 MHz e religa o servidor. Enquanto dormindo, `handle()`
insere `delay(10)` (dá chance ao light-sleep). `active` é capturado **uma vez** (static) na primeira
chamada. O menu mostra a frequência atual em "Tempo ligado".

### 12.4 `objects/server/updater/index.h` — `class Updater`

- `handleCheck(force)` — no máximo a cada 30 min (ver observações), se conectado:
  `GET api/v2/devices/check-update/?id=<esp_id>&sensor_id=<sid>&firmware=<ver>`. Se a resposta
  contém `true` → `needed=true` e, se em boot ou no menu, `requestUpdate()` (pergunta sim/não).
- `start()` — conecta se preciso, `config()`, `download()`, `handleCheck(true)`.
- **`config()`** — "configuração remota": `POST checkSettings/ {"esp_id":...}`; valida
  `status == "success"` e `data` (que é um JSON como string); mescla em settings; `$ETEV07!`.
  Retorna false com tela de erro em cada caso de falha ("sem resposta", JSON inválido, chaves
  inválidas, `doesnt`/`None` = nada a configurar).
- **`download()`** — OTA HTTP: `POST update/ {"esp_id":...}`, `Update.begin(contentLength)`,
  `writeStream` com callback de progresso (redesenha a cada 5 %), `Update.end()` → `$ETEV10!` e
  `ESP.restart()`.
- **`local()`** — OTA pela serial (comando `updt`): envia `_STARTING_UPDATE_`, `Update.begin
  (UPDATE_SIZE_UNKNOWN)`, espera até 35 s pelo 1º byte, e então lê chunks `$<base64>!` de até
  ~2,8 KB, decodifica, `Update.write`, responde `written` por chunk. Termina quando ficar 10 s sem
  bytes (`finished()`), `Update.end(true)` e reinicia.

---

## 13. `objects/display/` — LCD, toque, som, interface e menu

### 13.1 `objects/display/index.h` — `class Display`

`LGFX lcd` (autodetect WT32-SC01, rotação 2 = retrato invertido, 320×480), `width/height`, `on`,
`timeOff`.

- `setup()` — init, brilho 255 temporário, dimensões, `interface.setup()`, `brightness.setup()`,
  `touch.click()`, `sound.setup()`, `turnON()`.
- `handle()` — `menu.handle()`; **auto-off após 60 s sem toque** (exceto durante tempo de manobra).
- `turnON()` — restaura brilho, reseta toque, `on=true`.
- `turnOFF()` — `timeOff=agora`, reseta menu/som/toque, `exit()` (animação de "spinner" de 12
  raios com "Desligando display"), `clear()` (som off, tela preta, brilho 0), `on=false`.

### 13.2 `brightness/index.h` — `class Brightness`

Faixa `25..170`. `set(v)` clampa, calcula `percent`, **salva em NVS** e aplica. `increase(±10 %)`.
`update(val)` aplica sem salvar (usado para 120 no teste, 50 no sopro, 40 em falha de energia).
`reset()` volta ao salvo. `toString()` = "N0%".

### 13.3 `sound/index.h` — `class Sound`

Buzzer no GPIO 25 via LEDC (canal 0, 8 bits). Volume `25..255` salvo em NVS.

- `set(freq, wait)` — `ledcWriteTone`; se `wait>0`, `await(wait)` e silencia (bloqueante).
- `handleBeep(interval=150, sound=BLOW)` — bipe intermitente **não bloqueante** (toggle por
  intervalo) — usado durante o sopro, no alerta de motorista e no teste aleatório.
- `okBeep` (2800 Hz 0,5 s), `goodBeep` (2600 Hz 1,5 s), `twoBeep`, `badBeep` (500 Hz 1,5 s),
  `disable`, `reset` (recarrega volume), `increase`.

### 13.4 `touch/index.h` — `class Touch`

- `click()` — a cada 50 ms lê `getTouch`; **debounce espacial-temporal**: ignora se a < 50 px do
  último clique e < 700 ms. Atualiza `x,y,lastClick`.
- `centerClick()` — detector "de pressão contínua": filtra a presença de toque com EMA
  (`α = 0.3935`, equivale a e^−0.5); dispara true quando o filtrado passa de 0,90 (≈ 5 amostras
  seguidas) e se rearma abaixo de 0,10. Usado em "toque para adiar/iniciar" (evita toques
  acidentais).
- `areaClick(x,y,w,h)` — o último clique caiu no retângulo? Se sim, `reset()` (consome).
- `screenClick(updateTouch)` — clique na área central 80 %.
- `enableDraw(timeout)` — desenha bolinhas vermelhas onde tocar (easter egg da "família").
- `reset()` — `lastClick=agora; x=y=0`.

### 13.5 `interface/index.h` — `class Interface`

Primitivas de desenho de alto nível (todas ligam o display se estiver desligado):

- `label(text, x, y, w, h, txtColor, bgColor, contorno)` — retângulo com texto centralizado.
- `msg(type, text)` — limpa a tela com a cor do tipo (`MSG_*`) e escreve o texto centralizado
  (verticalmente, respeitando `\n`/`\r\n`, espaçamento 2×).
- `centeredText(text, color, startY=0, lineSpace=2, resetFont=true)` — multi-linha centralizada;
  `startY=0` centraliza verticalmente.
- `printIcon(glyph, scale, color, x, y)` — fonte Remix Icon 64 px (ícones do menu: wifi, engrenagem,
  setas…).
- `alert(title, subtitle, type=RED, await=3000, turnoff=false)` — `msg` + subtítulo a 70 % + espera.

`font/index.h` — `DisplayFont`: `setStyle`, `setBold` (Roboto Bold 10), `setSmall` (Regular 10),
`reset` (Regular 12).

### 13.6 `interface/inputs/index.h` — `class Inputs`

- `bichoices(upper, lower, await, timeout=60 s)` — metade superior amarela / inferior cinza;
  retorna true para superior **ou timeout**.
- `trichoices(t0, t1, t2, timeout=120 s, standard=2)` — três faixas (amarela, cinza, branca);
  retorna 0/1/2; no timeout retorna `standard`.
- `boolean(label, subtitle, timeout=5 min)` — botões "Sim" (azul, 70,200) e "Não" (vermelho,
  180,200); false no timeout.

### 13.7 `interface/loading/index.h` — `class LoadingWindow`

Barra de progresso reutilizável: `start(title, subtitle, timeout, heightPercent)` (se
`heightPercent<100` só ocupa o topo, deixando o resto da tela — usado sobre o aviso INMETRO);
`step(value, increment, render)` — valor explícito, incremento, ou automático por `timeout`;
redesenha no máximo a cada 100 ms; `done()` → true ao chegar a 100; `drawBar`.

### 13.8 `interface/keyboard/index.h` — `class Keyboard`

Teclado virtual de 5 páginas × 4 linhas × 3 colunas (dígitos, a–j, k–t, u–z + símbolos, símbolos),
teclas `<` (backspace), `+` (próxima página), `^` (maiúsculas), `OK`. `draw(title, value, alpha)`
mostra título, um valor fixo (ex.: a senha gerada) e o campo digitado; `get()` bloqueia até `OK` e
retorna a `String` (máx. 30 chars, trim). Layout em pixels fixos (320×480).

### 13.9 `interface/menu/index.h` — `class Menu` (763 linhas)

Menu tocável. `struct Page {label, icon, name, maxPages, startX, startY, width, height}` para
ID / INFO / CONFIG / SAIR (grade 2×2). `currPage/currSubpage/currMaxPages`, `active`.

- `handle()` — só age em `touch.click()`: se tela desligada e clique central → `draw()` (abre o
  menu); se em subpágina → `handleSubmenuTouch()`; senão `handleMenuTouch()`.
- `draw()` — abre o menu: se conectado e `updater.needed` → pergunta update; fundo `BG_COLOR`,
  `drawHeaderBar("MENU")` (temperatura/umidade coloridas por alerta, ícone wifi on/off, bluetooth),
  4 botões, "Último teste: X mg/L", botão do valet (se habilitado), botão verde "Desbloquear
  Veículo" (se contrassenha pendente).
- `handleMenuTouch()` — botão de desbloqueio → `pass.start()`; valet → `valet.start()`; páginas →
  `setSubpage(x, 1)`; SAIR → `turnOFF()`.
- `handleSubmenuTouch()` — setas próximo/anterior (rodapé) ou handlers específicos.
- `setSubpage(page, sub)` — despacha para `drawIdPage1/2`, `drawInfoPage1..4`, `drawConfigPage1..3`.
- `drawSubmenu(page, labels[], values[], n)` — lista de até 5 itens (rótulo em negrito + valor),
  "Página N/M" e setas.

Conteúdo das páginas:

| Página | Itens |
|---|---|
| ID 1 | versão, esp_id, sensor_id, SSID, senha Wi-Fi (toque na parte inferior → configurar Wi-Fi pelo teclado) |
| ID 2 | tempo de viagem (ignição), ID da telemetria (Suntech/Entrack), data de calibração, MAC, tipo de veículo |
| INFO 1 | empresa – modo de telemetria; bloqueado/desbloqueado – dirigindo/desligado; última leitura; tempo ligado + MHz; SSID do AP |
| INFO 2 | tempo de manobra, tempo de câmera, máx. adiamentos, modo aleatório, modo manobrista |
| INFO 3 | tempo médio de viagem, nº de sopros, suavização do sopro (`blowProb`), telemetria ativa/inativa + "Time Check", testes por viagem |
| INFO 4 | aquecedor (ligado por X), calibração (`newZero` (N %)), estabilidade (`mean (rel) – Estável/Estabilizando`) |
| CONFIG 1 | volume (−/+), brilho (−/+), Wi-Fi (toggle), reconectar/trocar canal, atualizar firmware |
| CONFIG 2 | autodiagnóstico, teste de álcool (`test.start(true)`), teste de telemetria (`diagnostic.serial`), configuração remota (`updater.config`), **reinício de emergência** (confirma e `ESP.restart()`) |
| CONFIG 3 | idioma (PT/EN/ES → salva e reinicia) |

`handleFamily()` — easter egg (1500 toques no cabeçalho da página ID → logo "família de
desenvolvimento" + desenho livre); a chamada está comentada.

---

## 14. `objects/diagnostic/` e `objects/logs/`

### 14.1 `objects/diagnostic/index.h` — `class Diagnostic`

Autodiagnóstico acessível pelo menu (CONFIG 2) e por comandos seriais.

- `start()` — `trichoices("Teste de sopro", "Teste de componentes", "Teste de relé")`.
- `blow()` — tara, "Sopre", `getFirstBreath()`, 3 s de sopro contínuo (mesma regra dos 1,8 s);
  sucesso → `check("pressworking")`; falha → `fail("$ERROR!")`.
- `components()` — `pressure()` (HX711 responde em 2,5 s?), `temperature()` (DHT válido em 7 s?),
  `alcohol()` (`failed()`; eventos `$ETEV24!` / `$ETEV20!`).
- `serial()` — envia `$ETKA!` e espera 15 s por qualquer resposta do rastreador; mostra os 15
  primeiros chars recebidos e a porta; sucesso `serialworking`, falha `$ETEV06!`.
- `relay()` — confirma ("vai bloquear a viagem") e faz `block(); unblock(); block();`.
- `fail(evt)` / `check(evt)` — telas vermelha/verde + evento + bipe.

### 14.2 `objects/logs/index.h` — `class Logs`

`Notes("/logs.txt")`. `add(log)` ignora strings < 6 chars, faz append e, se o arquivo passar de
**5000 bytes**, descarta as 5 primeiras linhas. `get()` devolve 10 linhas **e as remove** (fila).
Todo `telemetry.event()` passa por aqui, então o log é o histórico de eventos `$ETEVxx!`.

---

## 15. Fluxo completo de um teste (ponta a ponta)

1. **Ignição liga** — o rastreador informa (`ETAT01`, `STT;...`, `+QACC:high`…) →
   `ignition.set(true)` → `changed=true`.
2. `Telemetry::handleOperation()` → modo `.handle()`: `blocked && !driving` → **`test.start()`**.
3. `Test::start()`: display liga, "Teste Iniciado", checa I²C, avisos de vida do sensor, bipes.
4. `startLoadings()`: 5 s para adiamento de emergência; senão logos.
5. `process()`:
   - `camera.load()` — barra "Aguardando câmera" (default 5 s desde o início).
   - `calibration.load()` — barra "Calibrando Sensor" até `rel < 0.15 %` / 100 % por 12 s (ou
     "Aquecimento necessário" se o teste anterior foi positivo — purga de 2 a 5 min).
   - `calibration.prepare()` — fixa `newZero` = leitura atual.
   - `screens.input()` — "Clique para iniciar" (60 s).
   - `compute()` — "Sopre": até 25 s pelo 1º sopro; 3 s soprando (≥ 1,8 s contínuos) com amostras
     a 500 ms; depois ~23 s de "Analisando" sob o aviso INMETRO até 47 amostras.
   - `model.update()` → random forest → `result`; `analyze(min)` → mg/L; regra final:
     `has_coefs ? (result && mgl > 0.02) : result`.
   - `show()` — mostra mg/L, evento `$ETEV29!` (negativo) ou `$ETEV30xxxx!` (positivo).
6. Pós-processamento em `start()`:
   - **negativo** → `$ETEV16!`, sopros++, `unblock()` (tela verde, comando ao rastreador,
     `$ETBL010000!`, `$ETEV01!`), display desliga. O modo de telemetria, no próximo `handle()`,
     já tinha setado `driving = !blocked`; a viagem começa e `Randomic` passa a monitorar.
   - **positivo** (parado) → `block()` (tela vermelha, `$ETBL020000!`, `$ETEV02!`),
     `pass.start()` (contrassenha / outro teste / desligar display).
   - **positivo ou sem sopro** (já dirigindo, teste aleatório) → `$ETEV35!` + `alertDriver()`
     (bipe até desligar a ignição, então bloqueia).
   - **adiado** → `postpone.start()` (desbloqueia por `postpone_time`, contagem regressiva; toque
     → novo teste; ignição desligada → bloqueia).
   - **falha de calibração** → "Recalibrando" e `start(true)`.
7. **Ignição desliga** → `ManeuverTime::start()`: desbloqueado por `maneuver_time`; ligar de novo
   dentro do prazo não exige teste; expirar → `block()`.

---

## 16. Tabelas de referência

### 16.1 Eventos `$ETEVxx!` emitidos pelo firmware

| Evento | Significado | Origem |
|---|---|---|
| `$ETEV01!` | veículo desbloqueado | `Vehicle::unblock` |
| `$ETEV02!` | veículo bloqueado | `Vehicle::block` |
| `$ETEV05!` | sopro OK, analisando | `Test::compute` |
| `$ETEV06!` | diagnóstico serial falhou | `Diagnostic::serial` |
| `$ETEV07!` | configuração remota aplicada | `Updater::config` |
| `$ETEV08!` | boot da telemetria | `Telemetry::setup` |
| `$ETEV09<sid>!` | ID do sensor no boot | `AlcoholSensor::setup` |
| `$ETEV10!` | OTA concluído | `Updater::download` |
| `$ETEV11!` | não soprou (1º sopro) | `Test::compute` |
| `$ETEV12!` | teste aleatório iniciado | `Randomic::start` |
| `$ETEV13NNNN!` | sensor próximo do fim (N sopros) | `Blows` |
| `$ETEV14NNNN!` | sensor expirado | `Blows::danger` |
| `$ETEV15!` | teste adiado | `Postpone::start` |
| `$ETEV16!` | teste normal concluído | `Test::start` |
| `$ETEV17!` | tempo de manobra iniciado / resposta a `ETKA` | `ManeuverTime`, `Protocol` |
| `$ETEV18!` | tempo de manobra esgotado | `ManeuverTime::end` |
| `$ETEV20!` | sensor de álcool OK (diagnóstico) | `Diagnostic::alcohol` |
| `$ETEV22!` / `!ETEV23$` | valet ligado / desligado | `Valet::start` |
| `$ETEV24!` | falha no sensor/EEPROM | `AlcoholSensor::check`, `Diagnostic` |
| `$ETEV25!` | teste aleatório concluído | `Test::start` |
| `$ETEV26!` | liberado por contrassenha | `Pass::liberate` |
| `$ETEV27!` | temperatura alta / sensor DHT defeituoso | `sensorDHT` |
| `$ETEV28!` | temperatura grave | `sensorDHT` |
| `$ETEV29!` | resultado negativo | `Test::show` |
| `$ETEV30dddd!` | resultado positivo (mg/L sem ponto) | `Test::show` |
| `$ETEV32!` | valet desbloqueou | `Valet::unblock` |
| `$ETEV33!` | teste aleatório sem sopro | `Test::compute` |
| `$ETEV34!` | teste aleatório adiado | `Postpone::start` |
| `$ETEV35!` | motorista não autorizado dirigindo | `Test::start` |
| `$ETEV36<sid>!` | sensor trocado | `Storage::setup` |
| `$ETEV40<n>!` | contrassenha digitada | `Pass` |
| `$ETEV41!` | umidade alta | `sensorDHT` |
| `$ETBL010000!` / `$ETBL020000!` | comando desbloquear / bloquear ao rastreador | `Vehicle` |
| `$ETKA!` | keep-alive (diagnóstico) | `Diagnostic::serial` |
| `$ETKAACK!`, `$ETBLACK!`, `$ETATACK!`, `$ETEVACK!` | ACKs | `Protocol`, modos |
| `$NOBLOW!`, `$ERROR!`, `ON`, `OFF`, `success`, `error`, `written`, `_STARTING_UPDATE_` | diversos | — |

(O app desktop, em `desktop/src-tauri/src/lib.rs::strip_noise`, filtra exatamente esses padrões
para separar "ruído de telemetria" das respostas a comandos.)

### 16.2 Sons

| Nome | Hz | Duração | Uso |
|---|---|---|---|
| `BUZZER_GOOD_SOUND` | 2800 | 100 ms ×3 no boot; `okBeep` 0,5 s | boot, reinício |
| `BUZZER_SIGNAL` | 2600 | `goodBeep` 1,5 s; 200 ms ×2 | desbloqueio, início do teste |
| `BUZZER_BLOW` | 2600 | 200 ms ×2; intermitente 75–150 ms | "Sopre", durante o sopro |
| `BUZZER_BAD_SOUND` | 500 | `badBeep` 1,5 s; 2–6 s em alertas | bloqueio, erros |
| `BUZZER_RND_SOUND` | 800 | 500/1200 ms; intermitente 2 s | teste aleatório |

### 16.3 Timings importantes

| O quê | Valor |
|---|---|
| Amostragem do filtro de álcool / pressão / blower | 100 ms |
| Amostragem da calibração (`Array<20>`) | 500 ms → janela de 10 s |
| Amostragem do modelo de álcool (`Array<47>`) | 500 ms → ~23 s |
| Sopro mínimo contínuo | 1,8 s (janela de 3 s) |
| Espera pelo 1º sopro | 25 s |
| Timeout da calibração | 7 min |
| Estabilização a 100 % | 12 s |
| Histerese de descalibração | 20 s |
| Purga após positivo | 2–5 min conforme `last_analog` |
| Display auto-off | 60 s sem toque |
| Sleeper (downclock) | 5 min com display off |
| Check de update | ~30 min |
| Keep-alive MIX / Suntech / Entrack | 5 min / 2 s / 2 s |
| Telemetria "ativa" | recebeu algo há < 15 s |
| Heater sempre ON | 10 min pós-boot, display on, dirigindo, 10 min pós-ignição |
| Reinício preventivo | 3 dias ligado + 3 h parado |

---

## 17. Observações, dívidas técnicas e bugs latentes

Coisas notadas durante a leitura (não alteradas — apenas registradas):

1. **`Vehicle::block()` e `unblock()` escrevem `LOW` no relé (GPIO 2) nos dois casos.** O bloqueio
   efetivo depende do rastreador. Se o relé físico for usado, um dos dois deveria ser `HIGH`.
2. **`Protocol::check`**: os blocos `ETBL01`/`ETBL02` após `ETKA` são inalcançáveis (duplicados).
3. **`Updater::handleCheck`**: `if(!force && timer.ready()) return;` está invertido em relação ao
   padrão do resto do código (`!timer.ready()`); funciona por acidente porque o segundo `if` de 30
   min domina. E `static bool first_time = false` torna o `if(first_time) force = true` morto.
4. **`Calibration::stateUpdate`** mistura `||` e `&&` sem parênteses:
   `mean > 20000 || (newZero > MIN && pct == 100 && rel < 0.20)` — parece intencional, mas vale
   explicitar.
5. **`Calibration::load`**: `stableTime` só é (re)iniciado quando `percentage` **sobe** para 100;
   se cair e voltar, o cronômetro antigo é reaproveitado e os 12 s podem ser "pulados".
6. **`Array::getStd`** divide por `length−1` mesmo com o buffer parcialmente cheio (as posições
   vazias valem `junk`), e **`getMin` retorna `int`** enquanto `getMax` retorna `float`.
7. **`Travels::increment()` nunca é chamado** — a média de viagens só muda se já houver dados no
   NVS `"random"`.
8. **`Test::MIN_TIME`** é calculado e nunca usado. `Driver`, `AUTO_TEL`, `TEST_STARTED`,
   `EEPROM_FAIL/SENSOR_*`, `ButterworthFilter`, `Postpone::update` (variáveis de botão) são código
   morto.
9. **`ServerSleeper::handle`** captura `settings["wifi"]` em `static const` na primeira chamada:
   ligar o Wi-Fi pelo menu depois não ativa o sleeper (e vice-versa) até reiniciar.
10. **Filtros com estado `static` dentro de funções** (`AlcoholSensor::smooth`, `Pressure::get`,
    `Touch::centerClick`, `Sound::handleBeep`) — há uma única instância global de cada; funciona
    porque só existe um sensor de cada tipo.
11. **Senhas fixas no código**: AP `12345678`, bypass da contrassenha `5`, IDs de sensor de debug.
12. **`Company::configParams` e `Settings::reset` discordam** (telemetria 0 vs 2, manobra 1 vs 5
    min, `rand_*` invertidos). O provisionamento de fábrica (`Company`) prevalece.
13. **`Valet::start` emite `!ETEV23$`** (delimitadores invertidos) — o desktop já trata, mas a
    telemetria do rastreador pode não reconhecer.
14. **Loops bloqueantes longos** (`calibration.load` até 7 min, `Pass::start` sem timeout no
    teclado, `alertDriver` até a ignição desligar) mantêm o servidor HTTP vivo via `await`, mas
    **não processam a telemetria** em vários deles — comandos do rastreador chegados nesse período
    ficam no buffer da UART (até estourar) e só são lidos depois.
15. `Text<20> id` comporta exatamente os 19 chars de `generateID()`; um `esp_id` maior definido
    pelo servidor seria truncado silenciosamente.
16. `HEAT_MIN_TIME` só é usado no `MIN_TIME` morto; `ANALOG_INVALID` (1000) é o piso real de
    leitura válida.
17. `lr_old.h` e `blower (bkp)/index.h` compartilham include guards com os arquivos atuais e
    **não podem** ser incluídos junto — são apenas histórico.
