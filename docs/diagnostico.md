# Diagnóstico por sintoma

> Playbook de suporte do etilômetro Sighir. Cruza firmware v6.4.8, manuais (PPTC/INST), `troubleshooting.md`
> (checklists da equipe), chamados do Notion (`casos_notion.md`) e o que a API mostra.
> Para cada sintoma: **por que acontece → hipóteses em ordem de probabilidade → como descartar →
> solução → como confirmar**. Referências cruzadas: `telemetrias.md`, `eletrica_instalacao.md`,
> `operacao_telas.md`, `sensor_calibracao.md`, `comandos_config.md`, `portal_app.md`.

## 0. Antes de qualquer coisa

**Dados mínimos** (pergunte no máximo 3 coisas; se já veio, não pergunte):

1. **O que a tela mostra** (texto exato, cor) e **o que o buzzer faz**. O que a pessoa fez logo antes.
2. **Menu → ID pág. 1**: versão de firmware, número serial (`MIC…`), ID do sensor.
3. **Menu → INFO pág. 1**: empresa – telemetria (MIX 1.0/MIX 2.0/Suntech/Entrack) e Status de Viagem
   (Bloqueado/Desbloqueado – Dirigindo/Desligado); **INFO pág. 3**: Telemetria Ativa/Desativada.
4. Placa, empresa, telemetria instalada de fato, desde quando, o que já foi trocado.

**Evidência no servidor** (Helper: `python tools/helper.py veiculo PLACA` e `… logs PLACA`): último
evento e quando, sequência dos últimos testes, bloqueios/desbloqueios, `$ETEV08!` (reboots), `$ETEV24!`,
versão reportada, sensor/calibração, anomalias abertas, estado do módulo Suntech.
Lembre: na MiX resultado (`$ETEV29/30`), `$ETEV35` e `$ETEV24` **nunca chegam** e os eventos vêm em lote.

**Perfil de quem pergunta** — motorista: só ações na tela/veículo, sem abrir nada; instalador/técnico:
cabos, relé, conjunto, app, autodiagnóstico; engenheiro/N2: arquivos, eventos, NVS, comandos seriais.

**Isolamento clássico em campo**: autodiagnóstico do menu → teste de telemetria do menu → trocar
**conjunto** (exposta+embutida+espiral) → trocar **módulo de telemetria** → revisar **fiação** (VCC, GND,
pós-chave, relé 30/87a) → bancada com o Tester.

**Checklist da equipe** (Notion → Suporte → Troubleshooting, gerado em `troubleshooting.md` a cada
sincronização): é o roteiro que o suporte já usa. Siga-o no campo e use este documento para o porquê e
para as evidências.

| Sintoma aqui | Seção do `troubleshooting.md` |
|---|---|
| S1 não pede teste | Problemas de Requisição de Teste › MIX / Suntech |
| S2, S3, S4 bloqueio | Problemas de Bloqueio › MIX / Suntech |
| S6 reiniciando | Reiniciamentos Inesperados |
| S9 sopro | Problemas de Sopro |
| S10 falso positivo / álcool | Problemas de Alcool |
| S13 sem comunicação | Problemas de Comunicação › Suntech (MiX e Entrack ainda vazios no Notion) |
| S14 Wi-Fi / atualização | Problemas de Atualização |
| S16 app não conecta | Problemas de Conexão Aplicativo-Etilômetro |

---

## S1. Não pede teste ao ligar a ignição

**Por que:** o teste só dispara na **transição** da ignição para ligada, **com o veículo bloqueado e fora de
viagem**, e a ignição **vem do rastreador** (`telemetrias.md` §2).

| # | Hipótese | Como descartar | Solução |
|---|---|---|---|
| 1 | Aparelho **já estava desbloqueado** (5 reinícios → "Alimentação Indevida"; adiamento/manobra em curso; desbloqueio remoto; modo manobrista) | INFO 1 "Desbloqueado"; servidor: `$ETEV01!` recente **sem** `$ETEV16!` antes, `$ETEV08!` repetidos, `$ETEV38!`/`$ETEV32!` | desligar e esperar o tempo de manobra/bloqueio; corrigir alimentação (S6); desativar manobrista |
| 2 | **Rastreador não informa a ignição** | INFO 3 "Telemetria Desativada"; CONFIG 2 → **Teste de Telemetria** falha (`$ETEV06!`); boot mostrou "Comunicação Não Encontrada" (Suntech/Entrack) | MiX: pen drive/motorista identificado ("No Driver"?), script certo, entrada S1/S2, cabo MiX; Suntech: chip (invertido?), módulo vivo (`suntechs.is_connected`), fio azul (IGN) no derivador; Entrack: módulo configurado (AOVX). Depois: trocar cabo → módulo |
| 3 | **Telemetria configurada errada** no aparelho | INFO 1 mostra modo diferente do rastreador instalado (ex.: após `erase` virou Suntech) | ajustar `telemetry` (Tester `telemetry mix2/suntech/entrack` ou app) e reiniciar |
| 4 | Aparelho **preso em outra tela** | tela vermelha de sensor (trava o boot), contrassenha pendente, menu aberto | S7 / concluir contrassenha / sair do menu |
| 5 | Sem alimentação | display não acende ao tocar | S5 |

