# Base de conhecimento Sighir — mapa

Pasta compartilhada pelas três IAs (`Tester/`, `Server/`, `Helper/`). Caminhos abaixo são relativos a
`docs/` (de dentro de uma IA: `../docs/...`). **Comece por aqui, não pelos PDFs.**

## Qual documento para qual pergunta

| Pergunta | Leia |
|---|---|
| Como o sistema funciona, peças, fluxo, glossário | `sistema.md` |
| Um problema de campo (sintoma → causa → teste → solução) | **`diagnostico.md`** |
| MiX / MIX 2.0 / Suntech / Entrack: ignição, bloqueio, scripts, o que chega ao servidor | `telemetrias.md` |
| Cabos, cores, pinagem, relé 30/87a, chicote Suntech, instalação, validação, bancada | `eletrica_instalacao.md` |
| O que o motorista vê: telas (texto exato), sons, cores, menu ID/INFO/CONFIG | `operacao_telas.md` |
| Sensor, sopro, estabilização, falso positivo, vida útil, calibração de laboratório, troca de sensor | `sensor_calibracao.md` |
| Comandos seriais, parser, configurações (NVS) e padrões, Wi-Fi, rotas HTTP, OTA | `comandos_config.md` |
| Portal web, app Sighir Monitor, portais MiX/SystemSat/Movieit, API e suas armadilhas | `portal_app.md` |
| Cada evento `$ETEVnn!` (linha do firmware, fluxos, o que cada telemetria repassa) | `firmware_reference.md` |
| Schema do servidor Django, sync, instalar/editar/deletar no banco | `server_reference.md` |
| Checklists de campo da equipe por problema (gerado do Notion → Troubleshooting) | `troubleshooting.md` |
| Chamados reais já atendidos (gerado do Notion) | `casos_notion.md` |
| "Sincronizar os documentos": Notion + servidor → `docs/` | `sincronizar.md` |
| Árvore do Notion sincronizada, com o arquivo local de cada página/banco (gerado) | `notion_mapa.md` |
| Frota em produção: telemetrias, empresas, firmware em campo, calibração, anomalias (gerado) | `servidor_resumo.md` |
| Firmware completo explicado módulo a módulo (bugs latentes na §17) | `hardware/FIRMWARE_ETILOMETRO.md` |
| Código-fonte do firmware (fonte da verdade do comportamento) | `hardware/Main/` |
| Manuais originais, protocolo PPTC, procedimentos, Handover | `Notion/*.pdf` (lista abaixo) |

Regra: **dúvida de procedimento/uso → docs curados; comportamento exato → firmware (`hardware/Main`);
procedimento oficial/metrologia → manual (PDF)**. Quando código e manual divergem, diga e explique qual vale.

## Buscar

```
python docs/tools/kb.py busca termo [termo...]      # sem acento/caixa; mostra arquivo, página e linha
python docs/tools/kb.py busca termo --codigo        # inclui o código do firmware
python docs/tools/kb.py ler main.pdf --pagina 5     # texto extraído de um PDF (ou --grep, --linhas)
python docs/tools/kb.py novidades                   # o que mudou no Notion e ainda não foi revisado
```

## Atualizar com o Notion

1. **"Sincronizar os documentos"** → `sincronizar.md` (`tools/sincronizar.py`: Notion inteiro, sem a
   seção Credenciais). Alternativa: export manual (Markdown & CSV, com subpáginas) em `docs/Notion/`.
2. `python docs/tools/kb.py atualizar` (a sincronização e os `boot.py` das IAs fazem isso sozinhos):
   reextrai só o que mudou, regenera o catálogo abaixo, o `casos_notion.md` e o `troubleshooting.md`.
3. `python docs/tools/kb.py novidades` → para cada documento novo/alterado: ler, incorporar o que for
   novo nos docs curados (ex.: chamado resolvido → lição em `diagnostico.md`) e registrar
   `kb.py revisado "<arquivo>" --descricao "o que é" --quando "quando consultar"`.

Fora do git (grandes ou sensíveis): `Notion/` (136 MB, tem credenciais na `Handover.pdf`),
`ServerAnalysis/files/` (snapshot do banco, 148 MB) e `.index/` (gerado).

<!-- KB:AUTO:BEGIN -->

## Catálogo automático (gerado por `tools/kb.py atualizar` em 04/11/2026 14:39)

Não edite este bloco à mão: descrições vêm de `tools/catalogo.json` (registre com `kb.py revisado`). ⚠ = novo/alterado e ainda não revisado.

### Documentos curados (docs/*.md)

