# Elétrica e instalação

> Fontes: `Notion/MANUAL_DE_INSTALAO_DAD01_(3).pdf` (V0.2 dez/2024), `Notion/Procedimento_Padro_de_Instalao__Sighir.pdf`
> (INST 0001-02), `Notion/Procedimento_Padro_Testes_funcionais__Sighir.pdf` (bancada),
> `Notion/Procedimento_de_Instalao_{MIX 1,Suntech 1,Entrack}.pdf`, `Notion/Passo_a_passo__cabo_suntech.pdf`,
> `Notion/ETIQUETA_SINAL_IGNIO_E_RELE.pdf`, chamados do Notion. Figuras só nos PDFs.

## 1. Cabo de força (chicote do etilômetro)

| Cor | Sinal | Observação |
|---|---|---|
| **Vermelho** | VCC 10,5–40 V (12/24 V) | com **fusível** no VCC (o estoque usa 7,5 A) direto da bateria |
| **Marrom** | GND | terra da bateria |
| **Verde** | Pós-chave (10,5–40 V) | chave no 1º estágio — só usado em modo autônomo / chicote específico |
| **Branco** | Entrada 1 (10,5–40 V) — "ALT/alternador" nos conectores | no chicote Suntech vira a ignição (IGN) |
| **Laranja** | Relé de bloqueio (sinal +, mesma tensão da alimentação) | saída do DAD01 em modo autônomo |

Modo **sensor/compartilhado** (com telemetria): ligue só **VCC e GND** — ignição e bloqueio vêm do
rastreador. Modo **autônomo**: VCC, GND, pós-chave e sinal do relé.

## 2. Conectores (pinagem de bancada — PPTC testes funcionais)

**Conector de 8 vias (cabo espiral, exposta ↔ embutida):**

| Pino | Lado exposta | Lado embutida |
|---|---|---|
| 1 | Chave — verde | VCC — vermelho |
| 2 | RX — azul | Relé/COM — laranja |
| 3 | Relé/COM — laranja | RX — azul |
| 4 | VCC — vermelho | Chave — verde |
| 5 | N/A | GND — preto |
| 6 | Alternador/ALT — branco | TX — amarelo |
| 7 | TX — amarelo | Alternador/ALT — branco |
| 8 | GND — preto | N/A |

O lado do espiral importa (encaixe conforme a figura 7 do PPTC). **Continuidade de cada via ≤ 1,6 Ω**
(medir com o espiral solto).

**Conector de 6 vias (embutida ↔ alimentação/telemetria):** 1 Chave (verde) · 2 Alternador/ALT (branco) ·
3 VCC (vermelho) · 4 GND (marrom) · 5 N/A · 6 PSM (laranja).

**Cabo RS232:** microfit no módulo de telemetria (alimentação 12 V/GND + dados) e **DB9** na embutida
(aperte os 2 parafusos). Na Suntech/Entrack o RS232 tem conector de **4 vias** (só comunicação) e a
alimentação vem por um conector de 6 vias separado a partir do módulo.

Tipos de cabo serial: Cabo MIX (DB9–microfit), chicote Suntech, cabo DB9–USB (bancada), cabo serial Sighir.

## 3. Relé de bloqueio (padrão automotivo 5 pinos)

| Pino | Função |
|---|---|
| 85 e 86 | bobina (aciona o relé) |
| 30 | comum |
| 87 | NA — fecha quando o relé aciona |
| **87a** | **NF — abre quando o relé aciona** |

Corte de ignição usado pela Sighir: **corta-se o fio do pós-chave** e as duas pontas vão nos pinos **30 e
87a** (etiqueta `ETIQUETA_SINAL_IGNIO_E_RELE.pdf`: "SINAL DE PÓS CHAVE → PINO 30 / PINO 87a; VCC; GND").
Relé em repouso = ignição passa (liberado); relé acionado = 87a abre = ignição cortada (bloqueado).

- **Sinal de corte negativo** (padrão Suntech): 86 no VCC, 85 na **saída 1 do Suntech (fio laranja)**
  configurada para sinal negativo; 30 no GND se o sinal de corte for negativo.
- **Sinal de corte positivo** (DAD01 autônomo): 86 no GND, 85 na saída do DAD01 (sinal +); 30 no VCC.
- Sempre confirme com a montadora/empresa qual polaridade o circuito de ignição espera.
- Ordem de verificação quando "não bloqueia/não libera" (Suntech): **GND → VCC → pino 30 → pino 87a**.

## 4. Chicote Suntech (montagem na bancada)

Itens: cabo Suntech, chicote Sighir, porta-relé, derivadores, espuma, abraçadeiras, multímetro
(continuidade após **cada** emenda).

1. Vermelho (Suntech) → vermelho (Sighir): **VCC**.
2. Azul (Suntech) → branco (Sighir): **IGN**.
3. Preto (Suntech) → marrom (Sighir): **GND**.
4. Relé: terminal **85** ← vermelho do chicote Sighir; terminal **86** ← laranja do cabo Suntech.
5. Corte os fios do porta-relé deixando só **87a e 30** (vão para o corte da ignição).
6. Espuma nas emendas, trançar e prender o excesso, testar continuidade de novo.

Entrack (Handover): usar o cabo RS232 da Suntech, cortar a ponta microfit e derivar com os fios seriais
da Entrack; deixar para fora só 87a e 30.

