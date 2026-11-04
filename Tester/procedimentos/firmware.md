# Firmware: regras de versão e atualização

> Movido do manual antigo (GEMINI.md §5 e §7), sem cortes. Numeração original mantida.

## 5. Regras de Firmware

> Versão mínima do Tester: **v6.5.3** (`tools/core.py` `MIN_FIRMWARE`, desde 29/10/2026). Fonte do firmware:
> `Etilometro/hardware/Main` (cópia em `../docs/hardware/Main/`).

### 5.1 Classificação (via `status` / `firmware`)
- **`ok`** — versão `>= 6.5.3`. Pronto para tudo.
- **`below_min`** — versão `vX.Y.Z < 6.5.3`. `qualidade` e `register` recusam (código 2); atualize com `flash`.
- **`old`** — **`$firmware!` não respondeu, respondeu vazio ou em formato estranho/sem sentido**. Isso significa **firmware muito antigo** que nem suporta o comando. **Peça atualização ao usuário** (fluxo de versão antiga / WiFi, `procedimentos/firmware.md` §7.2).

> A CLI já distingue ruído serial (retry automático) de "firmware antigo" (após
> N tentativas limpas sem `vX.Y.Z` → status `old`). Confie nessa classificação.

### 5.2 Operações que exigem firmware `>= 6.5.3`
| Operação | Motivo |
|----------|--------|
| Cadastro (`register`) | critério do Tester: aparelho entregue sempre na versão atual |
| Testes de qualidade (`qualidade`) | usam o `/get-data` e os diagnósticos da v6.5.x |
| Configuração de telemetria | Parâmetros podem não ser reconhecidos em versões antigas |
| `qualidade autodiagnostico` e `qualidade sopro` (**v6.5.4**, `core.DIAG_FIRMWARE`) | o protocolo de sopro na tela (`TST_BLOW`) e as linhas JSON do autodiagnóstico só existem a partir dela; sem eles o relatório fica incompleto. Se o `flash` disser "já atualizado" na v6.5.3, a v6.5.4 ainda não foi publicada |

Diagnóstico básico (status, teste serial, leitura bruta) é permitido em qualquer
versão — mas sempre informe a versão detectada.

---

## 7. Procedimento de Atualização de Firmware

### 7.1 Atualização via USB / Serial (OTA) — método padrão

```
python tools/sighir.py flash
```

O `flash` faz: **escolher a build** → **baixar** → **conferir a versão da build** → **flashar** → **reiniciar/verificar**.

| Aparelho | Build | Como baixa |
|---|---|---|
| cadastrado | da empresa dele (`media/builds/<empresa>/Main.ino.bin`: logo, nome e parâmetros da empresa) | **re-arma `need_update`** (`PATCH`) e `/update` com o `esp_id` — não faça isso na mão |
| novo (não está no servidor) | genérica da Sighir | `/update` com `admin_sighir`: o servidor não procura o aparelho nem mexe em `need_update` (o `/update` com o `esp_id` de quem não está cadastrado dá erro 500) |

- A versão da build sai do próprio binário (string `vX.Y.Z\0`; a do ESP-IDF, `v5.x.x`, é descartada por ser menor).
  Build abaixo de v6.5.3 → **não grava** (código 2; `--forcar` grava assim mesmo). Mesma versão e mesma empresa
  (`settings company` do aparelho) → **não grava** (`já atualizado`).
- Na primeira partida com a build de outra empresa, o firmware grava os parâmetros dela (telemetria, câmera,
  adiamentos…) e reinicia sozinho (`device/company/index.h`): confira a telemetria depois.
- Protocolo (`objects/Updater/index.py`): `__updt__<tamanho>,<md5>,921600` → firmware novo (a partir de 04/11/2026)
  responde `_STARTING_UPDATE_921600_` e a sessão vai a **921600 com blocos de 4096** (~1 min de gravação; medido na
  bancada pelo cabo DB9–USB: 549 blocos, 0 reenvio, 57 s); firmware antigo responde só `_STARTING_UPDATE_` e a sessão
  segue como antes, **115200 com blocos de 2048** (~5 min). Blocos `$<base64>=#<offset>:<crc32>!`, respondidos com
  `written#<gravado>` (o antigo: `written`) ou `resend`; no fim `_UPDATE_OK_` (reinicia na versão nova) ou
  `_UPDATE_FAIL_` (segue na versão anterior; o `flash` sai com 1). Firmware de antes da v6.5 para de decodificar no `=` e
  só confirma reiniciando. O Tester antigo (`__updt__<tamanho>` só) continua gravando o firmware novo em 115200.
- **Robustez da sessão rápida:** o primeiro bloco confirma a velocidade; sem o `written` em 2,5 s, os dois lados voltam
  sozinhos para **115200 na mesma sessão** (o aparelho espera 3 s). Fora da sessão a serial é **sempre 115200**: em toda
  saída (sucesso, falha, 10 s sem bloco válido, Tester fechado no meio) o aparelho volta a ela. Na velocidade nova o
  Tester **nunca reenvia por silêncio** (o aparelho pode já estar em 115200 e o bloco viraria lixo nos comandos): só
  reenvia o que o aparelho pediu (`resend`); silêncio encerra a sessão e a segunda recomeça em 115200. MD5 da imagem
  inteira conferido pelo aparelho antes de ativar (`Update.setMD5`); sessão que cai no meio não ativa nada.
