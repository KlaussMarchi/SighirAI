@AGENTS.md

## Notas do Claude Code

- `.claude/settings.json` fixa o padrão desta pasta: Sonnet 5, esforço alto, `bypassPermissions` e acesso a
  `../docs`. O hook `SessionStart` roda `tools/boot.py hook claude` e injeta o estado do ambiente
  (inclusive as portas seriais vistas agora).
- `flash` e outras operações longas: rode com `run_in_background` e acompanhe o `flash.log`.
- `qualidade` com operador (`autodiagnostico`, `sem-alcool`, `com-alcool`) e `configurar --yes` (reinicia): Bash com
  `timeout: 600000` — o padrão de 2 min corta o autodiagnóstico (~3 min). `qualidade sopro` (~5 min, mais com etapas
  refeitas): `run_in_background` e leia a saída quando terminar.