Confirmação: ligar a chave → "Teste Iniciado" em segundos. No app (Monitoramento de Logs) deve chegar
o comando de ignição (`$ETAT01!`/`STT;…`/`+QACC:high`).
Casos: RJK1D03/2025 (módulo Suntech morto, teste serial falhava → trocar kit), QRM8G34 (comunicação),
LUE9A29/2026 (após troca da exposta — pendente), SRQ8A62 (parou de enviar e "liga direto" — retirado).
MiX (manual INST): chave/pen drive não reconhecido → reinserir, trocar chave, trocar chicote; em último
caso desbloqueio remoto pelo portal da MiX.

## S2. Pede teste, dá negativo ("Veículo Desbloqueado"), mas o veículo não liga

**Por que:** o etilômetro só **manda a ordem**; quem libera é o rastreador/relé.

| # | Hipótese | Como descartar | Solução |
|---|---|---|---|
| 1 | Ordem não chega/não é executada pelo rastreador (script MiX errado — MIX antigo × 2.0; Suntech sem comunicação) | servidor: `$ETEV16!`/`$ETEV01!` chegam mas o relé não muda; portal da telemetria não mostra o comando; Suntech `is_relay_on` | MiX: configurar telemetria certa e pedir o script à MiX (caso **LUA5E58**); Suntech: checar `CMD;…;04;02` no app/Tester |
| 2 | Relé/fiação | CONFIG 2 → Autodiagnóstico → **Teste de Relé**: o relé atraca e o veículo alterna? (Suntech) | revisar 85/86 e o corte 30/87a; **GND → VCC → 30 → 87a**; trocar embutida → módulo → kit |
| 3 | **Outro acessório** bloqueando (outro rastreador/imobilizador) | teste com o etilômetro desbloqueando e medir se o relé comuta; bloqueio persiste → é outro sistema | pedir desbloqueio à empresa do outro sistema |
| 4 | Bloqueio nunca funcionou (instalação) | testar bloquear/desbloquear só pelo módulo de telemetria, sem o etilômetro | reinstalar o sistema de bloqueio |

## S3. Não bloqueia (liga sem teste, ou liga mesmo com álcool)

| # | Hipótese | Como descartar | Solução |
|---|---|---|---|
| 1 | Relé de bloqueio **ligado errado ou em bypass** (ou fora do pós-chave) | com "Veículo Bloqueado" na tela o veículo liga → medir o pós-chave nos pinos 30/87a | refazer o corte no **pós-chave/ignição**; nunca na bomba de combustível |
| 2 | Rastreador sem script/comando de bloqueio | portal da telemetria não mostra o comando; MiX: Relay 1 "Ligado" deixado de uma intervenção anterior | MiX: enviar "Desligado e solto" / OFF AND RELEASED (Relay Driver 1 e 2); Suntech: comando pela SystemSat |
| 3 | Aparelho desbloqueou "legitimamente" | ver S1 hipótese 1 (reinícios, adiamento, manobra, manobrista, remoto) | tratar a causa |
| 4 | Teste não é pedido | S1 | |

Pede teste mas não bloqueia depois do tempo de manobra = mesma investigação (script/relé).

**Checklist da equipe** (`troubleshooting.md` "Problemas de Bloqueio"):
- **MiX**:
  1. Conferir se o **tipo de veículo** (INFO) bate com o real: carro × caminhão explica bloqueio inesperado.
  2. Pedir à MiX (Rafael/Mauro) um script com a "viagem só inicia depois de identificar o motorista" e
     com o etilômetro atuando no **relé 2**, e não no *immobilizer*.
  3. Testar se o desbloqueio pelo portal funciona sem o etilômetro.
  4. Por último, trocar o módulo.
