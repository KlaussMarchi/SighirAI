@AGENTS.md

## Notas do Claude Code

- `.claude/settings.json` fixa o padrão desta pasta: Sonnet 5, esforço alto, `bypassPermissions` e acesso a
  `../docs`. O hook `SessionStart` roda `tools/boot.py hook claude` e injeta o estado do ambiente.
- PDFs com figura/tabela que o `kb.py` extrai mal: leia o próprio PDF com a ferramenta Read (`pages`).
- Tarefas longas (varrer muitos logs, instalar dependências) → rode em background e leia a saída depois.
