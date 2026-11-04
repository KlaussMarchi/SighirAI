# Operação: telas, sons e menu do etilômetro

> Fonte: firmware v6.4.8 (`device/lang/index.h` para os textos exatos em PT; `objects/test/`,
> `objects/vehicle/`, `objects/display/interface/menu/index.h`), `hardware/FIRMWARE_ETILOMETRO.md` §9–13,
> `Notion/manual_de_treinamento.pdf` (manual do motorista), PPTC 0001-01 §2.3.1.
> Use os **nomes exatos das telas** ao orientar alguém — é o que a pessoa está vendo.

## 1. Cores e sons (o que significam)

| Cor de fundo | Uso |
|---|---|
| Preta | informativo (boot, "Teste Iniciado", "Tempo de Manobra", lembrete de sensor) |
| Branca | atenção leve ("Configurando Parâmetros", "Tempo Esgotado" do MIX 2.0, aviso de sensor 2000+) |
| **Verde** | **"Veículo Desbloqueado"** (liberado) |
| **Vermelha** | **"Álcool Detectado"**, **"Veículo Bloqueado"**, falhas de sensor, sensor vencido, temperatura grave |
| Laranja | alerta: "Reiniciamentos Inesperados", "Temperatura Alta", "Umidade Alta", sensor expirando |

| Som | Frequência | Quando |
|---|---|---|
| 3 bipes curtos agudos | 2800 Hz | ligou (boot) |
| 2 bipes | 2600 Hz | fim do boot (display apaga), início do teste, "Assopre" |
| Bipe intermitente rápido | 2600 Hz | enquanto sopra (pare de ouvir = sopro caiu) |
| Bipe longo agudo (1,5 s) | 2600 Hz | desbloqueio |
| **Bipe grave (0,5 kHz)** | 500 Hz | bloqueio, erro, álcool, falhas |
| Bipes graves a cada 0,5 s sem parar | 500 Hz | **"MOTORISTA NÃO AUTORIZADO"** — até desligar a ignição |
| Bipes 800 Hz, repetidos a cada 2 s | 800 Hz | teste randômico pedido (até 3 min) |

## 2. Ligando o aparelho (boot)

1. 3 bipes, logo Sighir. Se a empresa gravada não é "sighir": tela branca **"Configurando Parâmetros"** e
   reinicia (primeira configuração).
2. **"Telemetria MIX 1.0 / MIX 2.0 / Suntech / Entrack Iniciada" + "Verificando Comunicação"**.
   - Suntech: **"Suntech Configurado" + ID** ou tela vermelha **"Comunicação Não Encontrada"** (20 s sem `STT;`).
   - Entrack: **"Entrack Configurado" + ID** ou **"Comunicação Não Encontrada"**.
3. Checagem do sensor de álcool: se o I²C não responde, fica em tela vermelha **"SENSOR COM MAU CONTATO"**
   (ADS1115 0x48) ou **"SENSOR SEM EEPROM"** (0x50) até normalizar — trava o boot nesse ponto.
4. **"Etilômetro Veicular" / "Versão: v6.4.x"** (3 s), logo do cliente.
5. Com Wi-Fi habilitado: "Conectando à Rede" → "Conectado"/"Não Conectado" (desde 04/11/2026, no "Não Conectado"
   troca o canal uma vez sozinho, "Reestabelecendo Conexão / Configurando Canal N", e tenta de novo); pode perguntar
   **"Nova Versão Disponível — Deseja Atualizar?"**.
6. Display apaga, 2 bipes. **O aparelho começa sempre BLOQUEADO.**

Se o boot não termina 5 vezes seguidas (queda de energia no meio): tela laranja **"Reiniciamentos
Inesperados"** + bipe grave, depois **"Veículo Desbloqueado"** e texto vermelho fixo **"Alimentação Indevida —
Verifique a Bateria do Veículo"** por 30 s. O aparelho **desbloqueia de propósito** e desliga o Wi-Fi —
é proteção contra defeito elétrico, mas deixa o veículo livre. Causa: bateria/alimentação/fusível.

Reinício preventivo automático: ligado há 3 dias e parado há 3 h → reinicia sozinho (normal).

## 3. O teste (ignição ligada com veículo bloqueado)

