@AGENTS.md

## Notas do Claude Code

- `.claude/settings.json` fixa o padrão desta pasta: Sonnet 5, esforço alto, `bypassPermissions` e acesso a
  `../docs`. O hook `SessionStart` roda `tools/boot.py hook claude` e injeta o estado do ambiente.
- `python scan.py --write` leva minutos na 1ª execução do dia: use `run_in_background` e leia a saída
  inteira quando terminar.