- **Suntech**:
  1. CONFIG 2 → Autodiagnóstico → **Teste de Relé**: o relé deve atracar repetidamente.
  2. Conferir se o relé é da **tensão do veículo** (12 ou 24 V).
  3. Conferir a fiação GND → VCC → pino 30 → 87a.
  4. Trocar, nesta ordem: relé → placa embutida → módulo Suntech → chicote Sighir → kit completo.

## S4. Bloqueia sozinho (em viagem ou logo depois de liberar)

| # | Hipótese | Evidência | Solução |
|---|---|---|---|
| 1 | **Ignição oscilando** (pós-chave com mau contato; ponto de corte na **bomba de combustível**; bateria) → o aparelho vê desligar/ligar → tempo de manobra → bloqueio | "Veículo Desligado"/"Tempo de Manobra" no meio da viagem; `$ETEV17!` `$ETEV18!` `$ETEV02!` com o veículo rodando; tela oscilando | caso **SRU4A50**: mudar o corte para a ignição, trocar o conjunto; medir o pós-chave com o veículo em marcha |
| 2 | **MIX 2.0 caminhão sem `$ETEV03!`**: ignição ligada > 70 s, sem teste e sem "viagem" → "Tempo Esgotado" e bloqueio | tela branca "Tempo Esgotado" ~70 s após o teste; nenhum `$ETEV03!` | pedir à MiX o envio de `$ETEV03!` (veículo em movimento) no script; conferir `vehicle_type` (carro não precisa) |
| 3 | Tempo de manobra curto / motorista demorou | `maneuver_time` (INFO 2) — provisionamento de fábrica usa **1 min** | ajustar pelo portal (Configurar Parâmetros) ou app |
| 4 | Teste randômico reprovado/sem sopro em viagem → "MOTORISTA NÃO AUTORIZADO" → bloqueia ao desligar | `$ETEV12!` … `$ETEV11!`/`$ETEV33!`/`$ETEV35!` | orientar motorista (S11) |
| 5 | Bloqueio remoto (portal/telemetria) | `$ETEV37!`, comando no portal | confirmar com o gestor |
| 6 | Reinício do aparelho em viagem (sempre volta bloqueado) | `$ETEV08!` no meio da viagem | S6 |

## S5. Tela apagada / aparelho não liga

1. Toque na tela: o display **apaga sozinho** em 60 s — se acende, está normal.
2. Sem resposta: **fusível** do VCC e conector de alimentação (caso **contatto**: reencaixar fusível e
   alimentação resolveu); chave geral; bateria.
3. Medir **12/24 V** na alimentação da embutida (VCC/GND); espiral encaixado dos dois lados; continuidade.
4. Display com defeito (trincado, queimado, "memória RAM ruim" — itens reais do estoque): trocar exposta.
5. Tela acesa mas travada numa mensagem: ver S7/S6.

## S6. Reiniciando / "Reiniciamentos Inesperados" / "Alimentação Indevida"

**Por que:** 5 boots incompletos seguidos → o firmware assume defeito elétrico, **desbloqueia** o veículo e
desliga o Wi-Fi. Um boot a cada ~3 dias é o reinício preventivo (normal).

| # | Hipótese | Como descartar | Solução |
|---|---|---|---|
| 1 | **Bateria fraca/viciada** — cai a tensão no pico (ligar o Wi-Fi, dar partida) | medir a bateria em carga/partida; vários `$ETEV08!` por dia | trocar a bateria (caso **LUE9A29/2025**); evitar deixar o caminhão ligado direto |
| 2 | Mau contato na alimentação (conector, espiral, fusível), GND ruim | tela oscilando; mexer no chicote reproduz | refazer conexões, trocar espiral/conjunto |
| 3 | Alimentação pelo pós-chave em vez de direto na bateria | o aparelho desliga junto com a chave | alimentar direto na bateria (com fusível) |
| 4 | Lixo serial/integração (Movieit) | reinicia com o cabo serial conectado | remover o cabo serial e pedir novo script (manual DAD01) |
| 5 | Placa com defeito | persiste com alimentação boa de bancada | trocar conjunto; bancada com o Tester |

Casos: SRU4A50, RJM4H64 (retirado), SRJ7J95 e SRO7H79 (Logika, pendentes).

**Checklist da equipe** (`troubleshooting.md` "Reiniciamentos Inesperados"):
1. Dar partida direto: depois dos reinícios, o aparelho libera o veículo.
2. **Tirar o sensor** e esperar alguns minutos.
   - Se sair da tela, recolocar o sensor.
   - Se o problema voltar com o mesmo sensor, o sensor está com defeito: trocar.
