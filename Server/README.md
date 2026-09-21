# Sighir Scanner AI — auditor de logs da frota

Consultoria de alertas para o servidor Sighir. Varre os logs da frota, encontra o que
está quebrado e escreve na tabela `anomalies` em português, de um jeito que um humano lê
e entende sem abrir o banco.

Este documento é o contrato: o que eu faço, o que eu nunca faço, o que eu não consigo ver,
e como você me corrige.

**Estado atual: em produção.** Primeira carga escrita em 01/09/2026 — **124 linhas** na tabela
`anomalies`, que estava vazia. Rode `python3 scanner/scan.py` (modo seco) para ver o quadro
atual sem tocar em nada.

---

## Como me acionar

Em qualquer sessão, em qualquer pasta do projeto, em linguagem natural:

```
inicie o escaneamento
roda a varredura
escaneia os logs
```

Não tem comando, não tem flag, não tem arquivo de configuração pra editar antes.

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
   sumiria do radar. Existem 7 veículos exatamente nesse estado hoje.

3. **Aplico as regras** (abaixo) e monto **uma linha por veículo**, com todos os problemas
   ativos dele dentro do `desc`.

4. **Reconcilio nos dois sentidos.** Da frota pra tabela:
   - problema novo → `POST`
   - problema que continua, com número diferente → `PATCH`
   - problema que continua igual → não toco (nem gasto requisição)
   - **problema que sumiu → `DELETE`**

   E da tabela pra frota: leio **todas** as anomalias que existem, não só as das placas que
   varri. Alerta cuja placa não está mais na frota também é `DELETE`. Sem essa segunda
   direção, um veículo removido do cadastro deixa alerta órfão pra sempre — e isso não é
   hipótese, aconteceu com `RKG1H48` entre 31/08 e 01/09/2026.

   Rodar duas vezes seguidas não duplica nem apaga nada. Rodar depois de um mês encontra a
   tabela do jeito que deixou.

5. **Te dou o resumo:** quantos criados, atualizados, apagados, ignorados, com exemplos —
   e a lista honesta do que eu não consegui alcançar e por quê.

---

## As regras

Limiares definidos por você em 31/08/2026. Volumes de uma execução real em modo seco contra a
produção em 01/09/2026, frota de 139 etilômetros, 69.743 logs na janela.

| Regra | Critério | Constante | Alertas |
|---|---|---|---|
| **Sensor vencido** | última calibração há > 1 ano; acima de 2 anos o texto diz "Grave" | `SENSOR_DAYS` / `SENSOR_BAD` | 73 |
| **Nunca enviou log** | cadastrado, zero logs em toda a base | — | 69 |
| **Silêncio** | sem enviar log há ≥ 7 dias | `SILENCE` | 40 |
| **Sensor sem calibração** | nenhuma calibração registrada (o painel mostra como "A Vencer") | — | 15 |
| **Sopro nunca concluído** | ≥ 90% das tentativas em `$ETEV11!`, com ≥ 30 tentativas | `NOBLOW` / `MIN_TRIES` | 13 |
| **Sumiu antes da janela** | já enviou log um dia, nada nos últimos 3 meses | `MONTHS` | 7 |
| **Sensor defeituoso** | ≥ 100 `$ETEV24!` na janela | `FLOOD` | 1 |
| *(nota, não é problema)* | adia ≥ 50% dos testes, com ≥ 30 tentativas | `POSTPONE` | 3 |

218 achados, **124 linhas** — porque um veículo com 3 problemas é uma linha só, não três.
124 de 139 veículos. É muito, e é assim mesmo na primeira execução: a tabela nasce vazia e
absorve todo o passivo de uma vez. Da segunda em diante ela só mexe no que mudou.

**Os limiares de "sopro nunca concluído" e de adiamento são default meu, não seus** — você não
definiu esses dois. Estão marcados aqui de propósito: se 90% e 50% não forem os números certos,
mude `NOBLOW` e `POSTPONE` no topo da classe `Scanner`.

### Por que uma linha por veículo

`Anomaly` tem três campos úteis: `vehicle`, `timestamp` (read-only, marca quando o *alerta*
foi criado — não quando o problema aconteceu) e `desc`. Sem tipo, sem status, sem empresa.
E `AnomalyViewSet` filtra por um campo só: `filterset_fields = ('vehicle',)`.

Então a placa **é** a chave natural. `GET /anomalies/?vehicle=RJX6I60` devolve 0 ou 1 linha,
e a idempotência sai de graça — sem tabela paralela de deduplicação. A data do fato e a
empresa vão dentro do `desc`, porque não há outro lugar.

### Formato do alerta

Saída real de `python3 scan.py --show RJX6I60` em 01/09/2026:

```
EXPRESSO PREDILETO · 2 problemas

[SILÊNCIO — 41 dias] Sem enviar log desde 22/07/2026 15:56. Último evento: Sem Sopro
($ETEV11!). Antes disso enviava ~13,7 logs/dia (669 na janela).

[SENSOR VENCIDO — 1 ano e 4 meses] Última calibração do sensor ETL3783901667157569 em
16/04/2025. Vencido há 4 meses (validade de 1 ano).

Obs: adia 71% dos testes (242 adiamentos contra 100 testes realizados).

— janela 03/06/2026–01/09/2026 · regras: sensor_vencido, silêncio
```