| # | Tela (texto exato) | O que acontece / o que fazer |
|---|---|---|
| 1 | **"Teste Iniciado"** + 2 bipes | a ignição foi reconhecida |
| 2 | (se sensor ≥ 1750 sopros) aviso de vida do sensor — ver §5 | |
| 3 | **"Adiamento de Emergência" / "Toque Para Adiar"** (5 s) | tocar aqui adia o teste (se ainda há adiamentos) |
| 4 | logos | |
| 5 | **"Aguardando Câmera"** (barra sobre o aviso INMETRO) | espera `camera` s; toque adia |
| 6 | **"Aquecimento Necessário"** / "Último Teste com Álcool, Aguarde…" | só após teste positivo: purga de 2–5 min |
| 7 | **"Calibrando Sensor"** (barra; número vermelho no topo) → **"Estabilizando"** | estabiliza o zero; precisa de 12 s em 100 %. Até 7 min; travou → "Calibração Congelada" e devolve um adiamento |
| 8 | **"Recalibrando Sensor"** | leitura inválida logo antes do sopro: refaz sozinho |
| 9 | **"Clique para Iniciar"** / "Iniciando em NN seg" (60 s) | tocar começa; senão começa sozinho |
| 10 | **"Assopre"** + 2 bipes | soprar forte e **contínuo** no bocal; bipe intermitente = sopro detectado. Até 25 s para começar |
| 11 | **"Sem Sopro"** + "Tentar Novamente?" (Sim/Não) | não detectou sopro em 25 s (`$ETEV11!`). Sopro que para antes de 1,8 s reinicia o sopro sozinho (`$NOBLOW!`) |
| 12 | **"Analisando"** + aviso **Portaria INMETRO Nº369** (~23 s) | não precisa mais soprar |
| 13 | resultado **"X.XXX mg/L"** (1,5 s) | |
| 14a | negativo → **"Veículo Desbloqueado"** (verde, bipe longo) | pode ligar e seguir; display apaga |
| 14b | positivo → **"Álcool Detectado"** (vermelho, bipe grave) → **"Veículo Bloqueado"** | escolhas: **"Contrassenha" / "Realizar Outro Teste" / "Desligar Display"** |