3. Carregar a bateria do caminhão (chupeta ou carregador).
4. Reapertar os fios do conjunto embutido.
5. Trocar a exposta (defeito no etilômetro) e depois a embutida (defeito no kit).

O firmware ≥ 6.0.0 mitiga o problema.

## S7. "SENSOR COM MAU CONTATO" / "SENSOR SEM EEPROM" / `$ETEV24!` / "Sensor Sem Comunicação"

**Por que:** o ADS1115 (0x48) ou a EEPROM do sensor (0x50) não respondem no I²C (pinos 18/19). O aparelho
fica nessa tela até voltar.

1. Reencaixar o sensor (tampa traseira) e o conector; "Verifique o encaixe".
2. Autodiagnóstico → Teste de Componentes (`$ETEV20!` ok / `$ETEV24!` falha); Tester `test sensor`.
3. Trocar o sensor (depois: Validar Sensor no app, `$ETEV36!`); persistindo → exposta.
4. Na base: `$ETEV24!` aos milhares em Suntech/Entrack = firmware ≤ 6.4.7 repetindo a cada 1,5 s com o
   sensor mudo (a 6.4.8 limita a 1 por 10 min) → trocar sensor e atualizar firmware.

## S8. "Calibrando Sensor" não termina / "Calibração Congelada" / "Aquecimento Necessário" demorado

- "Calibrando" é **estabilização do zero** (não é a calibração de laboratório). Precisa de erro < 0,15 %
  e 12 s estável; até 7 min. Veja **INFO pág. 4** (Estabilidade, Calibração %, Pino de Aquecimento).
- Causas: sensor **frio** (acabou de energizar, rastreador cortando a alimentação à noite, parado > 24 h),
  **ar contaminado** na cabine, temperatura alta (> 52 °C atrasa), sensor no fim da vida/descalibrado.
- "Aquecimento Necessário" após positivo é normal: 2–5 min conforme a leitura.
- Tocar na tela durante a calibração adia (se houver adiamento).
- Persistente em ambiente limpo e aparelho aquecido: trocar sensor; na bancada, `analog` estável ~20.000.

## S9. "Sem Sopro" / o sopro não é reconhecido

- Precisa começar em até 25 s e manter **≥ 1,8 s contínuos** (bipe intermitente durante o sopro).
  Orientar: bocal encaixado, soprar forte e constante até o bipe parar/tela "Analisando".
- Bocal obstruído/solto, vazamento, sensor de pressão (HX711) com defeito: Autodiagnóstico → **Teste de
  Sopro** / Teste de Componentes (pressão). `blowProb` (INFO 3 "Suavização do Sopro") muito baixo deixa o
  detector intolerante a oscilações.
- **Facilidade do sopro** (`troubleshooting.md` "Problemas de Sopro"):
  - Ajuste: `CF:blowProb$X!` pelo app ou por configuração remota.
  - `blowProb` é a tolerância do detector em **segundos**: maior = mais fácil. O padrão é 0,1, e 0 também
    vira 0,1 (`objects/sensors/pressure/index.h`).
  - A equipe usa de 0,3 a 1,5; o checklist sugere 0,5.
  - O Notion aponta "INFO pág. 2", mas na v6.4.8 o valor aparece em **INFO 3** ("Suavização do Sopro").
  - Atualizar o firmware antes de ajustar.
- Recusa sistemática em soprar (muitos `$ETEV11!` sem `$ETEV05!`): pode ser conduta — o log não distingue
  sensor ruim de motorista que não sopra (anomalia `teste_inconclusivo`) → verificação em campo.

## S10. Falso positivo / "sempre álcool"

Siga a tabela de `sensor_calibracao.md` §7 (boca, cabine, sensor frio, purga, sensor sem coeficientes,
sensor vencido, firmware de debug). Caso **RSJ5A13**: MiX cortava a alimentação do etilômetro → sensor
frio pela manhã + produto de limpeza + chiclete de menta → 0,144 e depois negativo. Na MiX o resultado
não chega ao servidor: peça foto/vídeo da tela ou use o app (Monitoramento de Logs).

