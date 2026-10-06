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
- `docs/tools/kb.py`: indexa `docs/` (PDF via pdftotext/pypdf), gera o bloco automático do `INDEX.md` e
  o `casos_notion.md` e o `troubleshooting.md`; catálogo curado em `docs/tools/catalogo.json`.
- **"Sincronizar os documentos"** (ou "sincronize com o notion") → siga `docs/sincronizar.md`, sem perguntar:
  `python docs/tools/sincronizar.py` = `servidor.py` (resumo da frota + snapshot do banco) +
  `notion_sync.py` (árvore inteira da Sighir Enterprise, sem a seção Credenciais, arquiva o que saiu) +
  `kb.py`. Código 10 = sem token do Notion: faça a varredura pelo conector (§3) até a fila esvaziar e
  feche com `mcp-fim --arquivar`; depois revise as novidades (§6). `docs/hardware/` é manual (do usuário).

## Comandos úteis

```bash
python docs/tools/kb.py atualizar | busca termo [--codigo] | novidades | status
python docs/tools/sincronizar.py [--sem-snapshot]                  # "sincronizar os documentos"
python docs/tools/notion_sync.py status | mcp-proximos | mcp-fim --arquivar
python docs/tools/servidor.py resumo | snapshot                    # produção → docs (só leitura)
python docs/tools/test_notion_sync.py          # testes do sincronizador (sem rede)
python <IA>/tools/boot.py setup | status | start claude|gemini --dry-run
cd Server/scanner && python test_scan.py        # testes do scanner (sem rede)
python Helper/tools/test_helper.py              # testes do Helper (sem rede; inclui cobertura dos eventos do firmware)
python Tester/tools/sighir.py install MIC… --placa X --telemetria mix2   # prévia de instalação (grava só com --yes)
python Helper/tools/helper.py veiculo PLACA      # leitura da produção
```

Nesta máquina é `python` (não `python3`); no Bash use `PYTHONIOENCODING=utf-8`. AGY só carrega
`AGENTS.md`/hooks em modo **interativo** e em pasta confiável (o `boot.py` marca); `agy -p` ignora ambos.
