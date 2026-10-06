# Telemetrias (rastreadores) — como cada uma conversa com o etilômetro

> Fontes: firmware v6.4.8 `objects/telemetry/` (modos `mix`, `mix2`, `suntech`, `entrack`), PPTC 0001-01,
> manuais `Procedimento_de_Instalao_{MIX,Suntech,Entrack}*.pdf`, `Handover.pdf`, medição no banco
> (`firmware_reference.md` §4) e a tabela `companies` da API (23/09/2026).

O etilômetro **não bloqueia sozinho nem sabe da ignição sozinho**: quem informa a ignição e executa o
bloqueio é o rastreador. A configuração `telemetry` (NVS do aparelho) diz qual "idioma" ele fala; ela só
é lida **no boot** (trocar exige reiniciar). No menu: INFO pág. 1 mostra "Empresa – Telemetria …" e
INFO pág. 3 mostra "Telemetria Ativa/Desativada" (recebeu algo da serial nos últimos 15 s).

## 1. Resumo

| `telemetry` | Modo (tela no boot) | Ignição vem de | Keep-alive do etilômetro | Bloqueio feito por | Handshake no boot |
|---|---|---|---|---|---|
| **0** | MIX 1.0 / MIX antigo ("Telemetria MIX 1.0 Iniciada") | `$ETAT01!` liga, `$ETEV04!` desliga | `$ETACK!` a cada 5 min | rastreador, ao ler `$ETBL010000!`/`$ETBL020000!` | nenhum (2,5 s "Verificando Comunicação") |
| **2** | Suntech ("Telemetria Suntech Iniciada") — **default de fábrica** | pacote `STT;…` (campo da chave, char 7) em resposta ao `SttReq` | `SttReq` a cada 2 s | módulo Suntech via `CMD;<id>;04;01` (bloq) / `;04;02` (desbloq) → saída 1 → relé | espera `STT;` até 20 s; falhou → tela vermelha "Comunicação Não Encontrada" |
| **5** | MIX 2.0 / MiX novo ("Telemetria MIX 2.0 Iniciada") | `$ETAT01!` (ou `$ETEV31!` se carro) liga; `$ETEV04!` desliga; `$ETEV03!` = em movimento | `$ETACK!` a cada 5 min | rastreador (script MiX) | nenhum |
| **6** | Entrack ("Telemetria Entrack Iniciada") | `+QACC:high/low` em resposta ao `AT+QACC?` (média das 4 últimas: >0,75 liga, <0,15 desliga) | `AT+QACC?` a cada 2 s | módulo Entrack via `AT+GPIOVALUE=0,1` (bloq) / `0,0` (desbloq) | espera `OK` do `AT+QACC?` até 20 s, lê `AT+ID?`, envia `AT+ASSISTMASK0900=2`, `AT+LOG=5`, `AT+RELAYMODE=1` |

Valores legados (protocolo antigo, `PROTOCOL.pdf` 2025): 1 = autônoma, 3 = Infleet, 4 = Systemsat — **não
existem no firmware v6.4.8**. No Tester, `telemetry mix` grava **0** (MIX antigo) e `mix2` grava **5**.

No servidor, a telemetria de cada instalação é uma `Company` do tipo telemetria; o campo `value` guarda o
código: `MIX TELEMATICS` = 0, `SUNTECH` = 2, `MIX TELEMATICS (NOVO)` = 5, `Entrack` = 6
(`Etilometro.telemetry_label` na API). A lista `companies/` mistura transportadoras e telemetrias
(o filtro `?type=` não é aplicado pela API — filtre pelo campo `type`).

**Frota por telemetria** (números atualizados a cada sincronização em `servidor_resumo.md`; foto de
23/09/2026, 143 instalações): MIX TELEMATICS (NOVO) = MIX 2.0: **82**
(Predileto 46, Mosaic 27, Logika 4…); SUNTECH: **42** (Ricker 12, Predileto 11, Faje 7…); MIX TELEMATICS
(antigo): **12**; Entrack: **5**; e 2 cadastros com uma transportadora no lugar da telemetria (erro de
cadastro). Ou seja: quando alguém diz "MiX", quase sempre é **MIX 2.0 (5)** — no Tester é `telemetry mix2`
(`telemetry mix` grava o MIX antigo, 0). Confirme pelo `telemetry_label` do cadastro antes de gravar:
aparelho em modo diferente do rastreador pede teste mas não bloqueia (chamado LUA5E58). Atenção ao nome no
Tester: em `test --telemetry mix`, "mix" é a variante MIX 2.0 do `protocol.json`.

