# Sighir Tester AI

Assistente de bancada: conecta no etilômetro pela **USB**, lê o status (firmware, `esp_id`, sensor),
testa, lê/grava configurações, troca a telemetria, bloqueia/desbloqueia, atualiza o firmware, recupera
aparelho travado e **cadastra dispositivos no servidor**. Também ajuda a depurar e melhorar as próprias
ferramentas com você.

## Abrir

- Windows: `Tester_Claude.exe` (Claude Sonnet 5, esforço alto) ou `Tester_Gemini.exe` (Antigravity,
  Gemini Pro High). Linux/macOS: `bash start.sh claude` ou `bash start.sh gemini`.
- Primeira vez: instala sozinho Python, dependências (`.venv`), Git (Windows) e o agente; depois pede o
  login. Os dois abrem sem pedir permissão e já rodam o `init` (status do aparelho conectado).
- Linux: o usuário precisa estar no grupo `dialout` para acessar a serial (o lançador avisa).

## Ferramentas

`tools/sighir.py` (CLI: `init`, `status`, `settings`, `telemetry`, `test`, `register`, `install`, `flash`…),
`main.py` (menu interativo antigo), `protocol.json` (testes). Manual do agente: `AGENTS.md`; detalhes em
`procedimentos/`; base comum em `../docs/`.

## Recompilar os `.exe`

Os dois são o mesmo binário (`tools/launcher/launcher.cs`); o nome decide o agente.
Windows (sem instalar nada): `powershell -ExecutionPolicy Bypass -File tools\launcher\build.ps1`.
Linux (mono): `bash tools/launcher/build.sh`.
