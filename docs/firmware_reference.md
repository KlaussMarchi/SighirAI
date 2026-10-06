# Referência do etilômetro: eventos, fluxos e o que cada telemetria repassa

Extraído em 21/09/2026 (para o Scanner, útil a todas as IAs) destas fontes:

| Fonte | Onde está | O que deu |
|---|---|---|
| Firmware ESP32 (`Main.ino` diz `v6.4.8`) | `hardware/Main/` nesta pasta (cópia do repo git do firmware, commit `488260b`) | linha exata que emite cada evento, máquina de estados do teste, defaults de configuração |
| PPTC 0001-01 — *Protocolo de Comunicação DAD01* | `docs/Notion/main.pdf` (export do Notion, ignorado no git) | tabela canônica dos `$ETEVnn!`, fluxos em MIX 2.0, estágios de vencimento por sopros |
| Notion → *Resolução de Problemas* (18 chamados) | `docs/Notion/Resolução de Problemas/` | como cada tipo de defeito aparece na prática |
| Banco (`Etilometros_log`, 276 mil linhas em 21/09/2026) | `docs/ServerAnalysis/files/db.sqlite3` | o que cada telemetria **de fato** repassa ao servidor |

Tudo aqui foi lido no código ou medido no banco. Onde é inferência, está escrito "inferência".
Os caminhos de código são relativos a `hardware/Main/`.

---

## 1. Como o aparelho funciona (o mínimo)

O etilômetro é um ESP32 ligado por RS232 (115200 bps) a um **rastreador** (Suntech, MiX, Entrack).
Ele não tem internet própria em operação: todo evento `$ETEVnn!` sai pela serial, o rastreador
repassa pro servidor da telemetria, e a integração da telemetria (`telemetries/*` no servidor
Django) grava em `Etilometros_log`. Wi-Fi só é usado em bancada/instalação (`wifi = false` de
fábrica) — e é a **única** hora em que o aparelho reporta a versão de firmware ao servidor (§6).

Estados do veículo (`objects/vehicle/index.h`): `blocked` (relé cortando a partida), `driving`
(viagem em curso, habilita teste randômico), `ignition.on`. O aparelho **começa bloqueado** a cada
boot (`vehicle.setup()`: `blocked = true`).

Quem executa o bloqueio depende do modo (`telemetry` na configuração, `globals/constants.h`):

| `telemetry` | Modo | Ignição vem de | Bloqueio executado por |
|---|---|---|---|
| 0 | MIX (antigo) | comando serial `$ETAT01!` / `$ETEV04!` | rastreador, ao receber `$ETBL010000!`/`$ETBL020000!` |
| 2 | SUNTECH (default de fábrica) | resposta ao `SttReq` a cada 2 s (campo `key` do STT) | relé do aparelho + `CMD;<id>;04;01` (bloq) / `;04;02` (desbloq) pro módulo |
| 5 | MIX 2.0 | `$ETAT01!` (caminhão) ou `$ETEV31!` (carro), `$ETEV03!` marca viagem | rastreador |
| 6 | ENTRACK | `AT+QACC?` a cada 2 s (`+QACC:high/low`, média móvel de 4) | `AT+GPIOVALUE=0,1` (bloq) / `0,0` (desbloq) |

`vehicle_type`: 0 = caminhão (viagem começa no `$ETEV03!`), 1 = carro (viagem começa quando a
ignição liga com o veículo desbloqueado; aceita `$ETEV31!` como ignição).

---

## 2. Tabela de eventos

Coluna **Emissão** = arquivo:linha no firmware v6.4.8. **Chega na MiX?** = medido no banco inteiro
(nenhuma ocorrência em veículo MiX = "não"). Suntech e Entrack repassam tudo que o aparelho emite.