## 2. A regra comum de ignição (todos os modos)

```
ignição ligou (borda):  se bloqueado && !dirigindo → test.start();   dirigindo = !bloqueado
ignição desligou && dirigindo:  dirigindo = false  → tempo de manobra (se estava desbloqueado)
```

Consequências práticas:
- O teste **só dispara na transição desligado→ligado** e **só se o veículo estiver bloqueado**. Se o
  aparelho ficou desbloqueado (ex.: reinícios → "Alimentação Indevida" desbloqueia; adiamento; comando
  remoto `$ETBL01!`), ligar a chave **não pede teste**.
- Ignição que "pisca" (mau contato no pós-chave, ponto de bloqueio errado) gera ligar/desligar em
  sequência: tempo de manobra no meio da viagem, novo teste, bloqueio — caso SRU4A50 (Notion).

## 3. Particularidades por modo

### MIX 1.0 (0) e MIX 2.0 (5)
- Integração por **script do módulo MiX** (configurado pela MiX — contato na `Handover.pdf`). O módulo
  precisa estar com o script certo: aparelho em MIX antigo com rastreador em MIX 2.0 → pede teste mas o
  bloqueio/desbloqueio não acontece (chamado LUA5E58: "Rafael upou o script da MIX2.0").
- Conexão física: cabo RS232 com microfit na entrada **S1** do módulo MiX (algumas instalações usam S2 —
  confirme com a MiX; trocar de entrada exige ajuste do script). Alimentação: fio vermelho/marrom na bateria.
- **Pen drive (iButton/chave azul) de identificação do motorista**: sem motorista identificado a MiX não
  libera a viagem e **não pede teste**. "No Driver" no portal da MiX = sem identificação.
- **MIX 2.0, caminhão (`vehicle_type`=0)**: a viagem só começa quando o rastreador manda `$ETEV03!`
  (veículo em movimento). Se a ignição está ligada há > 70 s, sem teste nos últimos 70 s e o veículo está
  desbloqueado **sem estar "dirigindo"**, o aparelho mostra "Tempo Esgotado" e **bloqueia sozinho**
  (`mix2/index.h`, `timeOut()`). Script que não envia `$ETEV03!` → bloqueio ~70 s depois do teste.
- **MIX 2.0, carro (`vehicle_type`=1)**: aceita `$ETEV31!` como ignição; a viagem começa quando a
  ignição liga com o veículo desbloqueado.
- MIX 1.0 força tempo de manobra de 5 min.
- **O que chega ao servidor Sighir pela MiX** (medido): testes (`$ETEV16!`), adiamentos, manobra,
  sopro etc. chegam; **resultado (`$ETEV29!`/`$ETEV30!`), `$ETEV35!` e `$ETEV24!` nunca chegaram** de
  nenhum veículo MiX; `$ETEV01!`/`$ETEV02!` dependem do script de cada rastreador. Eventos chegam em
  **lote**, com atraso de minutos a horas e ordem não confiável. Em várias empresas (Mosaic, Atvos,
  Felka, Manchur) a MiX não repassa nada para o nosso servidor: ausência de log lá não é defeito.
- Portal MiX (us.mixtelematics.com): *Rastreamento ao vivo* → placa → ⋮ → *Comandos do dispositivo
  móvel* → **Relay 1 "Ligado"** desbloqueia em pane do etilômetro; **"Desligado e solto"** volta ao
  normal. Acompanhe em *Monitorar → Fluxos* ("Concluído", ~6 min). Eventos: *Monitorar → Histórico de
  rastreamento* (filtre "Etilometro"); relatório: *Medir → Relatórios → Relatório detalhado do evento*.
  Troubleshooting de campo (`troubleshooting.md`): enviar **OFF AND RELEASED** para *Relay Driver 1 e 2*.

### Suntech (2)
- Módulo **Suntech ST8300** (manual do ST4305 em `Notion/Manual_do_usuario_ST4305-1.pdf`), plataforma
  de rastreamento SystemSat (`tracking.systemsatx.com.br`, ver `Handover.pdf`).
- Conexão: cabo RS232 com conector de **4 vias** no módulo; conector de **6 vias** alimenta a embutida a
  partir do módulo. O chicote Suntech tem **relé acoplado** que corta o fio de ignição (pinos 30 e 87a).
  Montagem do chicote: `eletrica_instalacao.md` §4.
- O etilômetro pede `SttReq` a cada 2 s; a resposta `STT;…` traz o ID do módulo (campo 1) e o estado da
  chave (campo 14 ou 19, 7º caractere). Pelo rastreador real o estado precisa se repetir (média de 4
  amostras, histerese 0,9/0,1); pela USB (bancada) 1 pacote basta.