**Checklist da equipe** (`troubleshooting.md` "Problemas de Alcool"):
1. Firmware atualizado.
2. **ID pág. 2 → Data de Calibração**: vazia = sensor sem calibração gerada (S18/`cf_coefs`).
3. Trocar o sensor e reiniciar: se o problema parar, era o sensor.
4. Pôr o mesmo sensor em outro aparelho: se o problema continuar, é o aparelho ou a versão.
5. Conferir no app de calibração se a curva do sensor faz sentido.

## S11. "MOTORISTA NÃO AUTORIZADO" / muitos `$ETEV35!`

Teste reprovado ou sem sopro **com o veículo já em viagem** — quase sempre depois de **adiar**
(`$ETEV15!` → dirigiu → não soprou no retorno do teste). Alarme até desligar a ignição e então bloqueia.
Não é defeito: é conduta (anomalia `burla_bloqueio`). Orientar o gestor; revisar `max_postpone`/
`postpone_time`. Caso **RJK1D03/2026** ("parou de pedir teste"): na verdade pede, o motorista adia e ignora.

## S12. Pede vários testes seguidos / pede de novo logo depois de liberar

1. Ignição oscilando (S4 hip. 1) → cada religada fora do tempo de manobra pede teste.
2. **Cabo de comunicação da MiX** com problema (manual INST §6.3–6.4) → trocar o cabo; testar com
   RS232/USB + Tester (`$ETAT01!` deve gerar **um** teste).
3. Teste anterior não concluiu (sem sopro → "Tentar Novamente?"), recalibração automática.
4. Randômico: `number_of_tests` > 1 ou viagem longa (normal).

## S13. Eventos não chegam ao portal / veículo "sem comunicação"

1. **Telemetria MiX em empresa que não repassa** (Mosaic, Atvos, Felka, Manchur): normal; e MiX nunca
   repassa resultado/`$ETEV35`/`$ETEV24`.
2. Atraso de lote na MiX (minutos a horas) — espere/compare com o portal da MiX.
3. Suntech: chip (invertido, sem crédito/sinal — caso "Pedro (carro)"), módulo desconectado
   (`suntechs/<id>.is_connected`), IP/porta; SystemSat Debug mostra os pacotes.
   Checklist da equipe:
   - pedir o **padrão de piscar dos dois LEDs** do módulo energizado;
   - mau contato nos fios de comunicação, em especial o **fio azul do cabo Suntech no derivador**
     (apertar, tirar e recolocar; registrar se voltar);
   - energização do conjunto;
   - trocar o kit Suntech e depois o kit do etilômetro.
4. Aparelho mudo de fato: sem alimentação (S5), reiniciando (S6), telemetria desativada (INFO 3).
5. Cadastro: placa diferente entre o etilômetro e o `Vehicle`, etilômetro inativo, telemetria errada
   no cadastro (assinatura MiX num cadastro Suntech) — logs órfãos não aparecem na API.
6. Veículo parado/retirado (Notion "RETIRADO"). A anomalia `sem_comunicacao` dispara com ≥ 7 dias sem log.

## S14. Wi-Fi não conecta / atualização falha / versão errada no portal

(`troubleshooting.md` "Problemas de Atualização")
1. CONFIG 1: **WiFi ligado** (seta verde); ícone de Wi-Fi no cabeçalho sem risco.
2. ID pág. 1 "SSID da Rede"/"Senha da Rede" = uma rede **2,4 GHz** disponível **com internet** (hotspot
   do celular em 2,4 GHz serve). Sem caracteres especiais. Toque embaixo da ID pág. 1 para editar.
3. **"Reestabelecer Conexão"** (troca o canal; tentar até 3 vezes).
4. Servidor: `need_update=true` no device (portal Software / Tester re-arma) — o `/update` é one-shot.
5. "Falha no Update"/"sem resposta do servidor": repetir com rede melhor; pela USB use o Tester `flash`.
6. Versão no portal defasada/`1.0.0`: normal sem Wi-Fi (só o check-update informa). Confirmar na ID pág. 1.
7. Do checklist da equipe:
   - aparelho **habilitado para atualização** (`need_update`, com Klauss ou Jean);
   - CONFIG 2 → **Reinício de Emergência** e tentar de novo;
   - conectado e ainda falha → pedir vídeo do processo;
   - versões antigas: SSID e senha pelo app, conectado ao Wi-Fi do aparelho (`Sighir - MIC…`).

## S15. Contrassenha não aceita

- A resposta depende do desafio mostrado **agora** na tela (muda a cada tentativa); o app gera a
  contrassenha a partir do número digitado nele. Conferir que foi usado o desafio atual e todos os dígitos.