## 5. Instalação no veículo (qualquer telemetria)

1. Proteção antiviolação (ex.: **t4s**)? Peça ao gestor para desativar antes de abrir o painel.
2. **Desligue a chave geral.**
3. Posicione a **embutida** em superfície plana, escondida, cabos protegidos (principalmente o de bloqueio).
4. RS232 no módulo de telemetria (MiX: entrada **S1**; Suntech/Entrack: conector de 4 vias) e DB9 na embutida.
5. Alimentação: MiX → vermelho no + e marrom no − da bateria; Suntech/Entrack → 6 vias a partir do módulo.
6. Espiral pela parte interna do painel, 8 vias na embutida. **Exposta** perto do motorista, firme
   (trepidação!), longe de sol direto.
7. Religue a chave geral: o display tem de acender e mostrar o logo (sem logo = sem alimentação).
   Meça **12 V** nos fios de alimentação da embutida no conector RS232.
8. Toque na tela apagada → menu → **ID**: dados aparecem = touch e alimentação OK.
9. MiX: pen drive de ativação plugado e motorista identificado; peça à MiX o **script de ativação**
   informando a placa. Suntech/Entrack: relé do chicote no fio de ignição (30/87a).
10. Configure pelo **app Sighir Monitor** (Wi-Fi `SIGHIR - MICxxxx`, senha `12345678`): tipo de instalação,
    parâmetros (arquivo pré-configurado da empresa ou manual), placa, Wi-Fi da base (sem caracteres
    especiais). O aparelho reinicia com a configuração.

## 6. Validação (obrigatória antes de liberar o veículo)

1. Chave no 1º estágio (pós-chave) → em alguns segundos o etilômetro **pede o teste**.
2. Faça o teste sem álcool → tela verde **"Veículo Desbloqueado"** → o veículo **liga de verdade**.
3. Desligue → aparece **"Tempo de Manobra"**.
4. Espere o tempo de manobra → **"Veículo Bloqueado"** (vermelho) → o veículo **não dá partida** e um
   novo teste é pedido ao ligar.
5. Teste de adiamento: adie e confira que o teste volta após o prazo.
6. No app: *Monitoramento de Logs* com o Wi-Fi do aparelho mostra os eventos ao vivo.

Se liga sem teste → comunicação com a telemetria ou sinal de bloqueio comprometidos. Se pede teste e fica
bloqueado mesmo negativo → o módulo não está recebendo/executando o desbloqueio.

## 7. Bancada (antes de ir a campo) — resumo do PPTC de testes funcionais

1. Grimpar o espiral (8 vias no etilômetro, 6 na alimentação) e medir continuidade (≤ 1,6 Ω).
2. **Reguladores da embutida** (3 trimpots; gire com suavidade, ponta negativa no GND):
   fonte 5,0–5,5 V em VCC/GND (6 vias) → regulador 1: VCC no conector de 8 vias em 3,0–3,5 V; fonte
   6,5–7,0 V → regulador 1 em 5,7–5,8 V; fonte 5,0–5,5 V na entrada ALT → regulador 2: ALT em 3,2–3,4 V;
   fonte na entrada KEY → regulador 3: KEY em 3,2–3,4 V.
3. Conectar as placas, USB-C no ESP32, RS232-USB na embutida; API de testes → "Testar componentes":
   display/touch, conversor A/D + sensor de álcool, sensor de pressão (apertar), buzzer, relé (clique;
   ~0 Ω acionado / aberto em repouso), DHT (temperatura coerente), serial (`$ETAT01!` → `$ETATACK!`).

Hoje essa bancada é feita com o **Sighir Tester AI** (`Tester/`): `status`, `test`, `settings`,
`telemetry`, `flash`, `register`.

## 8. Lições de campo (chamados reais)

| Caso | O que era | Lição |
|---|---|---|
| SRU4A50 (08/2025) — bloqueava em viagem + tela de manobra | ponto de bloqueio na **bomba de combustível** (terceirizado); tela oscilando | bloquear no **pós-chave/ignição**, nunca na bomba; oscilação de tela = alimentação ruim |
| LUE9A29 (08/2025) — reiniciava, não deixava testar | **bateria viciada**; ao ligar o Wi-Fi o pico de corrente derrubava o ESP | medir a bateria sob carga; 5 boots incompletos → "Reiniciamentos Inesperados"/"Alimentação Indevida" |
| contatto (08/2026) — tela apagada após pane | **fusível/alimentação** | reencaixar fusível e alimentação antes de trocar peças |
| Pedro/carro (09/2025) — sem comunicação | **chip invertido** no Suntech | conferir chip e antena antes de condenar o módulo |
| RJK1D03 (08/2025) — não pedia teste | **módulo Suntech morto** após parado | teste serial do menu falha → trocar o kit |
| LUA5E58 (08/2025) — pedia teste mas não bloqueava | aparelho em **MIX antigo**, rastreador em MIX 2.0 | configurar telemetria certa e pedir o script correto à MiX |
| Manual — "pedia vários testes seguidos" / "não recebia eventos" | **cabo de comunicação da MiX** | trocar o cabo; testar com RS232/USB e o Tester |
| Manual — "desbloqueava mas o veículo não ligava" | **outro acessório** (outro rastreador) bloqueando; ou relé de bloqueio nunca funcional | testar bloqueio só com o módulo de telemetria, sem o etilômetro |
