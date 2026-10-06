# Serial: ruído, comandos, armadilhas do parser e desempenho

> Movido do manual antigo (GEMINI.md §8, §11 e §12), sem cortes. Numeração original mantida.

## 8. Tratamento de Ruído Serial

- **Sempre limpe o buffer** (`device.clear()`) antes de cada consulta. A CLI já faz.
- **Valide o formato** da resposta (ex: `$firmware!` deve casar `vX.Y.Z`; `esp_id` deve conter `MIC`).
- **Retry com backoff**: lixo assíncrono (`port changed to 1`, `SttReq`, `$ETACK!`, `AT+QACC?`, `CMD;...;04;0x`) — descarte, limpe e reenvie. A lista completa está em `utils/noise.py` (§8.1).
- **`$ETEVxx!` NUNCA é lixo.** Todo `$ETEVxx!` é resultado ou evento do device e precisa chegar íntegro:
  - `$ETEV17!` é a **segunda linha da resposta do `$ETKA!`** (o device responde `$ETKAACK!` **e** `$ETEV17!` — `protocol/index.h:67-71`), não ruído.
  - `$ETEV20!` é o **resultado OK do `TST_SENS`**; `$ETEV24!` é a falha. Descartar isso = jogar fora o resultado do teste.
- **Nunca** interprete resposta de formato inesperado como dado válido. Lembre: para `$firmware!`, formato inesperado após retries = **firmware antigo** (Seção 5.1).

### 8.1 Filtro de Ruído de Telemetria (`utils/noise.py`)

O `NextSerial` do firmware **troca o uart para a `Serial` (USB) assim que ela recebe dados**
(`../docs/hardware/Main/objects/telemetry/serial/index.h:62-66`). Ou seja: o tráfego de telemetria
(requests periódicos, acks, comandos de bloqueio) passa a sair **na porta que o tester lê**.
Esses comandos são **vitais para o device — não alterar o firmware**; o tester é que precisa ignorá-los.

`utils/noise.py` centraliza a lista e é aplicado em `Device.get()`, `Device.expect()` e `Device.request()`:

| Origem | Lixo emitido na USB |
|---|---|
| Suntech | `SttReq` (2 s), `CMD;<id>;04;01|02` (bloqueio/desbloqueio) |
| MIX / MIX 2.0 | `$ETACK!` (keep-alive 5 min) |
| Entrack | `AT+QACC?` (2 s), `+QACC:high|low`, `AT+GPIOVALUE=x,y`, ATs de setup (`AT+ID?`, `AT+LOG=5`, ...) |
| Debug do firmware | `port changed to N`, `Serial2 Started at RX=.. e TX=..` |

Comportamento: a linha é limpa (`noise.clean`); se sobrar **só lixo**, é descartada e a leitura
continua até vir conteúdo útil ou estourar o timeout — nunca se retorna uma string suja.
O **alvo do `expect()` é preservado** (`keep`), pois há testes que esperam justamente um desses
comandos (ex.: `protocol.json` espera `SttReq` no teste do Suntech).

> Para adicionar um novo ruído: `telemetryNoise` (texto fixo) ou `noisePatterns` (regex) em `utils/noise.py`.
> **Não** inclua eventos `$ETEVxx!` — eles são resultado de teste e precisam chegar íntegros.

---

## 11. Referência Rápida de Comandos do Device

Parser: `../docs/hardware/Main/objects/telemetry/protocol/index.h` (`Protocol::check()`).

