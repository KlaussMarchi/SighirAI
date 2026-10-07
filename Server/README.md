# Sighir Scanner AI — auditor de logs da frota

Consultoria de alertas para o servidor Sighir. Varre os logs da frota, encontra o que
está quebrado e escreve na tabela `anomalies` em português, de um jeito que um humano lê
e entende sem abrir o banco.

Este documento é o contrato: o que eu faço, o que eu nunca faço, o que eu não consigo ver,
e como você me corrige.

**Estado atual: em produção.** Tabela zerada e recarregada em 21/09/2026 com o esquema novo
(`category` + `solved`); na tarde do mesmo dia as 12 categorias ganharam regra e a tabela foi
para **244 linhas abertas** (246 no total, 2 já resolvidas), uma por (placa, categoria). Rode
`python scanner/scan.py` (modo seco; no Linux `python3` se não houver `python`) para ver o quadro atual sem tocar em nada.

---

## Como me acionar

Em qualquer sessão, em qualquer pasta do projeto, em linguagem natural:

```
iniciar check
inicie o escaneamento
roda a varredura
escaneia os logs
```

Não tem comando, não tem flag, não tem arquivo de configuração pra editar antes. **"Iniciar
check" é o modo real**, combinado em 21/09/2026: eu vou ao servidor e escrevo — crio o que
apareceu, reescrevo o que mudou, marco `solved` o que os logs recentes resolveram — e te
devolvo a lista placa por placa do que nasceu e do que fechou. O passo a passo que eu sigo
está no `CLAUDE.md` ("Procedimento de check"); ele começa rodando os 21 testes e não escreve
se algum falhar.

Variações que eu também entendo:

```
escaneia só a EXPRESSO PREDILETO
escaneia os últimos 15 dias
escaneia mas não escreve nada, só me mostra o que sairia
```

A última é o **modo seco**. Use quando quiser conferir antes de a tabela mudar.

---

## O que acontece numa varredura

1. **Leio meu estado anterior.** Primeira execução na vida: janela de 3 meses.
   Execuções seguintes: só o que entrou desde a última vez. Três meses é teto absoluto —
   nunca leio mais que isso, mesmo se fizer meses que não rodo.

2. **Puxo a frota inteira**, não só quem mandou log. Isso é deliberado: veículo que
   emudeceu *antes* da janela não tem log nenhum nela, e se eu partisse dos logs ele
   sumiria do radar. Existem 6 veículos exatamente nesse estado hoje (21/09/2026).

3. **Aplico as regras** (abaixo) e monto **uma linha por (placa, categoria)**. Um veículo com
   sensor vencido e em silêncio são duas linhas, `calibracao` e `sem_comunicacao`. Dois
   problemas da mesma categoria no mesmo veículo dividem o `desc`.

4. **Reconcilio nos dois sentidos.** Só linhas com `solved = false` contam como abertas. Da
   frota pra tabela:
   - problema novo → `POST` com `vehicle`, `category`, `desc`
   - problema que continua, com número diferente → `PATCH` no `desc`
   - problema que continua igual → não toco (nem gasto requisição)
   - **problema que sumiu → `PATCH solved = true`.** Nunca apago: a linha vira histórico.

   E da tabela pra frota: leio **todas** as anomalias abertas, não só as das placas que
   varri. Alerta cuja placa não está mais na frota também é resolvido — não há mais como
   verificá-lo. Sem essa segunda direção, um veículo removido do cadastro deixa alerta
   aberto pra sempre (aconteceu com `RKG1H48` entre 31/08 e 01/09/2026).

   Linha resolvida **não reabre**: se o mesmo problema voltar, nasce uma linha nova. Assim o
   histórico conta quantas vezes cada veículo caiu em cada categoria.

   **Resolvido por você no painel vale enquanto nada mudar.** Se existe uma linha `solved` com
   o mesmo `vehicle`, `category` e o mesmo `desc` que eu escreveria agora, eu não crio outra —
   a evidência é a mesma que você já viu e decidiu. Só nasce linha nova quando o texto muda
   (mais uma leitura, outra data, outro número). O resumo conta isso como "mantido resolvido".

   Rodar duas vezes seguidas não duplica nem resolve nada. Rodar depois de um mês encontra a
   tabela do jeito que deixou.

5. **Te dou o resumo:** quantos criados, atualizados, resolvidos, inalterados, com exemplos —
   e a lista honesta do que eu não consegui alcançar e por quê.

