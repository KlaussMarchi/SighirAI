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

## Catálogo automático (gerado por `tools/kb.py atualizar` em 08/10/2026 10:03)

Não edite este bloco à mão: descrições vêm de `tools/catalogo.json` (registre com `kb.py revisado`). ⚠ = novo/alterado e ainda não revisado.

### Documentos curados (docs/*.md)

| arquivo | conteúdo |
|---|---|
| `comandos_config.md` | Comandos seriais, parser, configurações (NVS) e padrões, Wi-Fi, rotas HTTP, OTA — *quando:* configurar/consultar o aparelho |
| `diagnostico.md` | Playbook por sintoma: hipóteses, testes, soluções, casos, categorias de anomalias — *quando:* qualquer problema de campo |
| `eletrica_instalacao.md` | Cabos, pinagens, relé, chicote Suntech, instalação, validação, bancada, lições de campo — *quando:* elétrica e instalação |
| `firmware_reference.md` | Eventos $ETEVnn! com linha do firmware, fluxos e o que cada telemetria repassa (medido no banco) — *quando:* interpretar eventos e logs |
| `migracao_servidor.md` ⚠ | Roteiro quando o servidor muda: contrato.py diferenca (rotas/campos/tabelas/migrações × referência, com quem usa), medir no snapshot, onde mexer em cada IA, testar, histórico das migrações — *quando:* servidor/tabelas/API mudaram, erro 404/400 novo numa IA, aviso 'O CONTRATO MUDOU' |
| `operacao_telas.md` | Telas (texto exato), cores, sons, fluxo do teste e menu ID/INFO/CONFIG — *quando:* o que o motorista/técnico vê |
| `portal_app.md` ⚠ | Portal web, app Sighir Monitor, portais MiX/SystemSat/Movieit, API (rotas, filtros, armadilhas) — *quando:* portal, app e servidor |
| `sensor_calibracao.md` | Sensor, sopro, estabilização, purga, vida útil, calibração, troca de sensor, falso positivo — *quando:* problemas de sensor/sopro/leitura |
| `server_reference.md` ⚠ | Schema do servidor Django, sincronização, instalar/editar/deletar, rotas — *quando:* operar no banco/servidor |
| `sincronizar.md` | Procedimento "sincronizar os documentos": Notion inteiro (API ou conector) + resumo do servidor + índice, e o que revisar depois — *quando:* atualizar a base docs/ |
| `sistema.md` | Visão geral: peças, identidades, fluxo de dados, ciclo de uso, perfis, glossário — *quando:* entender o sistema |
| `telemetrias.md` | MiX/MIX 2.0/Suntech/Entrack: ignição, bloqueio, handshake, portais, o que chega ao servidor — *quando:* problemas de integração/telemetria |
| `testes.md` | Bateria de testes das 3 IAs (testar.py: offline, --api só leitura, --completo, --bancada) e roteiro manual de bancada/gravação com o esperado de cada passo — *quando:* depois de mudar código ou migrar o servidor; antes de entregar |
| `troubleshooting.md` | Checklists de campo da equipe por problema (requisição de teste, atualização, bloqueio, app, reinícios, álcool, sopro, comunicação) — gerado do Notion (Suporte → Troubleshooting) — *quando:* roteiro de campo; o porquê e as evidências ficam no diagnostico.md |

### Firmware (docs/hardware/)

Código-fonte real do etilômetro em `hardware/Main/` (versão no `Main.ino`: **v6.4.8**). Busque no código com `kb.py busca termo --codigo`.

| arquivo | conteúdo |
|---|---|
| `hardware/FIRMWARE_ETILOMETRO.md` | Documentação completa do firmware v6.4.8 módulo a módulo, tabelas e bugs latentes (§17) — *quando:* comportamento exato do aparelho |
| `hardware/PROMPT_ASSISTENTE_SUPORTE.md` | Prompt original do assistente técnico (base do Helper): método, formato de resposta, perfis, limites, mapa sintoma→código — *quando:* como conduzir um atendimento |

### Notion — PDFs (manuais, protocolos, procedimentos)

