@AGENTS.md

## Notas do Claude Code

- `.claude/settings.json` fixa o padrão desta pasta: Sonnet 5, esforço alto, `bypassPermissions` e acesso a
  `../docs`. O hook `SessionStart` roda `tools/boot.py hook claude` e injeta o estado do ambiente
  (inclusive as portas seriais vistas agora).
- `flash` e outras operações longas: rode com `run_in_background` e acompanhe o `flash.log`.