| Comando | Descrição | Resposta esperada |
|---------|-----------|-------------------|
| `$ETKA!` | Sincronização (keep-alive) | `$ETKAACK!` **e depois** `$ETEV17!` (duas linhas) |
| `$firmware!` | Versão do firmware | `v6.4.0` — string crua, **sem `$`/`!`** (vazio/estranho = antigo) |
| `$ETRS!` | Reiniciar device | (reinicia, ~6 s até voltar) |
| `$erase!` | Reset **de fábrica** das settings + reinicia | (ver ⚠️ em §11.2 — apaga telemetria/wifi/empresa) |
| `CF:key$value!` | Grava setting (qualquer chave) + salva | `OK` (ou `NONE` se faltar `:`/`$`/`!`) |
| `ID:<key>$` | Lê uma setting **do NVS** | `$<value>!` (ou `ERROR`) |
| `sensor_id` | Lê o ID do cartucho **da EEPROM** (releitura real) | `ETL...` |
| `analog` / `last_analog` | Leitura atual / última leitura do teste | inteiro |
| `coefs` / `cf_coefs$<json>!` | Lê / grava coeficientes de calibração | JSON / `success`\|`error` |
| `__updt__` | Entrar em modo update USB | `_STARTING_UPDATE_` (com underscores) |
| `$ETBL01!` / `$ETBL02!` | Desbloqueia / **bloqueia** o veículo | `$ETBL0x0000!` + `$ETEV01!`/`$ETEV02!` (**sem `$ETKAACK!`** — ver nota) |
| `endTravel` | Encerra viagem: `driving=false` + **`blocked=true`** | `OFF` |
| `$ETAT01!` | (MIX/MIX2) Liga a ignição — **só dispara teste se bloqueado** (§11.3) | `$ETATACK!` |
| `TST_PRESS` / `TST_TEMP` / `TST_SENS` | Diagnóstico de pressão/temp/sensor | `pressworking` / `tempworking` / `$ETEV20!` |

> **Timeout dos `TST_*`**: o diagnóstico dá `await(2500)` antes de responder e o `TST_TEMP` varre
> até 7 s → a resposta pode levar **~10 s**. Use timeout ≥ 15 s (é o que o `protocol.json` faz).

> **`$ETBL01!`/`$ETBL02!` não devolvem `$ETKAACK!`** (verificado no device, firmware v6.4.4): o parser
> faz `response.set("$ETKAACK!")` e logo chama `vehicle.unblock()/block()`, mas todo `telemetry.event()`
> termina com `response.reset()` — o ACK é apagado antes de ser enviado. **Espere pelo `$ETEV01!`
> (desbloqueado) / `$ETEV02!` (bloqueado)**, que é a confirmação real de que o relé foi acionado.

### Mapa de Documentação (consulte ao ter dúvida — NÃO suponha)
| Arquivo | Quando usar |
|---|---|
| **`../docs/firmware_reference.md`** | Digest do firmware (eventos `$ETEVxx`, telemetria, settings, fluxo de teste). **Resposta rápida.** |
| **`../docs/hardware/Main/`** | **Código-fonte real do firmware (ESP32/C++)** = fonte da verdade. Leia quando precisar de exatidão ou o digest não bastar. |
| **`../docs/server_reference.md`** | Schema do servidor Django, API e procedimentos de banco (instalar/editar/deletar). |
| **`../docs/INDEX.md`** | Instalação física (Suntech/MIX/Entrack), calibração, ANATEL. |
| **`../docs/diagnostico.md`** (e `../docs/troubleshooting.md`) | Autodiagnóstico de problemas de campo (bloqueio, requisição de teste, atualização). |
| **`protocol.json`** | Scripts de teste corrigidos = gabarito rápido (semântica verificada na §11.1). |

> Regra: **dúvida simples → digest/instrução**; **dúvida fina ou comportamento exato → leia o source em `../docs/hardware/Main/`** antes de agir.

