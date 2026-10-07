# Ambiente, arquitetura do código e diagnóstico de campo

> Movido do manual antigo (GEMINI.md §2.1, §4, §10 e §14). Numeração original mantida.

### 2.1 Quando NÃO conecta (nenhuma porta serial / `status` falha)

Não conclua "aparelho quebrado" e não fique tentando sozinho. **Pergunte ao usuário, nesta forma:**

> "Não encontrei nenhuma porta serial. O etilômetro está realmente conectado no USB?
> Quer que eu instale o driver e tente de novo?"

Conforme a resposta:
1. **"Não estava conectado"** → peça para conectar e rode `python tools/sighir.py status` de novo.
2. **"Sim, quer instalar o driver"** → instale e **repita o status na sequência** (o próprio fluxo, sem
   pedir confirmação de novo):
   - **Windows**: `assets\files\driver.exe` (instalador do conversor USB-serial que já vem no repo).
     É o mesmo binário que o menu interativo chama em `objects/Tester/index.py:36`.
   - **Linux**: **não há driver para instalar** — `cp210x`/`ch341` já são módulos do kernel. Aqui o
     problema costuma ser **permissão**: confira `ls -l /dev/ttyUSB*` e se o usuário está no grupo
     `dialout` (`groups`); se não estiver, oriente `sudo usermod -aG dialout $USER` + relogin.
     Cheque também `dmesg | tail` para ver se o ESP32 sequer enumerou.
3. **Depois do driver, ainda nada** → cabo/porta USB (teste outro cabo — há cabo só de carga, sem
   dados), depois `python tools/sighir.py recover`. Só então trate como falha de hardware.

---

## 4. Cross-Platform (Linux e Windows)

- **Portas**: scan dinâmico via `serial.tools.list_ports`. Linux = `/dev/ttyUSBx`, Windows = `COMx`. Nunca hardcode.
- **Caminhos**: sempre `os.path`/`pathlib`. Nunca separadores hardcoded.
- **Dependências**: `requirements.txt`. Obrigatórias: `pyserial`, `requests`, `prompt_toolkit` (+ `pypdf` para ler PDFs da base `../docs`).
- **Instalação**: `tools/boot.py` (chamado pelos `.exe`, pelo `start.sh` e pelos hooks de sessão) cria o `.venv` e instala tudo; sem venv possível (Linux sem `python3-venv`), cai no Python do sistema com `--break-system-packages` (PEP 668). O `tools/preflight.py` (usado pelo `sighir.py init`) é a checagem rápida, com cache de 24 h. As CLIs se re-executam no `.venv` sozinhas (`tools/_venv.py`).
- **Baud rate**: `115200`.

---

## 10. Arquitetura (referência)

```
Tester/
├── main.py                  # menu interativo (loop principal)
├── requirements.txt         # dependências (fonte p/ humanos)
├── protocol.json            # scripts de teste (blow, temp, sensor, alcohol)
├── AGENTS.md / CLAUDE.md    # manual do agente (Claude importa o AGENTS.md)
├── procedimentos/           # detalhes: firmware, cadastro, serial, este arquivo
├── Tester_Claude.exe / Tester_Gemini.exe / start.sh   # lançadores (Windows / Linux)
├── .claude/settings.json    # Claude: Sonnet 5, esforço alto, bypass, hook de sessão
├── .agents/hooks.json       # AGY: hook de sessão
├── tools/                   # CLI + camada robusta (USAR PRIMEIRO)
│   ├── sighir.py            # CLI: init/status/firmware/settings/telemetry/erase/recover/register/test/flash
│   ├── core.py              # ops robustas (retry/backoff, classificação de firmware)
│   ├── preflight.py         # checagem rápida de dependências
│   ├── boot.py + ai.json    # bootstrap cross-platform (venv, deps, agente, base docs)
│   ├── _venv.py             # re-executa as CLIs no .venv
│   └── launcher/            # fonte e build dos .exe (launcher.cs, start.ps1, build.ps1, build.sh)
├── objects/
│   ├── Device/index.py      # serial: connect/send/get/expect/scan/clear
│   ├── Server/index.py      # cadastro + download de firmware
│   ├── Updater/index.py     # flash OTA via serial
│   ├── Tester/index.py      # menu (SighirTester) + protocol.py (testes)
│   └── Serial/index.py      # terminal serial interativo
└── utils/                   # api.py, variables.py, classes.py, functions.py, noise.py (filtro de ruído — §8.1)
```

- **API**: base `https://sighir.com:8000/api/v2`, JWT. Endpoints: `/devices` (aparelho **e** instalação: `plate`), `/telemetries` (módulo + chip; era `/suntechs`), `/companies`, `/etilometers` (leitura das instalações), `/update`, `/token/`.
- **Instância global**: `device = Device(rate=115200)`.

---

## 14. Manuais e Troubleshooting

Resumo consultável dos manuais em **`../docs/INDEX.md`** (mapa: qual documento para qual pergunta; instalação Suntech/MIX/Entrack, calibração, protocolo, portal). Os PDFs originais ficam em `../docs/Notion/`. Autodiagnóstico de problemas em **`../docs/diagnostico.md`** (e `../docs/troubleshooting.md`).

**O que fazer quando o usuário pedir ajuda com um problema:**
1. Consulte `../docs/diagnostico.md` para casar o sintoma (ex.: S1 "Não pede teste", S2 "não libera", S3 "não bloqueia").
2. Forneça um **autodiagnóstico guiado**, perguntando o que ele observa na tela do etilômetro e conduzindo a resolução passo a passo.
3. Para instalação física/calibração, use o `../docs/INDEX.md`; abra o PDF correspondente (via `pdftotext` ou leitura direta) só para detalhes finos/figuras.