- Verificação pós-flash: espera o aparelho reiniciar sozinho (~50 s: 20 s são o boot procurando o módulo Suntech) e
  confere que ficou **na versão da build gravada**; só se ele não voltar usa `$ETRS!` e o reset pelo RTS.
- `flash --arquivo <.bin>`: grava uma build local (ex.: a do `Etilometro/hardware/Config/index.py compile`) sem
  re-armar nem baixar do servidor. **Confira a empresa da build** (`device/company/index.h`): a build de outra empresa
  troca logo e parâmetros do aparelho na primeira partida.
- Cabo CH340 no Linux: com a porta aberta e **sem leitura**, ele repete o último pacote recebido e embaralha a resposta
  seguinte (medido: 1,1 MB em 10 s). O updater nunca dorme com a porta parada: lê e descarta.

> **A versão pode não mudar, e isso não é falha.** O `/update` serve o binário que o servidor tem; se o
> device já está nele com a mesma empresa, o `flash` nem grava (`já atualizado`); com `--forcar` (ou só a empresa
> diferente) grava inteiro (~2 min no firmware novo, ~6 no antigo) e pode terminar na mesma versão. **Confirme pelo
> device** (`sighir.py firmware`), nunca pelo campo `software_version` do servidor — ele só é atualizado
> pelo `check-update` via WiFi e **fica defasado** (visto: device `v6.4.4`, servidor `6.4.3`). Para acertar:
> `PATCH /devices/<esp_id>` `{"software_version": "<versão real>"}`.

> **⚠️ `/update` é one-shot**: ao servir o firmware, o servidor zera `need_update`
> e a próxima chamada volta **204 No Content**. Por isso o `flash` **re-arma**
> (`PATCH /devices/{id}` `{need_update:true}`) antes de baixar. **Nunca** faça um
> "download de teste" separado antes de flashar — isso consome o disparo.

> **⏱️ O flash leva ~2 min no firmware novo (549 blocos de 4 KB a 921600 + ~50 s de boot) e ~6 min no antigo
> (~1090 blocos de 2 KB a 115200).** Rode em **background com log**
> e monitore — não rode em foreground (estoura timeouts de ferramenta de IA).
> Acompanhe o progresso lendo `flash.log` (linhas de `%` e `completed in ... seg`).
>
> **📊 Progresso para o usuário a cada 20 s (obrigatório, Claude ou Gemini):** o `flash` grava a linha
> `PROGRESSO DO FLASH: 37% (gravando, 1 min 40 s)` no log e o estado em `.sighir/flash.json` a cada 20 s.
> Enquanto ele roda, repita `python tools/sighir.py progresso` (espera até 20 s por uma atualização e
> imprime `flash gravando: 37% (1 min 40 s)`) e **mostre cada resultado ao usuário** até sair
> `flash concluído` (ou `erro`). Código 2 = "SEM ATUALIZAÇÃO há mais de 1 min" → confira o `flash.log`, o
> cabo e o `recover`. No Claude: rode o `flash` com `run_in_background` e chame o `progresso` em seguida,
> uma vez por resposta curta, até concluir. Estados: preparando → sincronizando → gravando → verificando → concluído.
>
> - **Linux/macOS:**
>   ```
>   nohup python tools/sighir.py flash > flash.log 2>&1 & disown
>   ```
> - **Windows (PowerShell):**
>   ```
>   Start-Process -NoNewWindow python "tools/sighir.py flash" -RedirectStandardOutput flash.log -RedirectStandardError flash.err
>   ```
> - **Windows (cmd):**
>   ```
>   start /b python tools\sighir.py flash > flash.log 2>&1
>   ```

> **🔌 Hiccup de USB (Errno 5) durante o flash**: o device pode re-enumerar e a
> porta sumir por instantes. **Não brica** (OTA grava em partição separada; só troca
> ao concluir). A camada serial já tenta reconectar; se o processo morrer, rode
> `python tools/sighir.py recover` e tente o `flash` de novo.

### 7.2 Atualização via WiFi (fallback / firmware antigo)

Use quando o USB falhar ou o firmware for tão antigo que está como `old`:

1. Configure o device via serial:
   ```
   CF:ssid$Sighir!
   CF:passwd$Sighir2024!
   CF:esp_id$admin_sighir!
   $ETRS!
   ```
2. Instrua o usuário a conectar o etilômetro na rede WiFi "Sighir" e atualizar pelo painel WiFi do device.
3. Aguarde confirmação do usuário.
4. Reconecte via USB e rode `python tools/sighir.py erase` (regenera o `esp_id` nativo, removendo o `admin_sighir`) e depois `status` para confirmar a nova versão (deve ficar `>= 6.5.3`).
