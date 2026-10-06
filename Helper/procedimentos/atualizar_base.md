# Atualizar a base de conhecimento (Notion, manual novo, firmware novo)

A base `../docs/` é compartilhada pelas três IAs. O `kb.py` mapeia tudo sozinho; a IA faz a parte que
exige leitura: entender o que mudou e levar os fatos novos para os documentos curados.

## Passo a passo

1. **"Sincronizar os documentos"** → `../docs/sincronizar.md` (`sincronizar.py`: Notion inteiro + resumo do
   servidor; já roda o passo 2). Sem token nem conector: o usuário substitui `../docs/Notion/` pelo
   export (Markdown & CSV com subpáginas). Arquivo novo: vai em `../docs/` (firmware novo: substitui
   `../docs/hardware/Main/`).
2. `python ../docs/tools/kb.py atualizar` — extrai só o que mudou, regenera o catálogo do `INDEX.md`, o
   `casos_notion.md` (chamados) e o `troubleshooting.md` (seção Troubleshooting da página raiz do Notion).
   (O `boot.py` já faz isso ao abrir qualquer IA.)
3. `python ../docs/tools/kb.py novidades` — lista documentos novos/alterados sem revisão.
4. Para cada um:
   - leia: `kb.py ler "<arquivo>"` (ou `--pagina N`); para figuras, abra o PDF;
   - compare com os docs curados e **incorpore só o que é novo e verificável**, citando a fonte:
     chamado resolvido → lição em `diagnostico.md` (e na tabela de lições de `eletrica_instalacao.md`
     se for elétrico); telemetria nova/script → `telemetrias.md`; tela/menu → `operacao_telas.md`;
     parâmetro/comando → `comandos_config.md`; portal/app/API → `portal_app.md`;
   - registre a revisão:
     `kb.py revisado "<arquivo>" --descricao "o que é" --quando "quando consultar"`.
5. Firmware novo: compare a versão (`kb.py status`), leia o changelog/diff relevante e ajuste os docs
   que citam comportamento (eventos, tempos, telas). Se mudou evento, avise que o Scanner (`../Server`)
   pode precisar de ajuste de regra.
6. Mostre ao usuário um resumo do que entrou em cada documento.

## Regras

- Nada de copiar credenciais (a `Handover.pdf` tem logins) para os docs curados.
- `casos_notion.md`, `troubleshooting.md` e o bloco automático do `INDEX.md` são gerados — não edite à
  mão (corrija no Notion e sincronize).
- `troubleshooting.md` mudou → confira a tabela "Checklist da equipe" (§0 do `diagnostico.md`) e o
  `CHECKLISTS` do `tools/helper.py` (o `test_helper.py` acusa seção renomeada).
- Fato sem fonte não entra. Divergência entre manual e firmware: registre as duas versões e qual vale.