| Evento | Rótulo do painel | Emissão | Quando | Chega na MiX? |
|---|---|---|---|---|
| `$ETEV01!` | Veículo Desbloqueado | `objects/vehicle/index.h:96` | sempre logo após `$ETBL010000!`: teste sem álcool, contrassenha, adiamento, manobrista, `$ETBL01!` remoto, 5 reinícios (§5) | depende do script do rastreador (§4) |
| `$ETEV02!` | Veículo Bloqueado | `vehicle/index.h:72` | após `$ETBL020000!`: álcool, sem sopro em condução, fim do tempo de manobra, 70 s de ignição sem teste (MIX 2.0), `$ETBL02!` remoto | depende do script |
| `$ETEV03!` | Veículo ligado | **rastreador → aparelho** (`telemetry/modes/mix2/index.h:58`) | comando do rastreador; em caminhão marca `driving = true` | não é logado |
| `$ETEV04!` | Veículo desligado | **rastreador → aparelho** (`mix2/index.h:52`) | ignição estágio zero; encerra viagem, inicia tempo de manobra | sim, 1.746 na janela |
| `$ETEV05!` | Sopro Realizado | `objects/test/index.h:245` | sopro contínuo de 3 s com pressão; início da análise (~25 s), **não é resultado** | sim |
| `$ETEV06!` | Falha de Comunicação | `objects/diagnostic/index.h:63` | menu de diagnóstico: rastreador não respondeu `$ETKA!` em 15 s | — (0 na base) |
| `$ETEV07!` | Parâmetros Atualizados | `objects/server/updater/index.h:123` | configuração baixada do servidor por Wi-Fi | — |
| `$ETEV08!` | Dispositivo Inicializado | `objects/telemetry/index.h:59` | boot: serial aberta e modo de telemetria carregado | sim |
| `$ETEV09<id>!` | Sensor Inicializado | `objects/sensors/alcohol/index.h:55` | sensor achado no I2C; payload = 19 chars do nº de série. **Firmware antigo emite sem payload** (`$ETEV09!`: só em aparelhos `1.0.0`/`v4.27.7`) | sim |
| `$ETEV10!` | Firmware Atualizado | `server/updater/index.h:195` | OTA concluído (Wi-Fi); reinicia em seguida | sim |
| `$ETEV11!` | Sem Sopro | `test/index.h:208` | `getFirstBreath()` falhou na janela de espera. Motorista pode repetir; se recusar, teste encerra sem resultado | sim |
| `$ETEV12!` | Teste Randômico | `test/randomic/index.h:80` | solicitação em condução (`enable_random`); reenviado a cada nova solicitação | sim |
| `$ETEV13nnnn!` | Sensor Quase Vencido | `sensors/alcohol/storage/blows/index.h:85-108` | contador de sopros em 1750–2500; payload = contador com 4 dígitos | 0 na base (só a partir de 6.4.7, inferência) |
| `$ETEV14nnnn!` | Sensor Vencido (sopros) | `blows/index.h:116` | contador acima de 2500 | 0 na base |
| `$ETEV15!` | Teste Adiado | `test/postpone/index.h:46` | motorista adiou (até `max_postpone`); **`$ETEV01!` sai ~1 s ANTES** deste evento, e `forceDriving(true)` marca o veículo em condução | sim |
| `$ETEV16!` | Teste Realizado | `test/index.h:84` | teste de ignição concluído (com ou sem álcool), após o resultado | sim |
| `$ETEV17!` | Início do Tempo de Manobra | `vehicle/maneuver/index.h:60` **e** `telemetry/protocol/index.h:69` | ignição desligou com veículo desbloqueado — **e também é a resposta a todo `$ETKA!` do rastreador**, por isso é o evento mais comum na MiX | sim |
| `$ETEV18!` | Fim do Tempo de Manobra | `maneuver/index.h:141` | `maneuver_time` esgotou sem religar; segue `$ETEV02!` | depende do script |
| `$ETEV20!` | Sensor Próximo do Vencimento | `diagnostic/index.h:128` | só como resultado positivo do autodiagnóstico do sensor (menu) | — |
| `$ETEV22!` | Modo Manobrista Ativado | `vehicle/valet/index.h:30` | ativado no menu. **Em v4.27.7 sai logo após cada `$ETEV04!`** (RKG9C70: 309 na janela) — significava outra coisa no firmware antigo, não use pra contar manobrista | sim |
| `!ETEV23$` | Modo Manobrista Desativado | `valet/index.h:30` | delimitadores **invertidos de propósito no firmware**; o servidor descarta (não começa com `$ETEV`) | não |
| `$ETEV24!` | Sensor Defeituoso | `sensors/alcohol/index.h:122,131` | EEPROM/sensor não responde no I2C. v6.4.8 limita a 1 evento a cada 10 min (`EVENT_MIN_INTERVAL`, commit `5ffff50` de 16/09/2026, posterior à v6.4.7 do catálogo); **até a 6.4.7 emite a cada iteração (~1,5 s)** — daí TUI6C37 com 20 mil na janela | **não** |
| `$ETEV25!` | Teste Randômico Realizado | `test/index.h:84` | substitui `$ETEV16!` quando o teste é randômico | sim |
| `$ETEV26!` | Código Inserido (Contrassenha Aceita) | `test/pass/index.h:109` | contrassenha validada: libera, descarta o álcool, `$ETEV01!` em seguida | sim |
| `$ETEV27!` | Temperatura Alta | `sensors/dht/index.h:68,73` | > 52 °C ou sensor de temperatura mudo; no máx. a cada 15 min | sim |
| `$ETEV28!` | Temperatura Crítica | `dht/index.h:71` | > 60 °C | sim |
| `$ETEV29!` | Leitura Sem Álcool | `test/index.h:183` | resultado; antecede `$ETEV16!`/`$ETEV25!` | **não** |
| `$ETEV30mgl!` | Álcool Detectado | `test/index.h:183` | payload = mg/L × 1000 com 4 dígitos (`$ETEV300021!` = 0,021). **`$ETEV300000!` = 0,000 mg/L**: só acontece quando o sensor não tem coeficientes (`test/index.h`: `has_coefs ? (result && mgl > 0.020) : result`) | **não** |
| `$ETEV31!` | Ignição em Veículo Leve | **rastreador → aparelho** (`mix2/index.h:46`) | aceito só com `vehicle_type = 1`. Na base aparece em Suntech v4 (RKG9C70) — semântica antiga desconhecida | — |
| `$ETEV32!` | Desbloqueio em Modo Manobrista | `valet/index.h:59` | ignição ligada com manobrista ativo: **partida sem teste** | sim |
| `$ETEV33!` | Teste Randômico Não Realizado | `test/index.h:215` | randômico sem sopro e motorista recusou repetir; logo após `$ETEV11!` | sim |
| `$ETEV34!` | Teste Randômico Adiado | `postpone/index.h:46` | adiamento do randômico (`rand_ppn_time`) | sim |
| `$ETEV35!` | Motorista Não Autorizado | `test/index.h:117` | `(TEST_ALCOHOL \|\| TEST_BLOW_TIMEOUT) && driving && !pass.liberated`: teste reprovado **com o veículo já em condução**. Alarme sonoro até a ignição desligar (`alertDriver()`), e só então `block()`. Na prática vem quase sempre depois de um `$ETEV15!` (adiou → dirigiu → não soprou) | **não** |
| `$ETEV36<id>!` | Sensor Substituído | `sensors/alcohol/storage/index.h:47` | nº de série no boot difere do último gravado | sim |
| `$ETEV37!` / `$ETEV38!` | Bloqueio / Desbloqueio Remoto | **servidor** (portal) | o firmware não emite; o PPTC marca como reservado | sim (10 cada na janela) |
| `$ETEV40cod!` | Contrassenha Digitada | `pass/index.h:64,87` | cada tentativa (máx. 3) antes da validação | sim |
| `$ETEV41!` | Umidade Alta | `dht/index.h:91` | > 95 % (não está no PPTC) | — |

