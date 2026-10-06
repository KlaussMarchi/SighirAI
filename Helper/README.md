# Sighir Helper AI

Assistente de suporte técnico do etilômetro Sighir para **instalador, técnico, calibrador, engenheiro e
cliente**: diagnostica problemas de portal, elétrica/instalação, telemetria (MiX, Suntech, Entrack),
firmware e sensor, consultando a base `../docs/` (manuais, firmware, chamados do Notion) e o servidor.

## Abrir

- Windows: `Helper_Claude.exe` (Claude Sonnet 5, esforço alto) ou `Helper_Gemini.exe` (Antigravity,
  Gemini Pro High). Linux/macOS: `bash start.sh claude` ou `bash start.sh gemini`.
- Primeira vez: instala sozinho Python, dependências (`.venv`), Git (Windows) e o agente; depois pede o
  login do Claude/Google. Os dois abrem sem pedir permissão.
- Dá para abrir o agente direto na pasta (`claude` / `agy`): os hooks preparam o ambiente do mesmo jeito.

## O que pedir

- "O etilômetro da placa RJK1D03 não pede teste" · "tela vermelha SENSOR SEM EEPROM" · "como ligo o relé
  no Suntech?" · "o que é `$ETEV35!`?" · "gere o chamado desse atendimento" · "revise as novidades da base".

## Ferramentas

`tools/helper.py` (servidor: `veiculo`, `logs`, `evento`, `device`, `anomalias`, `lista`, `chamado`,
`patch`), `../docs/tools/kb.py` (busca na base). Manual do agente: `AGENTS.md`; procedimentos em
`procedimentos/`; chamados gerados em `chamados/`.