Adiamento: **"ADIANDO TESTE"**/**"Teste Adiado N/M"** → veículo liberado por `postpone_time` com **"Tempo
Restante: X"** e **"Toque para Iniciar"**; desligar a ignição por > 7 s bloqueia. Acabaram os adiamentos:
**"Limite de Adiamentos Excedido"**.

Contrassenha: a tela mostra um número (desafio); o supervisor informa a resposta, gerada pelo **app
Sighir Monitor** ("Desbloquear Veículo") para contas autorizadas. 3 tentativas; errou 3 → display apaga e
continua bloqueado. Cada tentativa gera `$ETEV40<digitado>!`; aceita → `$ETEV26!` + desbloqueio.
Procedimento administrativo — não é orientação para o motorista burlar o teste.

## 4. Durante e depois da viagem

- **Teste randômico**: 3 piscadas preto/branco **"Teste Randômico"** + bipes 800 Hz; metade de cima
  **"Iniciar Teste"**, metade de baixo **"Adiar"**; 3 min para responder (bipe a cada 2 s). Só acontece
  dirigindo e com o sensor calibrado.
- **"MOTORISTA NÃO AUTORIZADO" / "Estacione o veículo"** + alarme contínuo: teste reprovado ou sem sopro
  **com o veículo já em movimento** (normalmente depois de adiar). Toca até desligar a ignição; aí bloqueia.
  Gera `$ETEV35!`.
- Desligou a chave desbloqueado: **"Veículo Desligado"** → **"Tempo de Manobra" / "Tempo Restante: X"**
  (redesenha a cada 10 s). Religou dentro do prazo: libera sem teste. Esgotou: **"Tempo Esgotado"** →
  **"Veículo Bloqueado"**.
- MIX 2.0: ignição ligada > 70 s sem viagem e sem teste → tela branca **"Tempo Esgotado"** → bloqueia.
- **Modo manobrista**: botão no menu (se habilitado) → "Modo Manobrista Habilitado"; ao ligar a chave
  "Aguarde a Tela Verde Para Liberação" → libera sem teste (`$ETEV32!`). Desativar com a chave ligada
  inicia um teste.
- Display apaga sozinho 60 s sem toque (exceto na tela de manobra).

## 5. Vida do sensor (contador de sopros, avisado no início de cada teste)

| Sopros | Tela | Sinal | Evento |
|---|---|---|---|
| 1750–1999 | **"Lembrete de Troca de Sensor"** | preta 2 s, sem som | `$ETEV13nnnn!` |
| 2000–2249 | **"ATENÇÃO — Troca de Sensor"** | branca 4 s, sem som | `$ETEV13nnnn!` |
| 2250–2399 | **"Alerta de Sensor — Vencimento Próximo"** | laranja 6 s, 2 bipes | `$ETEV13nnnn!` |
| 2400–2500 | **"Sensor Quase Vencido — Troque o Sensor"** | vermelha 8 s, bipe de erro | `$ETEV13nnnn!` |
| > 2500 | **"Sensor Vencido — Troque o Sensor"** | vermelha, alarme 10 s + 30 s de tela travada | `$ETEV14nnnn!` |

O contador só sobe em teste **negativo**. A validade de **1 ano** da calibração **não** gera aviso no
firmware v6.4.8 (a data só aparece em ID pág. 2) — quem avisa é o portal/`anomalies` (`calibracao`).

## 6. Alertas de ambiente (só com o display apagado, 10 s)

| Tela | Condição | Evento |
|---|---|---|
| **"Temperatura Alta"** (laranja) | ≥ 52 °C (checa a cada 15 min) | `$ETEV27!` |
| **"Temperatura Grave"** (vermelha) | ≥ 60 °C | `$ETEV28!` |
| **"Sensor Defeituoso"** (vermelha) | DHT22 sem leitura válida | `$ETEV27!` |
| **"Umidade Alta"** (laranja) | ≥ 95 % | `$ETEV41!` |

No cabeçalho do menu, temperatura/umidade ficam laranja/vermelhas nos mesmos limites.

## 7. Menu (toque na tela apagada)

Tela **MENU**: botões **ID**, **INFO**, **CONFIG**, **SAIR**; "Último Teste: X mg/L"; botão do manobrista
(se habilitado); botão verde **"Desbloquear Veículo"** enquanto houver contrassenha pendente.
Setas no rodapé trocam de página.

| Página | Itens (rótulos exatos) |
|---|---|
| **ID 1** | Versão de Firmware · Número Serial (esp_id) · ID do Sensor · SSID da Rede · Senha da Rede (toque embaixo → configurar Wi-Fi pelo teclado) |
| **ID 2** | Tempo em Viagem · ID de Telemetria (Suntech/Entrack) · Data de Calibração · Mac Address · Tipo de Veículo (Caminhão/Carro) |
| **INFO 1** | Empresa – Telemetria … · Status de Viagem (Bloqueado/Desbloqueado – Dirigindo/Desligado) · Última Leitura · Tempo Ligado (+ MHz) · SSID do Roteador (a rede própria `SIGHIR - MICxxxx`) |
| **INFO 2** | Tempo de Manobra · Tempo de Câmera · Máximo de Adiamentos · Modo Randômico · Modo Manobrista |
| **INFO 3** | Tempo de Viagem (médio) · Número de Sopros · Suavização do Sopro (`blowProb`) · Telemetria Ativa/Desativada + "Time Check" · Testes por Viagem |
| **INFO 4** | Pino de Aquecimento (ligado por X) · Calibração do Sensor (zero N %) · Estabilidade do Sensor (média, erro relativo – estável/estabilizando) |
| **CONFIG 1** | Volume do Beep (−/+) · Brilho do Display (−/+) · WiFi (liga/desliga) · Reestabelecer Conexão (troca o canal) · Atualização de Firmware |
| **CONFIG 2** | Autodiagnóstico (v6.5.4: Diagnóstico Completo em destaque e a grade Serial / Temperatura / Álcool / Memória / Pressão / Sopro / Relé / Sair; v6.5: Diagnóstico Completo / Teste de Relé; v6.4: Teste de Sopro / Teste de Componentes / Teste de Relé) · Teste Alcoólico · Teste de Telemetria · Configuração Remota · Reinicio de Emergência |
| **CONFIG 3** | Mudar Idioma (PT/EN/ES — reinicia) |

Autodiagnóstico na **v6.5.4** (telas refeitas em 04/11/2026): a etiqueta azul "Teste de Componentes", o título e o
**Diagnóstico Completo** em verde na largura toda; embaixo, em duas colunas como o menu, os testes na ordem do
procedimento de qualidade do Tester (Serial, Temperatura, Álcool, Memória, Pressão, Sopro, Relé) e Sair. A lista volta
depois de cada teste; Sair ou 2 min sem toque apagam a tela. Toda tela de teste tem o mesmo cabeçalho — etiqueta azul
("Teste de Componentes", ou "Diagnóstico Completo N/7" dentro dele), o componente e o que é medido (chip, telemetria) —,
a barra de progresso até 100 % e um cartão cinza com a leitura ao vivo. O fim é um **cartão** (não mais a tela
inteira verde): verde com ✓ e "Estado Funcional", vermelho com ✗ e "Falha no Teste" ou cinza com "Ignorado", e embaixo o
valor medido; fica ~1,5 s (bipe curto) ou ~2,5 s na falha.

| Teste | O que faz | Passa quando | Serial |
|---|---|---|---|
| **Serial** | manda `$ETKA!` e a barra anda os 10 s inteiros, mesmo que o comando chegue antes; o cartão mostra ao vivo o último comando recebido (até 2 linhas) e a porta | chegou qualquer comando (módulo, Tester, telemetria) nos últimos 15 s; o cartão final mostra esse comando | `serialworking` / `$ETEV06!` + `ERROR` |
| **Temperatura** (DHT22) · **Álcool** (ADS1115) · **Pressão** (HX711) | lê 10 s com a barra (DHT a cada 2,1 s; ADS e HX711 a cada 0,5 s) | nenhuma leitura ruim duas vezes; o cartão final mostra a última leitura | `tempworking`/`ERROR` · `$ETEV20!`/`$ETEV24!` · `pressworking`/`$ERROR!` |
| **Memória** (EEPROM do cartucho, 0x50) | confere que a EEPROM responde no I2C e lê ID + calibração (~2 s) | ID `ETL` com 18+ caracteres e os 4 coeficientes > 0; o cartão mostra o ID e "Calibrado em DD/MM/AAAA" | `eepromworking` / `$ETEV24!` |
| **Sopro** | o protocolo da Sighir (3 sem soprar, 3 incompletos e 3 completos em fraco, médio e forte); cada etapa abre com a instrução e uma barra de 8 s (um toque começa antes), cada sopro termina num cartão verde/vermelho com o pico e a duração; etapa errada pergunta "Tentar Novamente?" (10 s) | a tabela final `n/3` por etapa | uma linha JSON por sopro + `{"diagnostic":"blow",…}` |
| **Relé** | aviso de bloqueio em viagem (2,5 s) → "Deseja Mesmo Continuar?" → bloqueia, desbloqueia e bloqueia pelo rastreador → "O Relé Comutou?" | o operador responde Sim. "Não" na primeira pergunta (ou 20 s sem toque) = **Ignorado**; no **MIX/MIX 2.0** o ciclo roda mas fica Ignorado ("Relé Comutado pelo Módulo MIX") | — |

**Diagnóstico Completo** (v6.5.4): as 7 etapas acima na ordem, sem parar numa falha — Serial, Temperatura, Álcool,
Memória, Pressão, um sopro de cada tipo (**não sopre** 25 s, sopro **incompleto** — pare quando o bipe começar —,
sopro **completo** até o bipe parar; pulado se a pressão falhou) e Relé —, e a **tabela por 6 s**: "Aprovado N/N" ou
"Reprovado N/M" (ignorados fora da conta) e uma linha por etapa com o selo OK (verde), Falha (vermelho) ou Ignorado
(cinza). Na serial sai `{"diagnostic":"full","serial":…,"temperature":…,"alcohol":…,"eeprom":…,"pressure":…,"blow":…,
"relay":true|false|null}` — `null` = ignorado. Leva ~2 a 3 min. Os testes de sensor sozinhos rodam o mesmo que o
`TST_*` da serial.

Autodiagnóstico na **v6.5** (`objects/diagnostic/`): **Diagnóstico Completo** roda em sequência, mesmo quando um
falha, pressão (`pressworking`/`$ERROR!`), sopro (só com o sensor de pressão ok; sopro cortado = `$NOBLOW!` e
"Tentar novamente?" por 5 s), temperatura (`tempworking`/`ERROR`) e sensor de álcool (`$ETEV20!`/`$ETEV24!`), e
fecha com a tabela azul (OK)/vermelha (Falha) por 5 s — é o que o Tester escuta em `qualidade autodiagnostico`.
Na **v6.4**: **Teste de Sopro** (sopre 3 s → "Estado Funcional"/"Falha no Teste") e **Teste de Componentes**
(pressão, temperatura, sensor de álcool: `$ETEV20!` ok / `$ETEV24!` falha). Nas duas, **Teste de Relé**
("Testando Comutação do Relé": bloqueia→desbloqueia→bloqueia — **vai bloquear o veículo**).
**Teste de Telemetria** (CONFIG 2) é o mesmo teste **Serial** do Autodiagnóstico: `$ETKA!`, a barra dos 10 s até
100 %, o último comando recebido com a porta e o cartão final (o comando inteiro em até 2 linhas, ou "Nenhum Comando
Recebido" + `$ETEV06!`). Na MiX com o pós-chave desligado o cartão começa em laranja "Ligue o Pós Chave". Até
04/11/2026 a barra parava no primeiro comando, a tela cheia mostrava só os 15 primeiros caracteres e a espera era de
15 s.

## 8. Orientações de uso (manual do motorista)

Não deixar o aparelho no sol; evitar produtos de limpeza, perfumes, sprays e desinfetantes com álcool na
cabine; não usar enxaguante bucal/spray antes do teste; evitar bala/chiclete forte (hortelã, canela) antes
do teste; se usou, esperar alguns minutos em ambiente ventilado (beber água ajuda); comunicar suspeita de
falso positivo informando o produto usado.
