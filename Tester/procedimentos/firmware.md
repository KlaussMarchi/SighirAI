# Firmware: regras de versão e atualização

> Movido do manual antigo (GEMINI.md §5 e §7), sem cortes. Numeração original mantida.

## 5. Regras de Firmware

> Versão mínima para operar plenamente: **6.4.0**.

### 5.1 Classificação (via `status` / `firmware`)
- **`ok`** — versão `>= 6.4.0`. Pronto para tudo.
- **`below_min`** — versão `vX.Y.Z < 6.4.0`. Bloqueie cadastro/telemetria; ofereça atualização.
- **`old`** — **`$firmware!` não respondeu, respondeu vazio ou em formato estranho/sem sentido**. Isso significa **firmware muito antigo** que nem suporta o comando. **Peça atualização ao usuário** (fluxo de versão antiga / WiFi, `procedimentos/firmware.md` §7.2).

> A CLI já distingue ruído serial (retry automático) de "firmware antigo" (após
> N tentativas limpas sem `vX.Y.Z` → status `old`). Confie nessa classificação.

### 5.2 Operações que exigem firmware `>= 6.4.0`
| Operação | Motivo |
|----------|--------|
| Cadastro (`register`) | Registro exige firmware compatível com o servidor |
| Configuração de telemetria | Parâmetros podem não ser reconhecidos em versões antigas |

Diagnóstico básico (status, teste serial, leitura bruta) é permitido em qualquer
versão — mas sempre informe a versão detectada.

---

## 7. Procedimento de Atualização de Firmware

### 7.1 Atualização via USB / Serial (OTA) — método padrão

```
python tools/sighir.py flash
```

O `flash` faz: **re-armar `need_update`** → **baixar firmware** → **flashar** → **reiniciar/verificar**.
Se `need_update` estiver `false`, **a própria CLI liga** (`PATCH`) antes de baixar — não faça isso na mão.

> **A versão pode não mudar, e isso não é falha.** O `/update` serve o binário que o servidor tem; se o
> device já está nele, o flash roda inteiro (~4 min, 933 chunks) e termina na mesma versão. **Confirme pelo
> device** (`sighir.py firmware`), nunca pelo campo `software_version` do servidor — ele só é atualizado
> pelo `check-update` via WiFi e **fica defasado** (visto: device `v6.4.4`, servidor `6.4.3`). Para acertar:
> `PATCH /devices/<esp_id>` `{"software_version": "<versão real>"}`.

> **⚠️ `/update` é one-shot**: ao servir o firmware, o servidor zera `need_update`
> e a próxima chamada volta **204 No Content**. Por isso o `flash` **re-arma**
> (`PATCH /devices/{id}` `{need_update:true}`) antes de baixar. **Nunca** faça um
> "download de teste" separado antes de flashar — isso consome o disparo.

> **⏱️ O flash é LONGO (~4 min, ~933 chunks de 2 KB).** Rode em **background com log**
> e monitore — não rode em foreground (estoura timeouts de ferramenta de IA).
> Acompanhe o progresso lendo `flash.log` (linhas de `%` e `completed in ... seg`).
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
4. Reconecte via USB e rode `python tools/sighir.py erase` (regenera o `esp_id` nativo, removendo o `admin_sighir`) e depois `status` para confirmar a nova versão (deve ficar `>= 6.4.0`).
