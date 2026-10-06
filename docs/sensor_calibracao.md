# Sensor de álcool, sopro e calibração

> Fontes: firmware v6.4.8 (`objects/sensors/alcohol/*`, `objects/sensors/pressure/*`, `objects/test/*`),
> `hardware/FIRMWARE_ETILOMETRO.md` §8–9, `Notion/Procedimento_de_Calibrao___Sighir.pdf` (PPTC 0001-01),
> `Notion/Procedimento_de_Calibrao_Tcnico.pdf` (PPTC 0001-02), manual do motorista, chamado RSJ5A13, API.

## 1. O sensor

- Sensor **semicondutor** de álcool lido por um **ADS1115** (I²C `0x48`, canal AIN1) e aquecido por um
  resistor (GPIO 0, ativo em LOW). No módulo do sensor há uma **EEPROM I²C `0x50`** com:

| Offset | Conteúdo |
|---|---|
| 0–18 | ID do sensor `ETL…` (19 chars) |
| 19–169 | JSON `{"c1":a,"c2":b,"c3":c,"c4":d,"timestamp":"…","zero":N};` — coeficientes, data da calibração, zero |
| 210–219 | contador de sopros `" $NNNN!"` |

- Leitura bruta (`analog`): **~20.000+ com ar limpo e sensor aquecido** (o "zero"); o valor **cai** com
  álcool. Abaixo de 1.000 = leitura inválida; abaixo de 5.000 = sensor não pronto.
- Sem ADS1115 → tela **"SENSOR COM MAU CONTATO"**; sem EEPROM → **"SENSOR SEM EEPROM"** (+ `$ETEV24!`,
  no máx. 1 a cada 10 min na v6.4.8; versões ≤ 6.4.7 repetem a cada ~1,5 s e inundam o log).

## 2. Como o teste decide

1. **Estabilização do zero** ("Calibrando Sensor" — não confundir com a calibração de laboratório): 20
   leituras a cada 500 ms; estável quando o erro-padrão relativo < 0,15 % (média > 5.000) ou média > 20.000.
   Precisa ficar **12 s em 100 %** ("Estabilizando"). Até **7 min**; se não estabiliza → "Calibração
   Congelada", devolve um adiamento. Display apagado aquece menos: o zero usa `média − 1500`.
2. **Preparação**: leitura instantânea precisa ser > 5.000 e próxima do zero (diferença < 2.500) — senão
   **"Recalibrando Sensor"** e o teste recomeça.
3. **Sopro** (sensor de pressão HX711 + modelo *random forest* de 55 árvores): até **25 s** para começar;
   depois **3 s** de janela com pelo menos **1,8 s contínuos**. Tolerância a falhas curtas =
   `blowProb` (padrão 0,1 → 100 ms; INFO 3 "Suavização do Sopro"). Sopro fraco/intermitente = "Sem Sopro"
   ou recomeço automático (`$NOBLOW!`).
4. **Análise** (~23 s, 47 amostras a 500 ms): uma *random forest* de 544 árvores olha a **forma da curva**
   (queda, derivada, amplitude…) e diz "tem álcool?" (limiar 0,7427). A concentração vem da curva de
   calibração da EEPROM: **mg/L = a · b^(c·x + d)** aplicada ao mínimo da curva (limitada a 2,5; < 0,010 → 0).
5. **Regra final**: com coeficientes válidos → álcool = modelo diz sim **e** mg/L > 0,020. Sem coeficientes
   (EEPROM sem calibração) → só o modelo decide, e o resultado sai como **`$ETEV300000!` (0,000 mg/L)** —
   dado de sensor sem calibração, não leitura real.
6. Após positivo: **purga obrigatória** ("Aquecimento Necessário") conforme o último analógico:
   < 7.000 → 5 min; < 15.000 → 4 min; < 17.000 → 3 min; senão 2 min.

## 3. Aquecimento (por que o 1º teste do dia é mais lento/instável)

O aquecedor fica **sempre ligado** nos 10 min após o boot, com display ligado, dirigindo e até 10 min após
mudar a ignição. Parado: ciclo 5 min liga / 2 min desliga; parado há > 24 h: 15 min liga / 60 min desliga.
Se o aparelho ficou **sem energia** (rastreador cortando a alimentação, chave geral desligada), o sensor
esfria: o primeiro teste demora a estabilizar e pode dar instável/falso positivo. Caso **RSJ5A13
(08/2025)**: a MiX desligava o etilômetro à noite (8 h sem energia) → positivo de 0,144 e negativo logo
depois; somado a produtos de limpeza e chiclete forte na cabine.

## 4. Vida útil e validade

- **Sopros**: contador na EEPROM, sobe só em teste negativo; avisos a partir de 1.750; **vencido acima de
  2.500** (telas em `operacao_telas.md` §5; eventos `$ETEV13nnnn!`/`$ETEV14nnnn!`).
- **Calibração**: validade de **365 dias** a partir da última calibração (PPTC 0001-02 §6.1). O firmware
  mostra a data (ID pág. 2) mas **não avisa** por data; quem acompanha é o portal (menu Controle →
  "Sensores Vencidos") e a tabela `anomalies` (categoria `calibracao`: > 1 ano; "Grave" > 2 anos).
  O manual PPTC 0001-01 diz que o firmware avisa no vencimento — na v6.4.8 isso não existe (só o aviso por sopros).
