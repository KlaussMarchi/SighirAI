# SighirAI — as IAs da Sighir

Três assistentes independentes, cada um na sua pasta, e uma base de conhecimento comum:

| Pasta | IA | Para quê |
|---|---|---|
| `Tester/` | **Sighir Tester AI** | bancada: conecta no etilômetro pela USB, testa, configura, atualiza firmware e cadastra no servidor |
| `Server/` | **Sighir Scanner AI** | auditoria da frota: varre os logs de produção e mantém a tabela `anomalies` |
| `Helper/` | **Sighir Helper AI** | suporte técnico para instalador, técnico, calibrador, engenheiro e cliente (portal, elétrica, telemetria, firmware) |
| `docs/` | base comum | manuais curados, firmware (`hardware/Main`), export do Notion, índice e busca (`docs/tools/kb.py`) |

Cada IA funciona sozinha: pode apagar as outras duas pastas que ela continua igual (só precisa da `docs/`
ao lado para a base de conhecimento).

## Abrir

| | Claude Code (Sonnet 5, esforço alto) | Antigravity / AGY (Gemini Pro High) |
|---|---|---|
| Windows | `Tester_Claude.exe` · `Server_Claude.exe` · `Helper_Claude.exe` | `Tester_Gemini.exe` · `Server_Gemini.exe` · `Helper_Gemini.exe` |
| Linux/macOS | `bash start.sh claude` (dentro da pasta) | `bash start.sh gemini` |

Os dois agentes abrem **sem pedir permissão** (bypass) e com acesso à `docs/`. Na primeira vez o
lançador instala o que faltar: Python, `.venv` com as dependências, Git (Windows, exigido pelo Claude
Code), o próprio Claude Code ou o Antigravity CLI (instaladores oficiais), marca a pasta como confiável
no AGY e indexa a base. Depois é instantâneo. Login do Claude/Google é pedido pelo próprio agente.

Abrindo o agente direto (`claude` ou `agy` dentro da pasta), vale o mesmo: `.claude/settings.json` e
`.agents/hooks.json` rodam o `tools/boot.py` no início da sessão (prepara dependências e informa o
estado do ambiente ao agente). As duas ferramentas leem o mesmo manual: `AGENTS.md` (o `CLAUDE.md` importa).

## Atualizar a base com o Notion

Diga (na raiz ou em qualquer IA): **"sincronizar os documentos"**. Ela segue `docs/sincronizar.md` e roda
`python docs/tools/sincronizar.py`: resumo do servidor (`docs/servidor_resumo.md` + snapshot do banco),
Notion inteiro e índice. A pasta `docs/hardware/` continua manual.

1. `docs/tools/notion_sync.py` baixa só o que mudou na página **Sighir Enterprise** (chamados, tarefas,
   troubleshooting, PDFs) para `docs/Notion/`, no formato do export, **sem a seção Credenciais**.
   - Com token (qualquer agente, qualquer máquina): `python docs/tools/notion_sync.py sincronizar`.
     Criar o token uma vez: `docs/sincronizar.md` §4, depois
     `python docs/tools/notion_sync.py token ntn_...` (fica em `docs/.notion_token`, fora do git).
   - Sem token, no Claude com o conector Notion: a IA busca pelo conector e entrega ao script.
   - Sem nenhum dos dois: export manual (Markdown & CSV, com subpáginas) em `docs/Notion/`.
2. Em seguida roda o `kb.py atualizar`, que refaz o índice, os chamados (`docs/casos_notion.md`) e
   os checklists (`docs/troubleshooting.md`, da seção Suporte → Troubleshooting).
3. A IA revisa as novidades e propõe levar o que é novo para os documentos curados
   (`kb.py novidades` / `kb.py revisado`).

Testes (sem rede): `python docs/tools/test_notion_sync.py`.

## Manutenção

- Lançadores: `tools/launcher/` de cada IA (`build.ps1` no Windows, `build.sh` no Linux). Os dois `.exe`
  de uma pasta são o mesmo binário; o nome decide o agente.
- `tools/boot.py`, `tools/_venv.py` e `tools/launcher/*` são idênticos nas três pastas; o que muda fica
  em `tools/ai.json`. Alterou um, copie para as outras.
- Modelo/esforço: `tools/ai.json` (lançador) e `.claude/settings.json` (Claude aberto direto).
- Fora do git: `docs/Notion/` (tem credenciais na `Handover.pdf`), `docs/.notion_token`, `docs/ServerAnalysis/files/`,
  `docs/.index/`, `.venv/`, `.sighir/`, `scratch/`.
