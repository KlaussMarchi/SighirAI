# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Escopo:** só para sessões abertas na **raiz** (manutenção do repositório). Se a sessão foi aberta
dentro de `Tester/`, `Server/` ou `Helper/`, siga o `AGENTS.md` daquela pasta e ignore este arquivo.

## Estrutura

Três IAs independentes (`Tester/` bancada USB, `Server/` auditoria da tabela `anomalies`, `Helper/`
suporte técnico) + base comum `docs/`. Visão geral e uso: `README.md`. Mapa da base: `docs/INDEX.md`.

- Cada IA: `AGENTS.md` (manual único, ≤ 12 mil caracteres — limite de regras do Antigravity),
  `CLAUDE.md` (`@AGENTS.md` + notas), `procedimentos/`, `tools/ai.json`, `.claude/settings.json`
  (Sonnet 5, effort high, bypass, hook `SessionStart`), `.agents/hooks.json` (hook `PreInvocation` do AGY),
  `<Pasta>_Claude.exe`/`<Pasta>_Gemini.exe`, `start.sh`.
- **Arquivos idênticos nas três pastas**: `tools/boot.py`, `tools/_venv.py`, `tools/launcher/*`,
  `start.sh`. Mudou um → copie para as outras e recompile os `.exe` (`tools/launcher/build.ps1`).
- **Sem código compartilhado entre IAs** (independência): cada uma tem o seu cliente da API de produção
  (`https://sighir.com:8000/api/v2`, JWT `token/` + `token/refresh/`) — `Tester/utils/api.py`,
  `Server/scanner/api.py`, `Helper/tools/api.py`. Mudança de rota/campo se replica nas três.
- Tester: `tools/sighir.py` (CLI não interativa usada pelos agentes; subcomandos na docstring) →
  `tools/core.py` → `objects/` (`Device`, `Serial`, `Server`, `Updater`) + `protocol.json` (comandos/eventos
  `$ETEV…!` do firmware). `main.py` é o programa interativo antigo da bancada.
- `docs/tools/kb.py`: indexa `docs/` (PDF via pdftotext/pypdf), gera o bloco automático do `INDEX.md` e
  o `casos_notion.md` e o `troubleshooting.md`; catálogo curado em `docs/tools/catalogo.json`.
- **"Sincronizar os documentos"** (ou "sincronize com o notion") → siga `docs/sincronizar.md`, sem perguntar:
  `python docs/tools/sincronizar.py` = `servidor.py` (resumo da frota + snapshot do banco) +
  `notion_sync.py` (árvore inteira da Sighir Enterprise, sem a seção Credenciais, arquiva o que saiu) +
  `kb.py`. Código 10 = sem token do Notion: faça a varredura pelo conector (§3) até a fila esvaziar e
  feche com `mcp-fim --arquivar`; depois revise as novidades (§6). `docs/hardware/` é manual (do usuário).
- **"O servidor mudou"** (tabelas, rotas, migração, erro 404/400 novo numa IA, ou o aviso "O CONTRATO MUDOU"
  do `sincronizar.py`) → siga `docs/migracao_servidor.md`, sem perguntar: `servidor.py snapshot` →
  `contrato.py diferenca` (rotas/campos/tabelas/migrações × `docs/servidor_contrato.json`, com `arquivo:linha`
  de quem usa cada coisa) → medir no snapshot → adaptar Tester/Server/Helper (tabela "onde mexer") e o `USO` do
  `contrato.py` → `testar.py --completo` → docs → `contrato.py capturar`. Produção só se lê até o fim.
- Modelo do servidor desde 24/09/2026: **instalação = `Device` com `plate` → `Vehicle`** (`PATCH /devices/<MIC>`),
  módulo Suntech/Entrack + chip em `telemetries/` (era `suntechs/`), `etilometers/` = leitura. Detalhe:
  `docs/server_reference.md` §2.
- **Testar tudo** → `docs/testes.md`: `python docs/tools/testar.py [--api|--completo|--bancada]` (nada grava);
  o que grava (aparelho/servidor) é o roteiro manual do §3, com o ok do usuário.

## Comandos úteis

```bash
python docs/tools/kb.py atualizar | busca termo [--codigo] | novidades | status
python docs/tools/sincronizar.py [--sem-snapshot]                  # "sincronizar os documentos"
python docs/tools/notion_sync.py status | mcp-proximos | mcp-fim --arquivar
python docs/tools/servidor.py resumo | snapshot                    # produção → docs (só leitura)
python docs/tools/test_notion_sync.py          # testes do sincronizador (sem rede)
python docs/tools/test_contrato.py             # testes do contrato.py (sem rede)
python docs/tools/testar.py [--api|--completo|--bancada]   # bateria das 3 IAs (docs/testes.md)
python docs/tools/contrato.py diferenca | verificar | uso | capturar   # o que mudou no servidor
python Tester/tools/test_cli.py                 # register/install/edit/onde/progresso do Tester com API falsa
python Tester/tools/sighir.py onde <MIC|ETL|módulo|placa|série>      # onde já está cadastrado
python <IA>/tools/boot.py setup | status | start claude|gemini --dry-run
cd Server/scanner && python test_scan.py        # testes do scanner (sem rede)
python Helper/tools/test_helper.py              # testes do Helper (sem rede; inclui cobertura dos eventos do firmware)
python Tester/tools/sighir.py install MIC… --placa X --telemetria mix2   # prévia de instalação (grava só com --yes)
python Helper/tools/helper.py veiculo PLACA      # leitura da produção
```

As suítes `test_*.py` não usam unittest/pytest: cada uma roda todas as funções `test*` do próprio arquivo e
sai com código 1 se alguma falhar (`test_scan.py` para na primeira falha com traceback). Não há seleção de um
teste só — rode a suíte inteira.

Nesta máquina é `python` (não `python3`); no Bash use `PYTHONIOENCODING=utf-8`. AGY só carrega
`AGENTS.md`/hooks em modo **interativo** e em pasta confiável (o `boot.py` marca); `agy -p` ignora ambos.