- No servidor: `sensors/<ETL…>` → `timestamp` = data da calibração corrente, `solution`, `analog`, `mgl`,
  `current_calibration`; `calibrations/` guarda cada ponto medido (analog, mgl, solução, nº).

## 5. Calibração de laboratório (resumo PPTC 0001-01/02)

- Feita **com o sensor já montado** no etilômetro final (captura trilhas, invólucro, fluxo no bocal).
- Bancada com gás de referência e software desktop de aquisição (serial): **purga com ar sintético** →
  **injeção** da solução certificada com vazão controlada → espera o transiente → grava janela estável →
  indexa pelo ID do sensor. Níveis típicos: **0,000 / 0,150 / 0,300 mg/L**, com réplicas.
- Padrões: **D'Quim** (INMETRO, U = 0,0088 mg/L, k = 2), **Guth Laboratories** (±3 %, retangular),
  **ACMA** (sem incerteza declarada). Soluções no estoque: Guth 0,02/0,05/0,10 mg/L, INMETRO 0,1994 /
  0,3189 / 0,4185 mg/L, 0,04 mg/L.
- Filtro de outliers (t de Student, ~5 %), ajuste **Levenberg-Marquardt** de `f(x)=a·b^(cx+d)`; qualidade
  por R², RMSE, MAE e erro máximo (exemplo: R² 99,98 %, RMSE 0,0015 mg/L). Compare **curvas**, não
  coeficientes (várias combinações de a,b,c,d dão a mesma curva). Sensor fora do limite é descartado.
- Incerteza (GUM): Tipo A (repetibilidade) + Tipo B (padrão) (+ ajuste por *bootstrap*), U = 2·uc.
- Coeficientes + zero gravados na EEPROM (comando `cf_coefs$…!`, que grava ID+JSON a partir do offset 0);
  validação com checagens; certificado emitido (baixável no portal: Relatórios → Calibração).

## 6. Troca de sensor em campo

1. Abrir a tampa traseira da exposta, retirar o sensor, encaixar o novo.
2. Conectar no Wi-Fi do etilômetro, app **Sighir Monitor** → Configurações → **Troca de Sensor de
   álcool / Validar Sensor**: o ID novo aparece → **Submeter**.
3. Quando o aparelho reiniciar, **Enviar** (já **fora** do Wi-Fi do etilômetro, com internet) → "Concluído".
4. No boot, ID diferente do anterior → evento **`$ETEV36<novo id>!`** (Sensor Substituído) e o
   `sensor_id` das configurações é atualizado.
5. Confira: ID pág. 1 (ID do Sensor), ID pág. 2 (Data de Calibração), um teste negativo completo.

## 7. Falso positivo / "sempre álcool" — como separar as causas

| Hipótese | Como confirmar | Ação |
|---|---|---|
| Resíduo na boca (enxaguante, spray, bala/chiclete forte, energético) | repetir após 5–10 min e um copo d'água | orientar; registrar o produto |
| Ambiente contaminado (produto de limpeza, perfume, álcool gel) | cheiro na cabine; positivo baixo e errático | ventilar, remover produtos |
| Sensor frio/instável (ficou sem energia, parado > 24 h) | INFO pág. 4 "Estabilidade" estabilizando; `Tempo Ligado` curto; primeiro teste do dia | esperar estabilizar; corrigir a alimentação (rastreador desligando o etilômetro) |
| Purga incompleta após positivo | "Aquecimento Necessário" pulado/interrompido | esperar a purga |
| Sensor sem coeficientes | resultados `$ETEV300000!` (0,000 mg/L "com álcool") | recalibrar/regravar coeficientes (metrologia) |
| Sensor vencido/deriva | sopros > 2.500 ou calibração > 1 ano; zero (`analog`) baixo | trocar/recalibrar sensor |
| Firmware de debug (`alcohol_debug`) | **todo** teste positivo; `sensor_id` falso (`ETL3550904305917103` / `ETL2608402025435219`) e `analog` fixo 23000 | regravar firmware de produção |

## 8. Comandos seriais do sensor (bancada — use o Tester)

| Comando | Resposta | Cuidado |
|---|---|---|
| `analog` | leitura bruta atual | — |
| `last_analog` | analógico do último teste | — |
| `sensor_id` | relê a EEPROM (ID real) | `ID:sensor_id$` devolve o valor salvo no NVS, que pode estar defasado |
| `coefs` | JSON dos coeficientes | — |
| `cf_coefs$<ID+JSON>!` | `success`/`error` | **metrologia**: sobrescreve ID e coeficientes |
| `erase_sensor` | `success`/`error` | **apaga 256 bytes da EEPROM (ID, coeficientes, sopros) — irreversível** |
| `calibrate` | dados do teste (modo coleta) | teste sem bloquear e sem eventos |
| `TST_SENS` | `$ETEV20!` ok / `$ETEV24!` falha | resposta pode levar ~10 s |