- Máximo 3 tentativas; depois o display apaga e segue bloqueado — "Realizar Outro Teste" é a outra saída.
- `$ETEV40<digitado>!` mostra o que foi digitado (Suntech/Entrack). Liberação administrativa: portal
  (desbloqueio remoto) com autorização do gestor.

## S16. App não conecta ao etilômetro

1. Wi-Fi do aparelho ligado (CONFIG 1) e visível como `SIGHIR - MICxxxx` (senha `12345678`).
2. Celular recusando rede sem internet: desativar dados móveis/"alternar rede automaticamente" ou usar
   outro aparelho (Android recomendado).
3. "Reestabelecer Conexão"; o Wi-Fi dorme após 5 min de display apagado — toque na tela.
4. Ícone de Wi-Fi do app com cadeado = sem conexão com o aparelho.

## S17. Temperatura/umidade (telas laranja/vermelhas, `$ETEV27/28/41`)

≥ 52 °C alerta, ≥ 60 °C grave, ≥ 95 % umidade. Sol direto no painel, aparelho perto de fonte de calor,
cabine fechada ao sol. Mudar a exposta de lugar/proteger do sol; direcionar ventilação. "Sensor
Defeituoso" em vermelho no ambiente = DHT22 sem leitura (troca da exposta se persistir).

## S18. Sensor vencido / expirando / "Sensores Vencidos" no portal

- Tela de sopros (1.750+) → programar troca; > 2.500 → trocar já (`sensor_calibracao.md` §6).
- Calibração > 1 ano (portal/anomalia `calibracao`): recalibrar ou trocar o sensor; sensor sem calibração
  registrada aparece "A Vencer" no painel.

## S19. Cadastro/portal inconsistente

| Situação | O que fazer |
|---|---|
| Placa sem `Vehicle` (anomalia recusada com 400) | cadastrar o veículo |
| Placa duplicada (dois etilômetros ativos) | desativar/remover a instalação antiga |
| Telemetria do cadastro ≠ instalada | corrigir o `telemetry` do etilômetro no servidor |
| `software_version` 1.0.0/defasado | normal sem Wi-Fi; corrigir após confirmar na tela (PATCH) |
| Device com `admin_sighir` | fazer `erase` no Tester para regenerar o `MIC…` antes de cadastrar |
| Sensor `ETL3550904305917103`/`ETL2608402025435219` | firmware de debug: não cadastrar, regravar firmware |

---

## Categorias da tabela `anomalies` (Server/Scanner) → onde investigar

| Categoria | Significa | Seção |
|---|---|---|
| `sem_comunicacao` | ≥ 7 dias sem log / sumiu antes da janela | S13, S5, S6 |
| `instalacao_pendente` | cadastrado e nunca mandou log | S13; pode ser estoque |
| `calibracao` | calibração > 1 ano (Grave > 2) ou sem calibração | S18 |
| `defeito_aparelho` | ≥ 100 `$ETEV24!` | S7 |
| `teste_inconclusivo` | ≥ 90 % sem sopro | S9 |
| `alcool` | álcool detectado com valor | conduta + S10 se contestado |
| `conduta_motorista` | adia ≥ 50 % | S11 |
| `burla_bloqueio` | `$ETEV35!` ≥ 3 / manobrista ≥ 5 partidas | S11 |
| `falha_integracao` | testes chegam, resultado não | `telemetrias.md` §5 (normal na MiX) |
| `dado_corrompido` | `$ETEV300000!`, relógio, evento malformado | sensor sem coeficientes / RTC |
| `firmware_desatualizado` | linha major.minor antiga | S14 (OTA/Tester) |
| `cadastro_inconsistente` | telemetria inválida/placa duplicada | S19 |

## Escalar para a engenharia — o que levar

Placa, empresa, `MIC…`, `ETL…`, versão (ID 1), telemetria (INFO 1), foto/vídeo da tela e do
comportamento, horário exato, o que já foi trocado/testado, trecho de eventos do servidor
(`helper.py logs PLACA --dias N`), e se possível os eventos pela USB/app. Registre o chamado no Notion
(Resolução de Problemas) — o Helper gera o texto pronto (`helper.py chamado`).

## Limites

Não orientar a burlar o bloqueio, simular sopro, forçar resultado ou usar modos de debug em operação
(`bypass`, `alcohol_debug`, `/NPTEST`, `/ALCTEST`, `press$1`, `testalc$1` são só de bancada e devem ser
desligados). Troca de coeficientes, `erase_sensor` e recalibração são metrologia (manual de calibração).