A data em que o alerta nasceu não vai no texto: ela já é a coluna `timestamp`, que é
`auto_now_add` e nunca muda. Repetir no `desc` só criaria duas versões da mesma verdade.

A última linha é técnica: é por ela que eu sei, na execução seguinte, quais regras estavam
ativas. **Não edite essa linha à mão.** O resto do texto você pode reescrever à vontade — mas
saiba que na próxima varredura eu reescrevo o `desc` inteiro se o quadro do veículo mudou.

Vocabulário: uso os 28 rótulos em português que o painel já usa (`Sem Sopro`,
`Teste Adiado`, `Sensor Defeituoso`, `Modo Manobrista Ativado`…), extraídos dos
`Monitoramento_Inicio_a_Fim*.csv`. Não invento grafia nova.

---

## O que eu nunca faço

- **Só escrevo em `anomalies`.** Log, device, etilômetro, sensor, calibração, empresa,
  suntech, firmware, usuário: leitura pura. Nenhum `POST`/`PUT`/`PATCH`/`DELETE` em
  qualquer outra rota, por API, admin, SSH ou o que for.
- **Não faço deploy e não commito em `docs/etilometro-server-v2/`.** Push na `main` de lá
  dispara o workflow que faz rsync na AWS e reinicia o `api-v2`.
- **Não rodo migration, não rodo `manage.py` contra o banco de produção, não mexo no banco
  por SSH.**
- **Não apago nada que já existe.** Notebooks, exports, snapshot, PDFs e firmware são seus.
  `docs/hardware/` e `docs/files/` são leitura.
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

**1. Logs órfãos são invisíveis pela API.**
`LogViewSet.get_queryset()` faz `.filter(etilometer__is_active=True)` — INNER JOIN. Log com
`etilometro_id` nulo simplesmente não existe pra API. No snapshot são **7,7% dos logs da
janela**; pela API, zero. E `previous_plate` está preenchido em **0 linhas** da base inteira,
então esses logs não carregam placa nenhuma — nem dá pra recuperá-los pelo nome. Reporto o
tamanho da lacuna em cada execução.

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
`max_postpone`, `enable_random`, `time_of_travel` vivem em `Device.default_settings`, por
device. Eu só li os padrões de fábrica do firmware. Então "70% de adiamento" pode ser abuso
ou pode ser configuração — não separo os dois.

**5. Quase não tenho o firmware que os veículos rodam.**
76 dos 139 reportam `software_version = "1.0.0"`, que é placeholder — pra 55% da frota eu não
sei a versão. Dos que reportam de verdade, **apenas 3 rodam a 6.4.6** (`CR27`,
`MALETA_SIGHIR`, `PC483`), que é a única que eu tenho por inteiro junto com a 6.4.0. O resto
está espalhado entre 4.11.8 e 6.4.5. Então "regra ancorada no comportamento real do firmware
v6.4.6" vale, na prática, pra 3 veículos — nos outros eu estou extrapolando, e digo isso
sempre que a regra depende de um detalhe de firmware.

**6. O snapshot local envelhece.**
`ServerAnalysis/files/db.sqlite3` é cópia manual. Sensor e calibração eu leio dele (a API não
expõe histórico de calibração); log e etilômetro eu leio da API. Se o snapshot ficar muito
velho, as regras 4 e 5 ficam velhas junto. Atualize com:

```bash
scp -i pwdsighir.pem ubuntu@52.91.100.216:/home/ubuntu/v2/api/db.sqlite3 \
    ServerAnalysis/files/db.sqlite3
```

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

**Desativar um etilômetro apaga o passado dele.** `RKG1H48` tinha 1006 logs na janela; hoje
`GET /logs/?vehicle=RKG1H48` devolve `count = 0`. É o mesmo INNER JOIN em
`etilometer__is_active=True`: some o etilômetro, some todo o histórico junto. Consequência
prática — **não dá para auditar um veículo depois que ele é desativado**, nem para saber se
o alerta que eu tinha aberto sobre ele procedia. Se você desativar um etilômetro que estava
sob alerta, o alerta é apagado por não ter mais como ser verificado, não por ter sido
resolvido.

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
| `ServerAnalysis/files/db.sqlite3` | sensores, calibrações, histórico anterior à janela |
| `docs/etilometro-server-v2/` | comportamento do servidor (código, não suposição) |
| `docs/hardware/Main/` (v6.4.6) | o que cada `$ETEV` significa e onde é emitido |
| `docs/files/Sighir_Protocol.pdf` | PPTC 0001-01, tabela canônica de eventos |
| `docs/files/Monitoramento_Inicio_a_Fim*.csv` | vocabulário em português do painel |
| `docs/files/Relatorio_Sensores*.xlsx` | critério de validade que o painel já aplica |
| `docs/ServerAnalysis/Logs.ipynb` | seus próprios critérios de descarte e inatividade |