- No boot, se o `STT;` não vem em 20 s → **"Comunicação Não Encontrada"** (tela vermelha + bipe). O
  aparelho continua, mas não vai saber da ignição.
- Tela ID pág. 2 mostra o **ID de Telemetria** lido; INFO pág. 3 "Telemetria Ativa".
- No servidor, `suntechs/<id>` tem `is_connected`, `is_ignition_on`, `is_relay_on`, `has_to_block`,
  `has_to_unblock`, `last_stt` — ótimo para saber se o módulo está vivo e o que o relé está fazendo.
- Falhas reais: **chip do módulo invertido** (sem comunicação com o servidor, mas pedia teste e
  bloqueava — "Pedro (carro)"); **módulo morto** após ~1 mês parado (RJK1D03, 2025: trocar o kit);
  **fio azul do derivador** com mau contato (ignição).
- Tudo que o aparelho emite chega ao servidor, com ~3 h de deslocamento de fuso no `timestamp − created_at`.

### Entrack (6)
- Módulo Entrack + chicote com relé (mesma lógica de corte 30/87a). Configuração do módulo pelo software
  **AOVX** (porta COM → servidor e chip → SET) — `Handover.pdf`. Chip também é registrado no cadastro.
- Ignição por acelerômetro/entrada do módulo (`+QACC`): precisa de algumas amostras seguidas (≈4 × 2 s)
  para virar "ligada". Na bancada, o Tester não simula isso (teste completo Entrack é pulado).
- Desde a 6.3.9 ("telemetria entrack funcional"). Tarefa aberta no Notion: melhorar
  bloqueio/desbloqueio Entrack (desbloqueio deve ligar independente da ordem do etilômetro).
- Chega ao servidor praticamente em tempo real (UTC).

## 4. Serial compartilhada com a USB (importante na bancada)

A classe `NextSerial` troca a porta ativa para a **USB assim que chega dado pela USB** (e volta para o
rastreador quando ele fala). Por isso, com o aparelho no USB, os pedidos periódicos da telemetria
(`SttReq`, `AT+QACC?`, `$ETACK!`, `CMD;…`) aparecem no terminal do computador — é ruído esperado, não
defeito (o Tester filtra em `Tester/utils/noise.py`). E pela mesma razão, **plugar o USB "rouba" a
conversa do rastreador** enquanto o computador estiver falando.

## 5. O que o servidor Sighir recebe de cada telemetria (janela 23/06–21/09/2026)

| Telemetria | `$ETEV16` | `$ETEV29/30` | `$ETEV01/02` | `$ETEV35` | `$ETEV24` | Atraso típico |
|---|---|---|---|---|---|---|
| Suntech | 3.242 | 2.215 / 46 | 4.268 / 4.246 | 207 | 43.254 | ~3 h (fuso) + segundos |
| Entrack | 349 | 351 / 9 | 521 / 283 | 26 | 9 | ~0 |
| MiX antigo | 221 | 0 / 0 | 209 / 97 | 0 | 0 | minutos a horas (lote) |
| MiX novo | 730 | 0 / 0 | 787 / 35 | 0 | 0 | idem |

Assinatura de cadastro errado: veículo cadastrado como Suntech com padrão da MiX (sem 29/30, sem 01/02,
entrega em lote) — o cadastro (`telemetry`) está errado (RJV1A55, 09/2026).

## 6. Diagnóstico rápido por telemetria

| Sintoma | MiX | Suntech | Entrack |
|---|---|---|---|
| Não pede teste | pen drive/motorista identificado? script certo (MIX vs MIX2)? S1/S2? chicote | "Comunicação Não Encontrada" no boot? `suntechs/<id>.is_connected`? chip? fio azul (IGN) | `AT+QACC` respondendo? módulo configurado (AOVX)? |
| Pede teste, não libera | script (MIX antigo × 2.0); Relay 1 no portal MiX; outro acessório bloqueando | autodiagnóstico → teste de relé atraca?; ligação 30/87a; saída 1 negativa | `AT+GPIOVALUE`; relé do chicote |
| Bloqueia sozinho | MIX 2.0 caminhão sem `$ETEV03!` (70 s); fim do tempo de manobra | pós-chave oscilando (bomba de combustível!); bateria | ignição média instável |
| Eventos não chegam ao portal | normal em várias empresas; lote; script | chip invertido/sem sinal; módulo morto | chip/servidor no AOVX |

Detalhe de cada caminho de diagnóstico: `diagnostico.md`.