| arquivo | conteúdo |
|---|---|
| `Notion/ETIQUETA_SINAL_IGNIO_E_RELE.pdf` | Etiqueta do corte de ignição: pós-chave nos pinos 30/87a do relé, VCC e GND — *quando:* ligação do relé de bloqueio (3 p.) |
| `Notion/Handover.pdf` | Handover (Letícia Reis): integrações MiX/SystemSat/Suntech/Movieit/Entrack, contatos, uso dos portais parceiros, AOVX/SyncTrak. CONTÉM CREDENCIAIS — não copiar — *quando:* operar portal da MiX/SystemSat/Movieit, contato das telemetrias (45 p.) |
| `Notion/MANUAL_DE_INSTALAO_DAD01_(3).pdf` | Manual de instalação DAD01 v0.2 (dez/2024): componentes, cabo de força (cores), relé positivo/negativo, instalação autônoma/compartilhada, app, update, solução de problemas MiX/SystemSat/Movieit — *quando:* cores do chicote, relé, passo a passo com o app (35 p.) |
| `Notion/Manual_do_usuario_ST4305-1.pdf` | Manual do fabricante do rastreador Suntech ST4305 (comandos, LEDs, entradas/saídas) — *quando:* detalhe do módulo Suntech (74 p.) |
| `Notion/PROTOCOL.pdf` | Protocolo serial ANTIGO (ago/2025): comandos ID:/CF:, lista de variáveis, telemetrias 0–5 (inclui Infleet/Systemsat) — *quando:* aparelhos antigos; significado histórico de chaves (6 p.) |
| `Notion/Passo_a_passo__cabo_suntech.pdf` | Montagem do chicote Suntech: derivações VCC/IGN/GND e relé 85/86/30/87a — *quando:* montar ou conferir chicote Suntech (5 p.) |
| `Notion/Procedimento_Padro_Testes_funcionais__Sighir.pdf` | Testes funcionais de bancada das placas: pinagem 8 e 6 vias, continuidade do espiral, ajuste dos 3 reguladores, API de testes — *quando:* bancada, pinagem, reguladores (15 p.) |
| `Notion/Procedimento_Padro_de_Instalao__Sighir.pdf` | INST 0001-02 — procedimento padrão de instalação: ferramentas, acomodação, RS232/microfit/DB9, S1/S2 MiX, verificação, app, testes de comunicação e solução de problemas (MiX, bloqueio, sensor) — *quando:* instalação e problemas de instalação (31 p.) |
| `Notion/Procedimento_de_Calibrao_Tcnico.pdf` | PPTC 0001-02 — manual técnico de calibração: modelo a·b^(cx+d), ajuste LM, R²/RMSE/MAE, incerteza GUM (D'Quim/Guth/ACMA), validade 365 dias — *quando:* metrologia, incerteza, certificado (14 p.) |
| `Notion/Procedimento_de_Calibrao___Sighir.pdf` | PPTC 0001-01 — procedimento de calibração (visão geral): bancada de gás, aquisição, filtro de outliers, regressão, certificação, validade 1 ano — *quando:* calibração de sensores (9 p.) |
| `Notion/Procedimento_de_Instalao_Entrack.pdf` | Procedimento de instalação com Entrack: conexões, relé no fio de ignição, verificação de comunicação — *quando:* instalar Entrack (7 p.) |
| `Notion/Procedimento_de_Instalao_MIX 1.pdf` | Procedimento de instalação com MiX (versão mais nova, com configuração remota): S1, bateria, pen drive, script de ativação, validação — *quando:* instalar MiX (6 p.) |
| `Notion/Procedimento_de_Instalao_MIX.pdf` | Procedimento de instalação com MiX (versão anterior; prefira a "MIX 1") — *quando:* histórico (5 p.) |
| `Notion/Procedimento_de_Instalao_Suntech 1.pdf` | Procedimento de instalação com Suntech (versão mais nova): 4 vias/6 vias, relé acoplado no fio de ignição, verificação, configuração remota — *quando:* instalar Suntech (7 p.) |
| `Notion/Procedimento_de_Instalao_Suntech.pdf` | Procedimento de instalação com Suntech (versão anterior; prefira a "Suntech 1") — *quando:* histórico (6 p.) |
| `Notion/api-logs.pdf` | Guia da API de logs: token JWT, /api/v2/logs/ e filtros (start, end, vehicle, event, telemetry), paginação, dash-data, alert-events, tabela de eventos — *quando:* consultar logs pela API (12 p.) |
| `Notion/guia-integracao-camera.pdf` | Integração com provedores de câmera: publicação de ocorrências, janela de vídeo, correlação, /logs/video/, homologação — *quando:* câmeras/vídeo de eventos (14 p.) |
| `Notion/main 1.pdf` | MUAM 0001-01 — manual do app Sighir Monitor: perfis, Wi-Fi do aparelho, configurações, monitoramento, desbloqueio manual, testes de protocolo — *quando:* dúvidas sobre o app (9 p.) |
| `Notion/main 2.pdf` | MUWP 0001-01 — manual do Portal Web: Controle, bloqueio remoto, Mapa, Software (OTA/parâmetros), Monitoramento, Relatórios de calibração — *quando:* dúvidas sobre o portal (11 p.) |
| `Notion/main.pdf` | PPTC 0001-01 — protocolo de comunicação DAD01 (atual): comandos, eventos $ETEVnn!, estágios do sensor, fluxos MIX 2.0 — *quando:* significado oficial de eventos/comandos (13 p.) |
| `Notion/manual_de_treinamento.pdf` | Manual do motorista (DAD01): passo a passo do teste, adiamento, randômico, manobra, câmera, menu, troca de sensor, cuidados contra falso positivo — *quando:* orientar motorista/cliente (27 p.) |

### Notion — tabelas (bancos exportados)

| arquivo | conteúdo |
|---|---|
| `Notion/Controle de entradas e saídas - ANO 2025 39d79b90eb7380888238f3166aafb544_all.csv` | IDENTIFICADOR: 00099 | ID ETILÔMETRO: MIC1712914554893427 | ID TELEMETRIA: MIX | RELAÇÃO DE ESTOQUE: ENTRADA | |
| `Notion/Controle de entradas e saídas - ESTOQUE 2026 39d79b90eb7380bdb3c1000bb9ee8548_all.csv` | ID DO ETILÔMETRO: MIC7296153883531459 | ID TELEMETRIA: 1700008080 - SUNTECH | RELAÇÃO DE ESTOQUE: ENTRADA | DE |
| `Notion/Estoque Sighir - Duque de Caxias/Estoque - Itens com defeito 3c079b90eb738087aa60000bd66c81de_all.csv` | Name: Espiral | Quantidade: 0 | Selecionar: Defeito |
| `Notion/Estoque Sighir - Duque de Caxias/Estoque - Produtos 25679b90eb7381c5a519c82156cc9182_all.csv` | Item do estoque: Derivadores suntech | Parent item: Conjunto Suntech | Quantidade: 0 | Custo Unitário: 1.43 |  |
| `Notion/Estoque Sighir - Duque de Caxias/Estoque - Produção 3c279b90eb7380ebb792000b606ee85d_all.csv` | Selecionar: Produção | Quantidade: 24 | Itens: Cabo suntech derivado | Número: 24/08/2026 |
| `Notion/Fonecedores Sighir 29379b90eb738141875fe2dd070c7c63_all.csv` | APLICAÇÃO: Todas | OBSERVAÇÃO: Via contato da Lisi | FORNECEDOR: MTC Cabos | LINK/CONTATO: (51) 99335-4742 | P |
| `Notion/Resolução de Problemas 25079b90eb7380048323ce9f5903d098_all.csv` | Tabela de chamados de campo (Notion, todas as linhas) — resumida em casos_notion.md — *quando:* chamados anteriores |
| `Notion/Tarefas 2af79b90eb738010861cc785e4bcdae8_all.csv` | Nome: Preparar 5 equipamentos Geocargo - mesmo padrão predileto | Criado em: 31/08/2026 15:31 (BRT) | Status:  |
| `Notion/Tarefas 31f79b90eb73812dae37c0f3638cd99c_all.csv` | Nome: Estabelecer API para mostrar nossos logs no portal da Systemsat, ver com eles no grupo e implementar | C |
| `Notion/Tarefas fb479b90eb7383c398f781f4e7ba717c_all.csv` | Nome: Preparar 6 equipamentos Ricker Transportes | Criado em: 07/08/2026 08:32 (BRT) | Status: Concluído | Pes |

### Notion — páginas (.md) por pasta

- **(raiz)**: 2 página(s)
- **Resolução de Problemas**: 17 página(s)
- **Tarefas**: 10 página(s)
- **Tarefas 2af7-dae8**: 3 página(s)
- **Tarefas fb47-717c**: 3 página(s)

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

Imagens soltas indexadas por nome: 34. Chamados de campo resumidos em `casos_notion.md` (gerado).

<!-- KB:AUTO:END -->