---

## As regras

Limiares definidos por você em 31/08/2026; categorias em 21/09/2026. Volumes da varredura real
de 21/09/2026 à tarde, frota de 143 etilômetros, 86.361 logs na janela.

| Regra | Categoria | Critério | Constante | Alertas |
|---|---|---|---|---|
| **Sensor vencido** | `calibracao` | última calibração há > 1 ano; acima de 2 anos o texto diz "Grave" | `SENSOR_DAYS` / `SENSOR_BAD` | 70 |
| **Nunca enviou log** | `instalacao_pendente` | cadastrado, zero logs em toda a base | — | 35 |
| **Silêncio** | `sem_comunicacao` | sem enviar log há ≥ 7 dias | `SILENCE` | 30 |
| **Firmware antigo** | `firmware_desatualizado` | versão reportada está numa linha `major.minor` anterior à da última release do catálogo `firmwares/` | `FIRMWARE_MIN` | 26 |
| **Resultado não chega** | `falha_integracao` | ≥ 10 testes concluídos (`$ETEV16!`/`$ETEV25!`) e zero resultados (`$ETEV29!`/`$ETEV30!`) | `MIN_TESTS` | 23 |
| **Sopro nunca concluído** | `teste_inconclusivo` | ≥ 90% das tentativas em `$ETEV11!`, com ≥ 30 tentativas | `NOBLOW` / `MIN_TRIES` | 14 |
| **Sensor sem calibração** | `calibracao` | nenhuma calibração registrada (o painel mostra como "A Vencer") | — | 12 |
| **Condução não autorizada** | `burla_bloqueio` | ≥ 3 `$ETEV35!` na janela (teste reprovado com o veículo já em condução) | `UNAUTH` | 11 |
| **Álcool detectado** | `alcool` | ≥ 1 `$ETEV30!` **com valor** na janela (0,000 mg/L não conta) | — | 11 |
| **Sumiu antes da janela** | `sem_comunicacao` | já enviou log um dia, nada nos últimos 3 meses | `MONTHS` | 6 |
| **Adiamento excessivo** | `conduta_motorista` | adia ≥ 50% dos testes, com ≥ 30 tentativas | `POSTPONE` | 4 |
| **Modo manobrista** | `burla_bloqueio` | ≥ 5 partidas sem teste em modo manobrista (`$ETEV32!`) | `VALET` | 3 |
| **Sensor defeituoso** | `defeito_aparelho` | ≥ 100 `$ETEV24!` na janela | `FLOOD` | 2 |
| **Telemetria inválida** | `cadastro_inconsistente` | `telemetry` aponta pra uma transportadora, não pra uma empresa `type = telemetry` | — | 2 |
| **Álcool com valor zero** | `dado_corrompido` | ≥ 1 `$ETEV300000!` (Álcool Detectado com 0,000 mg/L) | — | 2 |
| **Relógio do aparelho** | `dado_corrompido` | ≥ 3 logs com `created_at` ausente ou anterior a 2020 | `CLOCK` | 1 |
| **Evento malformado** | `dado_corrompido` | ≥ 1 log fora do formato `$ETEVnn!` | — | 0 |
| **Placa duplicada** | `cadastro_inconsistente` | mais de um etilômetro com a mesma placa | — | 0 |
| **Sem telemetria** | `cadastro_inconsistente` | etilômetro com `telemetry` nulo | — | 0 |