### 11.1 Semântica dos Testes (`protocol.json` — verificado no firmware)
- **Flags de debug** (via `CF:`): `press$1` = **simula sopro** (pula `getFirstBreath`/blower); `press$0` = **sopro real** exigido. `testalc$1` = **força álcool** (→ `$ETEV30`); `testalc$0` = leitura real (limpo → `$ETEV29!`).
- **Diagnósticos de sensor** (não exigem sopro): `TST_PRESS` → `pressworking`/`$ERROR!` (checa **comunicação** do load-cell HX711, **não** um sopro), `TST_TEMP` → `tempworking`/`ERROR`, `TST_SENS` → `$ETEV20!`/`$ETEV24!`. O teste de sopro **real** (`Diagnostic::blow()`) é **só pela tela touch**, não há comando serial.
- **Eventos do resultado**: `$ETEV05!` = analisando (~20 s); **sem álcool** → `$ETEV29!` → desbloqueia (`$ETEV01!`); **com álcool** → `$ETEV30<mgL>!` → bloqueia (`$ETEV02!`) + contrassenha.
- Telemetria no tester (`utils/variables.py`): `mix`→**5 (MIX 2.0)**, `suntech`→**2**, `entrak`→**6**. As variantes de teste completo cobrem `mix`/`suntech`; em `entrak` os testes completos são **pulados com aviso** (o gatilho serial exigiria um burst de 4×`+QACC:high` que o runner não emite) — `entrak` roda os testes `any` (sopro/temp/sensor) normalmente.

### 11.2 Armadilhas do Parser (leia antes de inventar comando)
- **O matching é por `contains()`, em cadeia, na ordem do arquivo.** Uma string casa pelo *pedaço*:
  `ID:` casa por **`"D:"`**, `CF:` casa por **`"F:"`**, `__updt__` casa por **`"updt"`**, `$erase!` por **`"erase"`**.
  Consequência: **nunca mande texto arbitrário na serial** — uma string que contenha `updt`, `erase`
  ou `ETRS` dispara update/reset de fábrica/reboot sem querer.
- **Durante um teste o device não lê comandos.** `Test::compute()` fica em loop chamando só
  `server.handle()`/sensores — `telemetry.handle()` (o parser) **não roda**. Ele continua *emitindo*
  eventos, mas **não responde a nada** até o teste acabar. Não mande comando no meio do teste: espere
  o `$ETEV29!`/`$ETEV30...!` (e o `$ETEV01!`/`$ETEV02!`).
- **A resposta pode vir GRUDADA num evento.** O `$ETEV17!` (2ª linha da resposta do `$ETKA!` da sync)
  chega ~100 ms depois do `$ETKAACK!` e cai na leitura seguinte: `ID:telemetry$` retorna
  `"$ETEV17! $6!"`. Quem pega "do primeiro `$` até o primeiro `!`" lê **`ETEV17` como se fosse o valor**.
  Use `core.extractValue()` (pega o **último** token `$...!`, descartando `$ETEVxx!`) ou o comando
  `settings` — nunca faça o parse ingênuo na mão.
- Histórico: o `Device.request()` descartava resposta com < 5 caracteres, o que sumia com settings curtas
  (`$6!`) e devolvia `None`. **Corrigido** — mas a lição fica: **valide o formato, não o tamanho**.
- **`sensor_id` ≠ `ID:sensor_id$`**: `sensor_id` **relê a EEPROM do cartucho** (valor real);
  `ID:sensor_id$` devolve o que está salvo no NVS (pode estar defasado ou `None`). Para cadastro, use `sensor_id`.
- ⚠️ **`$erase!` é reset de fábrica, não "só o esp_id"**: ele reescreve *todos* os defaults
  (`device/settings/index.h:43-71`) → **`telemetry` volta para `2` (Suntech)**, `wifi=false`,
  `vehicle_type=0`, `ssid/passwd` de fábrica. Como o `register` faz erase automático
  quando o `esp_id` não é nativo, **um device MIX/Entrack vira Suntech no processo**: depois do erase,
  **reconfigure a telemetria** (`CF:telemetry$5!` MIX 2.0, `$6!` Entrack, `$0!` MIX legado) e o resto do que foi apagado.