Mensagens de controle que o servidor **não grava desde 07/04/2026** (último log não-`$ETEV` na base):
`$ETBL010000!`/`$ETBL020000!` (ordem de desbloqueio/bloqueio ao rastreador), `$NOBLOW!` (sopro
interrompido antes de 1,8 s, reinicia sozinho), `$ETACK!` (keep-alive do aparelho a cada 5 min),
`$ETKAACK!`/`$ETATACK!`/`$ETEVACK!` (ACKs), `ON`/`OFF` (viagem forçada), `CMD;…`/`AT+…` (comandos
ao módulo). Antes dessa data há 21 mil linhas assim, inclusive lixo de serial (`'CK!'`, `'(rec) '`,
`'$\x00\x00L`E9W!'`) — é por isso que a regra de evento malformado hoje dá zero.

---

## 3. Fluxos (ordem em que os eventos chegam)

**Boot:** `$ETEV08!` → `$ETEV09<id>!` → `$ETEV36<id>!` (só se o sensor mudou). Se o contador de
reinícios (`reset` nas preferências) chegou a 5 antes de completar o setup, `checkSystem()` chama
`vehicle.unblock()` → `$ETBL010000!` + `$ETEV01!` **sem teste**, com a mensagem "Alimentação
Indevida — Verifique a Bateria" (`device/tasks/index.h:39`). É a defesa contra bateria ruim dos
chamados do Notion, mas também libera o veículo.

**Teste na ignição:** ignição liga (`blocked && !driving`) → `test.start()` → `$ETEV13/14!` se o
sensor está na faixa de aviso → `$ETEV24!` se o sensor não responde → aquecimento; um toque na tela
adia: `$ETBL010000!`, `$ETEV01!`, `$ETEV15!` e `forceDriving(true)` → senão `$ETEV11!` (sem sopro) ou
`$ETEV05!` (sopro válido) → `$ETEV29!`/`$ETEV30mgl!` → `$ETEV16!` → sem álcool: `$ETBL010000!`
+ `$ETEV01!`; com álcool: `$ETBL020000!` + `$ETEV02!` + tela de contrassenha.

**Adiamento e o `$ETEV35!`:** depois de adiar, o veículo está liberado e `driving = true`. Quando o
prazo (`postpone_time`, default 5 min) vence, o teste volta. Se o motorista não sopra
(`TEST_BLOW_TIMEOUT`) ou tem álcool, cai em `$ETEV35!` + alarme até desligar a ignição + `$ETEV02!`.
Sequência real (RJK1D03, 126 vezes na janela): `$ETEV01! $ETEV15! … $ETEV11! $ETEV35! … $ETEV02!`.

**Contrassenha** (`test/pass/index.h`): desafio de 4 dígitos na tela; resposta esperada é
`2·senha + 3` (ou variações com um dígito extra — `check()`). Com `bypass = true`, digitar `5`
libera. Cada tentativa gera `$ETEV40cod!`; aceita gera `$ETEV26!` + `$ETEV01!` e apaga o álcool
(`had_alcohol = false`).

**Teste randômico** (`enable_random`, default true, só em condução e com sensor calibrado):
`$ETEV12!` (3 min pra responder) → `$ETEV34!` se adiar → mesmas etapas do teste, com `$ETEV25!` no
lugar de `$ETEV16!` → `$ETEV11!` + `$ETEV33!` se recusar repetir → `$ETEV35!` se reprovar em condução.

**Desligamento:** `$ETEV04!` do rastreador (ou ignição pelo hardware) → `$ETEV17!` se estava
desbloqueado (inicia `maneuver_time`, default 5 min; MIX antigo força 5) → religou dentro do prazo:
`$ETEV01!` sem teste (`maneuver/index.h:97`) → prazo esgotou: `$ETEV18!` + `$ETEV02!`.

**Auto-bloqueio (MIX 2.0):** ignição ligada há mais de 70 s, sem teste no mesmo intervalo e
veículo desbloqueado sem viagem → `$ETEV02!` (`mix2/index.h:82`).

**Auto-reinício:** ligado há 3 dias, 3 h sem teste, sem viagem, 3 h sem manobrista → `ESP.restart()`
(`device/tasks/index.h:55`). Um `$ETEV08!` a cada ~3 dias é normal, não é defeito.

---

## 4. O que cada telemetria repassa (medido na janela 23/06–21/09/2026)

| Telemetria | `$ETEV16` | `$ETEV29/30` | `$ETEV01/02` | `$ETEV35` | `$ETEV24` | Atraso `timestamp − created_at` |
|---|---|---|---|---|---|---|
| Suntech | 3.242 | 2.215 / 46 | 4.268 / 4.246 | 207 | 43.254 | ~3 h 00 min 02 s (BRT ingênuo + entrega imediata) |
| Entrack | 349 | 351 / 9 | 521 / 283 | 26 | 9 | ~0 (manda UTC) |
| MiX (antigo) | 221 | **0 / 0** | 209 / 97 | **0** | **0** | 3 h + minutos a horas (lote) |
| MiX (novo) | 730 | **0 / 0** | 787 / 35 | **0** | **0** | idem |

Consequências para o scanner:

- **Na MiX, álcool é invisível.** `$ETEV29!`/`$ETEV30!` nunca chegaram de nenhum veículo MiX, em
  toda a base. `$ETEV35!` e `$ETEV24!` também não. A regra `alcool` só enxerga Suntech e Entrack.
- **`$ETEV01!`/`$ETEV02!` na MiX dependem do rastreador.** PPQ9017, RJM1B06, RJT9G28, SRA4H41 e
  SRV9I49 mandam; os outros 18 veículos MiX da Predileto não mandam nada de bloqueio. É configuração
  por rastreador (script da MiX), não do aparelho — chamado LUA5E58 no Notion: "configurado para MIX
  antigo, falha só na parte do bloqueio; Rafael upou o script da MIX2.0".
- **Ordem dos eventos não é confiável na MiX.** Chegam em lote, `created_at` é a hora do aparelho
  (BRT) e vários eventos partilham o mesmo segundo. Regra que depende de "A antes de B" só funciona
  em Suntech/Entrack. Por isso o scanner conta eventos e olha uma vizinhança de ±6, nunca exige
  ordem estrita.
- **Assinatura de telemetria.** Veículo cadastrado como Suntech mas com o padrão da MiX (sem
  29/30, sem 01/02, entrega em lote) é cadastro errado: RJV1A55 em 21/09/2026.
- **Logs órfãos** (`etilometro_id` nulo, 4.793 na janela = 5 %): a integração recebeu evento de um
  rastreador que não bate com nenhum etilômetro ativo. A API não os expõe.

---

## 5. Configurações que mudam o significado de um alerta

Defaults de fábrica em `device/settings/index.h:44-71`. O valor real de cada aparelho está em
`Device.default_settings` no servidor, que o scanner **não lê** — então "70 % de adiamento" pode
ser abuso ou pode ser `max_postpone` alto.

| Chave | Default | Efeito |
|---|---|---|
| `telemetry` | 2 (Suntech) | modo da §1 |
| `vehicle_type` | 0 (caminhão) | quando a viagem começa; carro aceita `$ETEV31!` |
| `max_postpone` | 3 | adiamentos por teste; 0 vira 1 se `enable_random` |
| `postpone_time` | 5 min | quanto o veículo fica liberado após adiar |
| `enable_random` | true | testes randômicos em viagem |
| `rand_ppn_time` / `rand_min_time` | 5 / 2 min | adiamento do randômico / mínimo antes do primeiro |
| `time_of_travel` / `number_of_tests` | 10 / 1 | duração média da viagem e nº de randômicos nela |
| `maneuver_time` | 5 min | tolerância pra religar sem teste |
| `valet` | (ausente = false) | habilita o botão de modo manobrista no menu |
| `bypass` | false | contrassenha vira "5" |
| `wifi` | false | sem Wi-Fi não há `check-update` → versão nunca reportada |
| `reset` | 0 | contador de reinícios; ≥ 5 libera o veículo no boot |

---

## 6. Versão de firmware: o que o servidor sabe

- `Device.software_version` só muda quando o aparelho chama
  `GET api/v2/devices/check-update/?id=…&sensor_id=…&firmware=…` (`server/updater/index.h:51`),
  por Wi-Fi, a cada 30 min enquanto conectado. Flash por USB **não** atualiza o campo.
- Default do servidor é `1.0.0` = "nunca reportou". Em 21/09/2026: 70 de 139 aparelhos.
- Catálogo `GET /api/v2/firmwares/` (8 releases): v4.25.12, v4.27.0, v5.0.0, v5.3.0, v6.3.9
  (12/05/2026), v6.4.2 (07/07/2026), **v6.4.7 (01/09/2026)**. O repo está em v6.4.8 e um aparelho
  (RJT5E02) já reporta 6.4.8. O catálogo pode ficar atrás do binário servido em `/update`.
- `$ETEV10!` (Firmware Atualizado) na janela prova que houve OTA — e OTA implica Wi-Fi, logo o
  campo foi atualizado junto.
- O que muda entre linhas, pelo `desc` do catálogo: 6.3.9 trouxe "telemetria entrack funcional";
  6.4.2 "sensor trocado enviado por telemetria" (`$ETEV36`); 6.4.7 "protocolo atualizado e robusto,
  melhoria de detecção do sopro".

---

## 7. Chamados reais do Notion e o que aparece no log

| Chamado (placa, data) | Causa encontrada | Assinatura no log | Categoria |
|---|---|---|---|
| LUA5E58, 08/2025 — pede teste mas não bloqueia | aparelho em MIX antigo, rastreador em MIX 2.0 | testes chegam, `$ETEV01/02` não | `falha_integracao` |
| SRU4A50, 08/2025 — bloqueia em viagem + tempo de manobra | ponto de bloqueio na bomba de combustível (sinal pós-chave ruim) | `$ETEV17!`/`$ETEV02!` no meio da viagem | `defeito_aparelho` (elétrico) |
| LUE9A29, 08/2025 — reiniciando, não deixa testar | bateria viciada; ao ligar Wi-Fi a corrente cai | vários `$ETEV08!` por dia, `$ETEV01!` sem teste após 5 reinícios | `defeito_aparelho` |
| RSJ5A13, 08/2025 — falsos positivos (0,144 e depois negativo) | MiX desligava o aparelho; sensor frio e descalibrado + produtos de limpeza/chiclete | `$ETEV30` seguido de `$ETEV29` em minutos | `calibracao` |
| RJK1D03, 08/2025 — não pede teste | módulo Suntech morto | silêncio total | `sem_comunicacao` |
| "Pedro (carro)", 09/2025 — sem comunicação | chip invertido no módulo | pedia teste e bloqueava, nada chegava | `sem_comunicacao` |
| RJK1D03, 04/2026 — "parou de pedir teste" | (pendente) | na janela: 130 `$ETEV35!` após adiar — o aparelho pede, o motorista adia e ignora | `burla_bloqueio` |
| SRQ8A62, 11/2026 — parou de enviar, liga direto | retirado | silêncio a partir de uma data | `sem_comunicacao` |
| contatto, 08/2026 — tela apagada | fusível/alimentação | boot após silêncio | `defeito_aparelho` |

Tipos de problema usados no Notion: Comunicação, Elétrico, Funcionamento, Não identificado,
RETIRADO. "Retirado" é um veículo que saiu de operação — no scanner vira silêncio e o alerta é
resolvido quando o etilômetro é desativado.

---

## 8. Documentos do Notion que ainda não foram usados

Ficam em `docs/Notion/` (136 MB, fora do git). Os que podem render regra depois:

- `Procedimento_Padro_Testes_funcionais__Sighir.pdf` — bancada: resistência do cabo espiral,
  reguladores, API de testes (`TST_TEMP`, `TST_SENS`, `TST_PRESS` do `protocol/index.h`).
- `Procedimento_de_Calibrao_Tcnico.pdf` (PPTC 0001-02) — modelo `a·b^(cx+d)`, incerteza; explica o
  `$ETEV300000!` (sensor sem coeficientes).
- `Procedimento_Padro_de_Instalao__Sighir.pdf` + `Procedimento_de_Instalao_{MIX,Suntech,Entrack}.pdf`
  — onde pegar ignição e bloqueio; o chamado SRU4A50 é o que acontece quando se ignora.
- `main 1.pdf` (MUAM 0001-01, app mobile) e `main 2.pdf` (MUWP 0001-01, portal web) — o que o
  cliente vê; o portal filtra anomalias por "tipo de problema" (`category`).
- `Handover.pdf` — contatos e logins das integrações (MiX, SystemSat, Movieit, Entrack). Contém
  credenciais em texto claro; não copiar.
- `Controle de entradas e saídas/` e `Estoque Sighir - Duque de Caxias/` — estoque de conjuntos
  (`MIC…` + `ETL…`): cruzar com `instalacao_pendente` diria se um cadastro sem log é estoque.