| arquivo | conteúdo |
|---|---|
| `comandos_config.md` ⚠ | Comandos seriais, parser, configurações (NVS) e padrões, Wi-Fi, rotas HTTP, OTA — *quando:* configurar/consultar o aparelho |
| `diagnostico.md` ⚠ | Playbook por sintoma: hipóteses, testes, soluções, casos, categorias de anomalias — *quando:* qualquer problema de campo |
| `eletrica_instalacao.md` | Cabos, pinagens, relé, chicote Suntech, instalação, validação, bancada, lições de campo — *quando:* elétrica e instalação |
| `firmware_reference.md` ⚠ | Eventos $ETEVnn! com linha do firmware, fluxos e o que cada telemetria repassa (medido no banco) — *quando:* interpretar eventos e logs |
| `migracao_servidor.md` | Roteiro quando o servidor muda: contrato.py diferenca (rotas/campos/tabelas/migrações × referência, com quem usa), medir no snapshot, onde mexer em cada IA, testar, histórico das migrações — *quando:* servidor/tabelas/API mudaram, erro 404/400 novo numa IA, aviso 'O CONTRATO MUDOU' |
| `operacao_telas.md` ⚠ | Telas (texto exato), cores, sons, fluxo do teste e menu ID/INFO/CONFIG — *quando:* o que o motorista/técnico vê |
| `portal_app.md` ⚠ | Portal web, app Sighir Monitor, portais MiX/SystemSat/Movieit, API (rotas, filtros, armadilhas) — *quando:* portal, app e servidor |
| `sensor_calibracao.md` | Sensor, sopro, estabilização, purga, vida útil, calibração, troca de sensor, falso positivo — *quando:* problemas de sensor/sopro/leitura |
| `server_reference.md` | Schema do servidor Django, sincronização, instalar/editar/deletar, rotas — *quando:* operar no banco/servidor |
| `sincronizar.md` | Procedimento "sincronizar os documentos": Notion inteiro (API ou conector) + resumo do servidor + índice, e o que revisar depois — *quando:* atualizar a base docs/ |
| `sistema.md` | Visão geral: peças, identidades, fluxo de dados, ciclo de uso, perfis, glossário — *quando:* entender o sistema |
| `telemetrias.md` ⚠ | MiX/MIX 2.0/Suntech/Entrack: ignição, bloqueio, handshake, portais, o que chega ao servidor — *quando:* problemas de integração/telemetria |
| `testes.md` ⚠ | Bateria de testes das 3 IAs (testar.py: offline, --api só leitura, --completo, --bancada) e roteiro manual de bancada/gravação com o esperado de cada passo — *quando:* depois de mudar código ou migrar o servidor; antes de entregar |
| `troubleshooting.md` | Checklists de campo da equipe por problema (requisição de teste, atualização, bloqueio, app, reinícios, álcool, sopro, comunicação) — gerado do Notion (Suporte → Troubleshooting) — *quando:* roteiro de campo; o porquê e as evidências ficam no diagnostico.md |

### Firmware (docs/hardware/)

Código-fonte real do etilômetro em `hardware/Main/` (versão no `Main.ino`: **v6.5.4**). Busque no código com `kb.py busca termo --codigo`.

| arquivo | conteúdo |
|---|---|
| `hardware/FIRMWARE_ETILOMETRO.md` | Documentação completa do firmware v6.4.8 módulo a módulo, tabelas e bugs latentes (§17) — *quando:* comportamento exato do aparelho |
| `hardware/PROMPT_ASSISTENTE_SUPORTE.md` | Prompt original do assistente técnico (base do Helper): método, formato de resposta, perfis, limites, mapa sintoma→código — *quando:* como conduzir um atendimento |

### Notion — PDFs (manuais, protocolos, procedimentos)

| arquivo | conteúdo |
|---|---|

### Notion — tabelas (bancos exportados)

| arquivo | conteúdo |
|---|---|

### Notion — páginas (.md) por pasta

- **(raiz)**: 1 página(s)

### Outros

| arquivo | conteúdo |
|---|---|
| `Datasheet/antigo/main_v4.tex` | main_v4.tex (3 KB) |
| `Datasheet/main.tex` | main.tex (57 KB) |
| `Datasheet/tex/desenhos.tex` | desenhos.tex (10 KB) |
| `Datasheet/tex/telas.tex` | telas.tex (6 KB) |
| `ServerAnalysis/files/db.sqlite3` | snapshot do banco de produção (SQLite) (141 MB) |
| `fluxograma_tester.pdf` ⚠ | Procedimento padrão · Bancada e produção do etilômetro · Rev. 1 — 07/10/2026 (4 MB) |
| `servidor_contrato.json` | servidor_contrato.json (23 KB) |

Imagens soltas indexadas por nome: 20. Chamados de campo resumidos em `casos_notion.md` (gerado).

<!-- KB:AUTO:END -->