- **Firmware de debug**: o `Main.ino` do source liga `alcohol.debug`/`bypass`. Nesse modo o `analog` é
  fixo **23000** e o `sensor_id` é **falso e hardcoded** (`ETL2608402025435219` ou `ETL3550904305917103`).
  Se um device responder um desses dois IDs, **não cadastre** — é build de debug, não um cartucho real.

### 11.3 Como o Teste Completo Realmente Dispara (a regra que mais me pega)
O gatilho **não é o comando** — é a **transição da ignição**, e só com o veículo **bloqueado**:

```c++
if(ignition.changed && ignition.on){          // modes/{mix,mix2,suntech,entrack}/index.h
    if(vehicle.blocked && !vehicle.driving)
        device->test.start();
    ...
}
```

Daí as três condições, todas obrigatórias:
1. **`blocked == true`** — no boot já é `true`; depois de um teste limpo o device **desbloqueia**, e aí
   um novo `$ETAT01!` **não faz nada**. Re-arme com **`endTravel`** (`forceDriving(false)` → `blocked=true`,
   ignição OFF, responde `OFF`) ou `$ETBL02!`. É exatamente por isso que todo script do `protocol.json`
   **começa e termina com `endTravel`**.
2. **`ignition.changed`** — precisa ser uma *transição* OFF→ON. Mandar `$ETAT01!` com a ignição já ligada
   não dispara nada (`Ignition::set()` só marca `changed` se o valor mudou).
3. **Modo de telemetria correto** (`CF:telemetry$...!`), porque cada modo tem seu gatilho:
   - **MIX (0) / MIX 2.0 (5)**: `$ETAT01!` → `$ETATACK!` + ignição ON. `$ETEV04!` → ignição OFF.
   - **Suntech (2)**: pacote `STT;...` com o campo de chave (`_______1___` liga / `_______0___` desliga).
     Pela USB **1 pacote basta** (`keyUpdate` pula a média quando `port == 1`); pelo rastreador real precisa de ~4.
   - **Entrack (6)**: ignição vem da média das últimas 4 amostras de `+QACC:high`/`low` (>0,75 liga) →
     precisa de um **burst de ~4 `+QACC:high`**, que o runner não emite (por isso o teste é pulado).

> **MIX 2.0 tem timeout**: ignição ligada, desbloqueado e sem dirigir por **70 s** → o device **bloqueia sozinho**.

---

## 12. Notas para Maximizar Performance

- **Comece sempre pela CLI** (`tools/sighir.py`) — é mais rápida, robusta e consistente que reescrever lógica.
- **O device é RÁPIDO; a lentidão costuma ser nossa.** Medido: `$firmware!` responde em **0,10 s** e o
  `$ETKA!` em 0,28 s. Se algo demora, o gargalo é sleep no tester, não o aparelho. Duas exceções
  **legítimas** (são do firmware, não tente "otimizar"): o `sensor_id` leva **~2 s** (lê 170 bytes da EEPROM
  a `await(10)` por byte) e os `TST_*` levam até **~10 s** (`await(2500)` + varredura).
- **Nunca "conserte" latência com sleep fixo.** `Device.clear()` drena até o silêncio (~0,2 s) e
  `Device.connect()` espera o `$ETKAACK!` em vez de dormir 2,5 s — foi o que levou o `status` de **9 s → 3,7 s**.
  ⚠️ `connect(delay=0)` **não sonda** de propósito: é o reconnect do meio do flash, e um `$ETKA!` no meio
  do stream de update corromperia o firmware. **Não mexa nisso.**
- **Não teste o download de firmware isoladamente** (é one-shot). Vá direto ao `flash`.
- **Flash sempre em background com log**; monitore por leitura do log, não por foreground.
- **Confie na classificação de firmware** (`ok`/`below_min`/`old`) para decidir o próximo passo.
- **Em falhas de serial**, `recover` primeiro, depois retente — não conclua "quebrado" sem retry+backoff.
- **Seja conciso** com o usuário; mostre resultados e erros claramente.