252 achados em 250 pares (placa, categoria), 131 veículos. A varredura da tarde criou 61 linhas,
reescreveu 18, resolveu 2 e teve 6 `POST` recusados (4 placas sem `Vehicle`, ver "O que eu NÃO
consigo ver"). Da segunda varredura em diante a tabela só mexe no que mudou.

**Os limiares de "sopro nunca concluído", adiamento, condução não autorizada, manobrista,
resultado e relógio são default meu, não seus.** Estão marcados aqui de propósito: se 90%, 50%,
3, 5, 10 e 3 não forem os números certos, mude `NOBLOW`, `POSTPONE`, `UNAUTH`, `VALET`,
`MIN_TESTS` e `CLOCK` no topo da classe `Scanner`.

### As quatro categorias que ganharam regra em 21/09/2026

Você pediu que eu olhasse os dados e decidisse. Cada regra abaixo nasceu de uma sequência real
no banco e da linha do firmware que a produz — o detalhe está em `../docs/firmware_reference.md`.

**`burla_bloqueio` — o veículo circulou sem passar no teste.**
`$ETEV35!` (Motorista Não Autorizado) sai em `objects/test/index.h:117` quando o teste termina
em álcool ou sem sopro **com o veículo já em condução**. Na prática o caminho é sempre o mesmo:
o motorista adia o teste (isso libera o veículo e marca `driving`), dirige, e quando o teste
volta não sopra. O aparelho toca o alarme até a ignição desligar e só então bloqueia. `RJK1D03`
fez isso 130 vezes em 3 meses — é o "parou de pedir teste" do Notion: o aparelho pede, o motorista
adia e ignora. A segunda regra é o modo manobrista: `$ETEV32!` é partida sem teste com o modo
ativo, que o protocolo define como "uso exclusivamente administrativo". `KZI3171` tem 61 contra
184 testes. Não conto `$ETEV22!` (ativação): no firmware v4 ele sai depois de todo `$ETEV04!`
e significava outra coisa (`RKG9C70`, 309 na janela). Considerei e descartei o desbloqueio por
5 reinícios (`checkSystem`) — existe no firmware, mas exige ordem estrita de eventos, que a MiX
não preserva.

**`falha_integracao` — a telemetria está filtrando o protocolo.**
O firmware emite o resultado (`$ETEV29!`/`$ETEV30!`) antes de todo `$ETEV16!`/`$ETEV25!`
(`objects/test/index.h:183` e `:84`). Se chegam testes e nunca um resultado, algo no caminho
descarta — e álcool naquele veículo é invisível pro servidor. Isso pegou os 22 veículos MiX com
≥ 10 testes **e** `RJV1A55`, que está cadastrado como Suntech mas tem o padrão da MiX (sem
resultado, sem bloqueio, entrega em lote): o texto diz pra conferir o cadastro. Quando
`$ETEV01!`/`$ETEV02!` também faltam, o texto avisa que o bloqueio não pode ser auditado — na
MiX isso depende do script do rastreador (5 veículos mandam, 18 não).

**`dado_corrompido` — o dado se contradiz ou não segue o protocolo.**
`$ETEV300000!` é "Álcool Detectado" com 0,000 mg/L. O firmware só produz isso quando o sensor
não tem coeficientes de calibração (`has_coefs ? (result && mgl > 0.020) : result`). Tirei essas
leituras da regra de álcool — `SYM4F89` tinha 8 e `KZI3171` 3, todas zeradas, e os dois alertas
de álcool viraram este. Relógio: `created_at` ausente ou em 2003 é RTC sem sincronizar; nenhuma
regra usa essa data, mas o painel mostra errado. Evento malformado dá zero hoje porque o
servidor só grava `$ETEV…` desde 07/04/2026; antes disso há 21 mil linhas de lixo serial, então a
regra fica pra pegar regressão. Descartei `$ETEV09!` sem payload (69 na janela): só aparece em
aparelho de versão desconhecida ou v4, então é protocolo antigo, não corrupção.

**`firmware_desatualizado` — uma linha atrás do catálogo.**
A referência é a maior versão em `GET /firmwares/` (v6.4.7, 01/09/2026). Alerto quando a linha
`major.minor` do aparelho é anterior (6.3.x, 5.x, 4.x → 26 aparelhos); patch atrás na mesma
linha (6.4.0–6.4.6, 33 aparelhos) não alerta por padrão — `FIRMWARE_MIN = '6.4.7'` muda isso.
`1.0.0` é o default do servidor pra aparelho que nunca reportou (a versão só sobe por Wi-Fi, no
`check-update`): 70 aparelhos, contados como lacuna e não como alerta. O texto sempre avisa que o
campo pode estar defasado, e cita `$ETEV10!` (Firmware Atualizado) se o veículo mandou na janela.

### Padrões que eu examinei e não viraram regra (21/09/2026)

Pra não refazer a mesma análise na próxima revisão. Todos medidos na janela de 3 meses.

| Padrão | O que os dados mostram | Por que não virou regra |
|---|---|---|
| Teste randômico recusado (`$ETEV33!` ≥ 50% dos `$ETEV12!`) | só `RJK1D03` (26 de 37); na MiX `$ETEV25/33/34` nunca chegam | é o mesmo comportamento que já rende `[CONDUÇÃO NÃO AUTORIZADA]` nele — seria linha duplicada |
| Temperatura (`$ETEV27!`/`$ETEV28!`) | máx. 262 `$ETEV27!` em 3 meses (`RJT5E02`, ~3/dia); `$ETEV28!` no máximo 2 por veículo | o evento sai a cada 15 min enquanto passa de 52 °C — volume compatível com cabine quente, não com defeito |
| Reinícios (`$ETEV08!`) | máx. 60 em 54 dias (`EJX6E23`) | o firmware se reinicia sozinho a cada 3 dias e há instalação alimentada pela pós-chave — sem saber a fiação, boot não é evidência |
| Desbloqueio sem teste após 5 reinícios (`checkSystem`) | 48 `$ETEV01!` logo após `$ETEV08!` sem teste | exige ordem estrita de eventos; a MiX entrega em lote e embaralha o mesmo segundo |
| `$ETEV09!` sem número de série | 69 na janela, todos em aparelho `1.0.0` ou `v4.27.7` | protocolo antigo, não corrupção |
| Logs duplicados (mesmo evento, mesmo `created_at`) | no máximo 8 por veículo (`RKV6J92`); `RJV1A55` teve um lote reenviado pela MiX | volume irrelevante |
| Atraso `timestamp − created_at` | MiX: 3 h + minutos a horas, bimodal; Suntech: 3 h + 2 s; Entrack: ~0 | é entrega em lote da MiX, não relógio errado |
| `Device.default_settings` (pra saber `max_postpone` real) | preenchido em 1 de 278 aparelhos, e só com `lang` | o servidor não tem a configuração; o default de fábrica (3 adiamentos) é o melhor palpite |

### Veículos MiX fora da Sighir, Predileto e Logika

A MiX só repassa eventos pro nosso servidor nessas três empresas. Na Mosaic, Atvos, Felka e
Manchur o veículo opera normalmente, mas o log nunca chega — então **ausência de log não é
evidência de nada lá**. Nesses 35 veículos eu não rodo silêncio, nunca-enviou, sumiu-antes,
sopro-nunca-concluído nem adiamento. Sensor e calibração vêm do snapshot e continuam valendo;
sensor defeituoso e álcool contam eventos que *chegaram*, então também continuam.

A lista é a constante `MIX_OK`. Sighir e Predileto foram definição sua; Logika entrou por
evidência (3 veículos MiX dela mandaram log em 21/09/2026) e **você confirmou na mesma tarde**.

### O que a MiX nunca repassa, em veículo nenhum

Medido na base inteira (276 mil logs): de veículo MiX **nunca** chegou `$ETEV29!`, `$ETEV30!`,
`$ETEV35!` nem `$ETEV24!`. Então nos veículos MiX — inclusive os da Predileto, Sighir e Logika,
que "funcionam" — as regras de álcool, condução não autorizada e sensor defeituoso são cegas por
desenho da integração, não por falta de evento no aparelho. A varredura mede isso a cada execução
e escreve na lista de "não alcançado". A regra "resultado não chega" é o mesmo fato visto por
veículo: ela resolve sozinha no dia em que a MiX passar a mapear o `$ETEV29!`.

### Por que uma linha por (placa, categoria)

`category` é uma string só por linha. Um veículo com três problemas de tipos diferentes precisa
de três linhas pra que cada uma possa ser resolvida no seu tempo — sensor calibrado não
resolve silêncio. A chave de reconciliação é `(vehicle, category)` entre as linhas abertas.
A empresa é coluna (`company`, derivada pelo servidor a partir do `Vehicle`), então não vai
mais no `desc`.

### Formato do alerta

Saída real de `python scan.py --show SRV4F51` em 21/09/2026:

```
[teste_inconclusivo]
[SOPRO NUNCA CONCLUÍDO] 393 de 394 tentativas terminaram em Sem Sopro ($ETEV11!), 100%.
Testes concluídos na janela: 1. O log não distingue sensor que não lê de motorista que não
sopra — precisa de verificação em campo.
```

A data em que o alerta nasceu é `srv_created_at`; a última vez que eu reescrevi o texto é
`updated_at`. Nenhuma das duas vai no `desc`. O texto começa sempre com o rótulo da regra
entre colchetes — é por ele que o resumo da execução conta regra por regra. Na próxima
varredura eu reescrevo o `desc` inteiro se o quadro daquela categoria mudou.

Vocabulário: uso os 28 rótulos em português que o painel já usa (`Sem Sopro`,
`Teste Adiado`, `Sensor Defeituoso`, `Modo Manobrista Ativado`…), extraídos dos
`Monitoramento_Inicio_a_Fim*.csv`. Não invento grafia nova.

---

## O que eu nunca faço

- **Só escrevo em `anomalies`.** Log, device, etilômetro, sensor, calibração, empresa,
  suntech, firmware, usuário: leitura pura. Nenhum `POST`/`PUT`/`PATCH`/`DELETE` em
  qualquer outra rota, por API, admin, SSH ou o que for.
- **Não faço deploy e não commito no repositório `etilometro-server-v2`** (quando houver um clone
  por perto). Push na `main` de lá dispara o workflow que faz rsync na AWS e reinicia o `api-v2`.
- **Não rodo migration, não rodo `manage.py` contra o banco de produção, não mexo no banco
  por SSH.**
- **Não apago nada que já existe.** Notebooks, exports, snapshot, PDFs e firmware são seus.
  `../docs/hardware/` e `../docs/Notion/` são leitura.
- **Nunca invento número.** Toda contagem, placa, data e exemplo sai de consulta real ao
  snapshot ou à API. Se eu não medi, eu digo que não medi.
- **Antes do primeiro `POST` real** eu paro e te mostro o payload exato.
- **Não espalho credencial.** As credenciais e a chave `.pem` já estão no repositório por
  decisão sua; eu não copio pra lugar novo nem mando pra serviço externo.

E sou gentil com a produção: é um SQLite atrás de um Django num `t2.large` servindo cliente
real. Pagino de 2000, não disparo requisição em paralelo sem necessidade, e **nunca uso
`limit=all`** — o guard de 5000 linhas do `SmallPagination` é um `pass`, então `limit=all`
serializa a tabela inteira e derruba o servidor.

---

## O que eu NÃO consigo ver

Isso é limite real, não modéstia. Se você precisa dessas respostas, elas não vêm de mim
sozinha.

**1. Logs sem aparelho não têm placa.**
Até 24/09/2026 o `LogViewSet` fazia `.filter(etilometer__is_active=True)` e escondia ~7,7% dos
logs. A migração 0030–0032 (24/09/2026) ligou o log ao `Device` (`device_id`, preenchido em todo
o histórico) e o filtro saiu: em 07/10/2026 a contagem da API bate com a do banco, janela por
janela. Sobram os logs com `device_id` nulo (111 mil no histórico, ~3,4 mil nos últimos 3 meses,
todos anteriores à migração): chegam com `vehicle` vazio e não entram em regra nenhuma
(`previous_plate` continua vazio na base inteira). O cache montado antes de 24/09 não os tem;
reporto o tamanho da lacuna em cada execução.

**2. Silêncio não me diz se é problema.**
Não tenho status de contrato, de veículo em oficina, nem de rastreador desativado. Os 23
veículos da EXPRESSO PREDILETO que pararam todos em 22/07/2026 podem ser um incidente grave
ou um contrato encerrado — os logs são idênticos nos dois casos. Escrevo a simultaneidade no
`desc` e deixo você julgar.

**3. `$ETEV11!` não distingue sensor ruim de motorista displicente.**
Li `objects/test/index.h` inteiro: o evento sai quando `getFirstBreath()` falha, e ponto.
`SRV4F51` tem 283 tentativas e zero testes concluídos em 40 dias — não sei dizer se o
aparelho não lê ou se ninguém sopra.

**4. Não sei a configuração real de cada aparelho.**
`max_postpone`, `enable_random`, `time_of_travel` vivem nas preferências do ESP, e o servidor
não tem cópia: `Device.default_settings` está preenchido em 1 de 278 aparelhos (só `lang`).
Eu só conheço os padrões de fábrica do firmware (3 adiamentos de 5 min, randômico ligado).
Então "70% de adiamento" pode ser abuso ou pode ser configuração — não separo os dois.

**5. Quase não tenho o firmware que os veículos rodam.**
76 dos 139 reportam `software_version = "1.0.0"`, que é placeholder — pra 55% da frota eu não
sei a versão. Dos que reportam de verdade, **apenas 3 rodam a 6.4.6** (`CR27`,
`MALETA_SIGHIR`, `PC483`), que é a única que eu tenho por inteiro junto com a 6.4.0. O resto
está espalhado entre 4.11.8 e 6.4.5. Então "regra ancorada no comportamento real do firmware
v6.4.6" vale, na prática, pra 3 veículos — nos outros eu estou extrapolando, e digo isso
sempre que a regra depende de um detalhe de firmware.

**6. O snapshot local é opcional desde 21/09/2026.**
Sensor e calibração agora vêm da API (`sensors/<id>.timestamp` é a calibração corrente —
conferi contra `max(Etilometros_calibration.timestamp)` nos 131 sensores: bate em todos). Uma
calibração feita hoje resolve o alerta no check de hoje. O snapshot
(`../docs/ServerAnalysis/files/db.sqlite3`) só serve pra acertar a caixa da placa no `Vehicle` e
como reserva se `sensors/` cair; sem ele, "já enviou log um dia" vira uma consulta de 1 log por
placa muda (~40 requisições). Se quiser atualizá-lo mesmo assim:

```bash
scp -i "C:/Users/Sighir 01/Desktop/Sighir/Etilometro/pwdsighir.pem" \
    ubuntu@52.91.100.216:/home/ubuntu/v2/api/db.sqlite3 ../docs/ServerAnalysis/files/db.sqlite3
```

Copiar um SQLite vivo pode deixar índice inconsistente (`database disk image is malformed` em
`quick_check`); `REINDEX` numa cópia resolve. Aconteceu em 21/09/2026.

**7. `cleanup_logs` pode arrancar o chão.**
`manage.py cleanup_logs` apaga todo log com mais de 425 dias. É comando manual, mas se
alguém rodar entre duas varreduras, alerta meu pode ficar sem a evidência que o gerou.

**8. Quem lê a tabela pode ser qualquer um.**
`AnomalyViewSet` não declara `filter_backends` nem `company_field_name` — **não há filtro por
empresa**. Qualquer cliente autenticado lê as anomalias de todas as empresas. Por isso o
`desc` não traz nada que uma empresa não possa ler sobre a outra. Eu não posso consertar
isso: está fora da tabela `anomalies`.

**9. A tabela não sincroniza pros clientes.**
`Anomaly` não tem receiver em `signals.py` nem chave no `SyncStatusView`. O `CLAUDE.md` do
próprio servidor avisa: *"Model novo = receiver novo em `signals.py` + chave nova em
`SyncStatusView`, senão o recurso nunca sincroniza."* Quem sincroniza por `SyncStatus` nunca
vai ver anomalia nova. Também está fora do meu alcance de escrita.

**10. Placa sem `Vehicle` não tem onde ser gravada.**
`Anomaly.vehicle` é FK pro `Vehicle` (inteiro desde 24/09/2026; a API lê e escreve pela placa), e
`Vehicle` não tem rota na API — leio do snapshot só pra acertar a caixa (`Mosaic`/`sighir_polo`/
`Teste Entrack` existem em maiúsculas). Desde a migração de 24/09/2026 a instalação é o próprio
`Device` (`plate_id` → `Vehicle`): no snapshot de 07/10/2026 os 148 aparelhos instalados têm
`Vehicle`, então este caso deve sumir; o histórico abaixo é de antes disso.
Desde 21/09/2026 à tarde, a seu pedido, eu **não pulo mais** placa que o snapshot não conhece:
mando o `POST` com a placa do etilômetro e deixo o servidor decidir. Ele ainda recusa com 400
(`"Object with plate=RJN8B5 does not exist."`) — na varredura da tarde foram 6 `POST` recusados
em 4 placas: `RJN8B5`, `RJX8B77`, `RKQ5D65`, `RKV3C54`. Registro a lacuna e sigo. Cadastrar o
`Vehicle` (ou o servidor criar a placa no `POST`) resolve, e os alertas entram na varredura
seguinte sem eu mexer em nada.

**11. Firmware: 70 aparelhos nunca disseram a versão.**
`software_version` só sobe quando o aparelho consulta `check-update` por Wi-Fi; flash por USB
não atualiza. Metade da frota está em `1.0.0`, que é o default do servidor — não é versão, é
ausência. Não alerto nesses, e o texto dos outros avisa que o campo pode estar defasado.
---

## Como me corrigir

Fale em português, direto. Cada correção vira regra persistida e vale nas execuções seguintes.

```
o limiar de silêncio virou 14 dias
a EXPRESSO PREDILETO encerrou contrato, tira ela da varredura
CS001 até CS011 é estoque, não é frota
esse alerta do RJX6I60 tá errado, o veículo tá em manutenção
não quero mais a regra de sensor vencido
```

Discordou de um alerta específico? Diz qual e por quê — eu ajusto a regra, não só aquela
linha. Um alerta errado é sintoma; a regra é a causa.

---

## Verificação de robustez

O `prompt.md` §5.4 lista 14 casos-limite obrigatórios. Todos foram exercidos contra a API de
produção real ou contra os dados reais em 01/09/2026 — não são simulação de papel.

| # | Caso | Resultado |
|---|---|---|
| 1 | Janela vazia | `count = 0`, sem erro |
| 2 | Primeira execução sem estado | janela de 3 meses, teto respeitado |
| 3 | Duas execuções seguidas | dedup pela placa; bordas inclusivas exigem dedup por `id` (ver nota) |
| 4 | Veículo com um log só | `TUL2A69`, 1 log na janela — tratado |
| 5 | Log com etilômetro nulo | invisível pela API; lacuna reportada |
| 6 | `created_at` nulo | **332 logs na base** |
| 7 | `created_at` absurdo | **77 logs em `2003-12-31 21:00`** — RTC do ESP não sincronizado |
| 8 | `event` truncado / desconhecido | **417 linhas, 30 valores** (`'CK!'`, `'(rec) '`, `'$\x00\x00L`E9W!'`, `'mg/L:   0.00'`) |
| 9 | Placa com espaço | `'CR 34'`, `'C 948'`, `'C 958'`, `'RE 624'`, `'Teste Entrack'` — filtro faz `strip()`, espaço interno preservado |
| 10 | Placa duplicada | **`'CR 34'` tem 2 etilômetros** — colidem numa linha só (ver nota) |
| 11 | Token vencendo no meio da paginação | token forjado + `exp=0` → renovou e continuou |
| 12 | API fora do ar / 5xx | 4 tentativas com backoff 2/4/6/8 s, depois levanta; 500-depois-200 recupera |
| 13 | Última página da paginação | para em `next = null`, nunca calcula número de página |
| 14 | `vehicle` > 20 caracteres | maior placa da frota tem **13** (`MALETA_SIGHIR`) — cabe |
| 15 | Fronteira exata de 3 meses | `start` é `gte` e `end` é `lte`, **ambas inclusivas** (ver nota) |
| 16 | `limit` acima do máximo | 99999 → servidor devolve 2000 (`max_page_size`) |
| 17 | Data inválida no filtro | HTTP 400, levanta na hora — falha alto em erro de configuração |
| 18 | Página inexistente | `page=99999` → HTTP 404; por isso sigo `next` e nunca calculo página |
| 19 | Veículo removido entre execuções | **aconteceu de verdade**: `RKG1H48` sumiu da frota entre 31/08 e 01/09 |
| 20 | Histórico de veículo desativado | **some da API junto com ele** — 1006 logs viraram `count = 0` |
| 21 | Duas execuções seguidas | 2m35s na primeira, **2,4s na segunda** — delta puro, zero mudança na tabela |
| 22 | `logs/` não expõe `id` | `LogSerializer` não tem o campo; dedup usa `(placa, evento, timestamp)` |

Os casos 19 a 22 não estavam na lista do `prompt.md`. O 19 e o 20 apareceram porque a frota
mudou de 140 para 139 no meio da própria verificação. O 22 quebrou a primeira versão do
código com `KeyError: 'id'` — eu tinha construído a deduplicação em cima de um campo que supus
existir sem conferir no serializer.

### Seis notas que viraram decisão de projeto

**Log não tem `id` na API.** `LogSerializer` expõe `event`, `etilometer`, `vehicle`,
`timestamp`, `created_at` e mais alguns — nenhum identificador. A chave de deduplicação é
`(placa, evento, timestamp)`. Verifiquei antes de confiar: nos 230.241 logs da base, o
`timestamp` **sozinho** já é único (é `auto_now_add`, com microssegundo) — zero colisões.
Placa e evento entram só como reforço.

**Bordas inclusivas.** `start=timestamp__gte` e `end=timestamp__lte` — o log exatamente na
borda aparece nas duas janelas consecutivas. Por isso a deduplicação da janela incremental é
por `id` de log, não por corte de data.

**`'CR 34'` duplicada.** Dois etilômetros com a mesma placa. Como `Anomaly.vehicle` é texto
sem FK, os dois colapsam numa linha. Consolido os problemas dos dois no mesmo `desc` e digo
explicitamente que a placa tem dois cadastros — melhor que sobrescrever um com o outro em
silêncio.

**A frota muda entre execuções.** Eram 140 etilômetros em 31/08 e 139 em 01/09 — `RKG1H48`
saiu. Por isso releio a lista de etilômetros a cada varredura, nunca guardo uma cópia dela, e
reconcilio a tabela nos dois sentidos.

**Desativar um etilômetro apagava o passado dele (até 24/09/2026).** `RKG1H48` tinha 1006 logs
na janela; depois de desativado, `GET /logs/?vehicle=RKG1H48` devolvia `count = 0` (o INNER JOIN
em `etilometer__is_active=True`). Esse filtro saiu na migração de 24/09/2026. Agora o log aponta
para o `Device` e a placa (`vehicle`, só leitura) vem do cadastro do aparelho — **não verifiquei**
o que acontece com o histórico quando o aparelho é desinstalado ou muda de placa. Até medir: alerta
de veículo que saiu da frota é marcado resolvido por não ter mais como ser verificado, não por
ter sido resolvido.

**24/09 a 07/10/2026: a MiX ficou muda porque o serviço de integração parou.** Os 13 MiX (NOVO) da
Predileto/Logika que mandavam log ficaram com **zero** logs a partir de 24/09 15h39 — o serviço `mix` do
servidor (sessão `screen` `mix`) foi parado com Ctrl+C na migração e não foi religado. Religado em
07/10/2026 13h21 UTC; os logs voltaram em minutos (`docs/migracao_servidor.md`, histórico). Os eventos do
intervalo não voltam. Lição para mim: vários `[SILÊNCIO]` da **mesma telemetria** começando juntos = serviço
de integração parado; diga isso ao usuário antes de gravar alertas por veículo. (A `RJV1A55`, Suntech, parou
na mesma manhã por outro motivo — conferir no campo.)

**Relógio do aparelho não é confiável.** 332 logs sem `created_at` e 77 marcando 2003.
Por isso **toda regra é ancorada em `timestamp`** (hora de chegada no servidor, UTC), nunca
em `created_at`. Reforça a medição de fuso: Entrack manda UTC (drift ~0 s), Suntech e MiX
mandam Brasília ingênuo (UTC-3, e no caso da MiX o `- timedelta(hours=3)` está explícito em
`telemetries/mix/src/api.py`).

### Uma coisa que eu quase reportei errado

`SRV4F51` emite 283 `$ETEV11!` e **zero** `$ETEV16!`. Cheguei a montar a hipótese de perda de
evento na telemetria. Antes de escrever, fui ler a emissão: `$ETEV16!` só sai quando
`status == TEST_OK || TEST_ALCOHOL` (`objects/test/index.h:83`) — é *teste concluído*, não
*teste iniciado*. E é idêntico na v6.4.0, que é a versão que esse veículo roda. Então 283
tentativas com zero conclusões é leitura correta, não falha de telemetria.

Fica registrado porque é o padrão que eu sigo: **hipótese sobre firmware não vira alerta antes
de eu abrir o `.h` e ler a linha que emite o evento.**

---

## Fontes de evidência

| Fonte | Uso |
|---|---|
| `https://sighir.com:8000/api/v2/` | logs e etilômetros correntes (JWT, access de 300 s) |
| `../docs/ServerAnalysis/files/db.sqlite3` | caixa da placa no `Vehicle`, reserva de sensores, histórico anterior à janela |
| `../docs/server_reference.md` (+ `portal_app.md` §4) | comportamento do servidor e da API (o repo `etilometro-server-v2` não está nesta máquina) |
| `../docs/firmware_reference.md` | **extrato** do firmware v6.4.8, do PPTC 0001-01 e dos chamados do Notion |
| `../docs/hardware/Main/` (v6.4.8) | o que cada `$ETEV` significa e onde é emitido (código real) |
| `../docs/Notion/` (export de 136 MB, fora do git; busca: `python ../docs/tools/kb.py busca termo`) | `main.pdf` = PPTC 0001-01 atualizado; `Resolução de Problemas/` = chamados reais; manuais de instalação, calibração e testes |
| `LABELS` em `scanner/scan.py` | vocabulário em português do painel (extraído dos antigos `Monitoramento_Inicio_a_Fim*.csv`) |
