# Pipeline do cadastro: atualizar, testar a qualidade, cadastrar

> Vale sempre que o usuário pedir para **cadastrar** um aparelho. Versão mínima do Tester: **v6.5.3**
> (`tools/core.py` `MIN_FIRMWARE`). Firmware de referência: `Etilometro/hardware/Main` (cópia em
> `../docs/hardware/Main/`).

## 1. Ordem

1. **`init`** → firmware (com a classificação contra v6.5.3), `esp_id`, `sensor_id` e a linha `servidor:`
   (`não cadastrado → register` ou `já cadastrado: edit` — aparelho que já existe é `edit`, nunca `register`).
2. **Pergunte antes de qualquer outra coisa, numa mensagem só:**
   > "Antes do cadastro, o padrão é **atualizar o firmware e fazer todos os testes de qualidade** (serial,
   > temperatura, sensor de álcool, calibração, pressão, autodiagnóstico, sopros, teste sem e com álcool).
   > Seguimos assim, ou prefere só atualizar, só testar ou nenhum? E qual o seu **nome** para o relatório?"

   Firmware abaixo de v6.5.3 (`below_min`/`old`): a atualização é **obrigatória** — qualidade e cadastro ficam
   bloqueados (código 2) até o aparelho estar na v6.5.3.
3. **Atualizar** — §2.
4. **Testes de qualidade** — §3, todos. Reprovou em algo → mostre a tabela e pergunte se segue; não cadastre
   aparelho reprovado sem o "sim" dele.
5. **Configuração da empresa** — pergunte a empresa (liste no chat as opções que o `register` sem `--company`
   mostra) e rode `configurar --company X`: mostra cada configuração do aparelho → padrão da empresa
   (`companies/<empresa>.data.settings`) e não grava. **Pergunte se ele quer mudar alguma** (manobra, adiamento,
   câmera, telemetria, tipo de veículo…) e grave com `configurar --company X [--set chave=valor …] --yes` (grava,
   reinicia e confere). O que ele pedir vai também no `remote` do aparelho: um flash da build da empresa depois
   do cadastro reaplica os parâmetros da empresa e o `remote` volta por cima.
6. **Cadastro** (`procedimentos/cadastro.md` §6): ID do módulo e chip → `register --company X --modulo … --chip …
   --tecnico "<nome>" [--obs "…"]` → etiqueta. O `register` grava junto o **`default_settings`** (§4): a
   configuração lida do aparelho + o relatório de ensaio, e imprime o veredito. Se ele avisar que o aparelho roda
   a build de outra empresa: `flash` (build da empresa) e depois `relatorio --tecnico "<nome>" --yes` para reenviar
   o `default_settings` com o aparelho já na build final.
7. **Relatório**: o servidor gera o PDF a partir do `default_settings` e ele sai no portal (rota e botão com o Jean, time do servidor).
   Diga ao usuário o veredito que o `register`/`relatorio` imprimiu.

Aparelho já cadastrado (`edit`): passos 1–5, o `edit` que for preciso e `relatorio --tecnico "<nome>"` (mostra) →
`--yes` (PATCH do `default_settings`).

## 2. Atualizar

`flash` em background + `progresso` a cada 20 s (`procedimentos/firmware.md` §7.1). O `flash` decide sozinho:

| Situação | O que o `flash` grava |
|---|---|
| aparelho **já cadastrado** | a build da empresa dele (`media/builds/<empresa>/Main.ino.bin`), re-armando o `need_update` |
| aparelho **novo** (não está no servidor) | a build **genérica da Sighir** (`/update` com `admin_sighir`: não consulta nem mexe em nada no servidor) — o `/update` só entrega a build de uma empresa a aparelho cadastrado |
| já na versão da build **e** com a build da mesma empresa | nada (`já atualizado`, ~5 s); `--forcar` grava de novo |
| build do servidor **abaixo de v6.5.3** | nada, código 2: a versão nova ainda não foi publicada (`Etilometro/auxiliary/FirmwareBuilder`) — avise o usuário, não há como seguir |

**Aparelho novo, menos flashes:** se ele já está na v6.5.3 e o usuário pediu atualizar, deixe o flash para
**depois do `register`** (um flash só, já com a build da empresa). Abaixo da v6.5.3 não dá: flash da build
genérica antes (libera testes e cadastro) e, depois do `register`, o flash da build da empresa.

## 3. Testes de qualidade (`python tools/sighir.py qualidade [etapas] [--vezes N]`)

Cada etapa imprime `OK`/`FALHOU` com o que mediu, e o comando fecha com a tabela e `APROVADO`/`REPROVADO`
(código 0/1). Todas usam as telas de diagnóstico do próprio aparelho: as automáticas pelos `TST_*` da serial, as
com operador pelo menu e pelo teste de verdade. **Avise o que ele vai fazer ANTES de rodar** o comando (ele não vê
a saída da CLI, só a tela do aparelho).

| Etapa | Comando | Operador | Passa quando |
|---|---|---|---|
| automáticas (~40 s) | `qualidade` | nada | **serial**: `$ETKA!`→`$ETKAACK!` (latência), `$firmware!` e `/get-data`; **temperatura**: `TST_TEMP`→`tempworking` e 4 s de leituras entre -10 e 70 ºC, umidade 1–100 % (mín/média/máx); **sensor** (álcool): `TST_SENS`→`$ETEV20!`, `analog` válido (nem -1 nem 23000 fixo) e ≥ 5.000 (aquecido); **calibracao**: `coefs` do cartucho com c1–c4 > 0, calibração com até 365 dias e a curva `a·b^(cx+d)` lendo < 0,020 mg/L no ar limpo; **pressao**: `TST_PRESS`→`pressworking` e variação em repouso < 0,5 |
| autodiagnóstico | `qualidade autodiagnostico` | "Na tela: Menu → Configurações (pág. 2) → **Autodiagnóstico** → **Diagnóstico Completo**; sopre quando ela pedir" — até 4 min | a CLI escuta os vereditos da própria tela: pressão `pressworking`, sopro `pressworking`, temperatura `tempworking`, sensor `$ETEV20!` (falhas `$ERROR!`/`ERROR`/`$ETEV24!`; sem sensor de pressão a tela pula o sopro) |
| sem álcool | `qualidade sem-alcool [--vezes N]` | "Quando a tela pedir, sopre **sem álcool**, contínuo até o bipe parar" | `$ETEV29!` em todos |
| com álcool | `qualidade com-alcool [--vezes N]` | "Quando a tela pedir, sopre **com o álcool**; no resultado, toque em **Desligar Display**" | `$ETEV30<mg/L>!` em todos |

- **Testes de sopro (sensor de pressão)** — protocolo da Sighir, 3 de cada, sempre pelo teste real (a tela pede o
  sopro e a CLI escuta os eventos). Antes, ajuste a tolerância se o usuário pedir: `settings --set blowProb=X
  --restart` (X entre **0,3 e 1,5 s**: quanto maior, mais fácil o sopro; o firmware só lê no boot). O relatório
  anota o `blowProb` usado.

  | Comando | Operador (avise antes) | Passa quando |
  |---|---|---|
  | `qualidade sopro-nenhum` | **não** sopra; em cada "Tentar novamente?" toca **Não** (3 testes, ~40 s cada) | os 3 terminam em sem sopro (`$ETEV11!`) e nenhum aceita sopro |
  | `qualidade sopro-incompleto --forca fraco` (depois `medio`, `forte`) | sopra **curto** (< 1 s) 3 vezes na força pedida; depois para e toca **Não** | 3 sopros cortados (`$NOBLOW!`) e nenhum aceito (`$ETEV05!`) |
  | `qualidade sopro-completo --forca fraco` (depois `medio`, `forte`) | sopra **contínuo até o bipe parar**, sem álcool, em 3 testes | os 3 aceitos e sem álcool (`$ETEV05!` → `$ETEV29!`) |

  Protocolo confirmado pelo usuário em 29/10/2026: por força, 3 sopros incompletos (recusados) e 3 completos (aceitos).
- **Repetições só quando o usuário pedir** ("faz 3 testes sem álcool") → `--vezes 3`. Cada teste sai com
  resultado, mg/L, `analog` do teste (`last_analog`) e duração; valide com ele (ex.: os 3 com `$ETEV29!` e analog
  parecido).
- O teste completo é o de verdade: a CLI põe `press$0` (sopro real) e `testalc$0` (sem álcool forçado), dispara
  pela **ignição da telemetria configurada** (MIX/MIX 2.0 `$ETAT01!`, Suntech pacote `STT` com a chave, Entrack
  5× `+QACC:high` espaçados) e no fim desliga a ignição e manda `endTravel` (aparelho bloqueado, como no boot).
  Não muda a telemetria do aparelho.
- Durante o teste o aparelho **não lê comandos** (`serial.md` §11.2): a CLI só escuta os eventos. `$ETEV11!` =
  ninguém soprou em 25 s (a tela pergunta "Tentar novamente?": **Sim** e sopre); `$NOBLOW!` = sopro cortado
  antes de 1,8 s (o aparelho pede de novo sozinho); `$ETEV05!` = analisando (~20 s).
- Com álcool a tela abre "Contrassenha / Realizar Outro Teste / Desligar Display" e só volta a responder depois
  do toque. Por isso o aviso de tocar em **Desligar Display**: sem toque em 120 s ela cai no **teclado da
  contrassenha**, que espera para sempre e não lê a serial — o operador sai dele pela tela, ou `recover`
  (que agora reinicia pelo pino RTS quando o `$ETRS!` não é lido).
- Saiu sem resultado (`sem resultado`): o teste não disparou ou ninguém soprou. Olhe a tela (toque em "Não" no
  "Tentar novamente?") e rode `status`.

### 3.1 Reprovou? Leia as variáveis ao vivo

`python tools/sighir.py monitor [--segundos 10] [--intervalo 0.5]` — `/get-data` em tabela (temperatura,
umidade, `analog`, `filtered`, `pressure`, `driving`, `chave`) e o resumo mín/média/máx. Não grava nada.

| Sintoma no `monitor` | Causa provável |
|---|---|
| `analog` -1 | sensor fora do I2C / ADS sem resposta (cartucho mal encaixado ou sem EEPROM) |
| `analog` 23000 fixo e `sensor_id` `ETL2608402025435219`/`ETL3550904305917103` | build de **debug** (`alcohol.bypass`): o cartucho não é lido, o `TST_SENS` sempre falha (`$ETEV24!`) e o resultado de álcool não vale — **não cadastre** |
| temperatura/umidade 0, `nan` ou paradas | DHT22 (`TST_TEMP` → `ERROR`) |
| `pressure` sem variar nada ao soprar | mangueira/bocal ou HX711 (`TST_PRESS` → `$ERROR!` se não comunica). Medido na bancada: parado ~37 com deriva ~0,1; um sopro sobe de +12 (fraco) a +110 e depois o filtro passa ~4 abaixo da base |
| `pressure` andando sozinha muito | célula de carga instável (o detector de sopro do firmware trabalha sobre a linha de base) |

## 4. `default_settings`: configuração + relatório de ensaio no servidor

- Cada `flash`, `qualidade`, `configurar` e `register` anota o que fez e **as medidas** em
  `.sighir/bancada/<MIC>.json` (`tools/session.py`). Vale o que foi feito nas últimas **24 h** (resultado mais velho
  não entra) e a última rodada de cada ensaio.
- O `register --tecnico` (aparelho novo) e o `relatorio --tecnico [--yes]` (reenvio, aparelho já cadastrado) gravam
  em `Device.default_settings` o texto JSON `{"settings": {...}, "report": {...}}`:
  `settings` = configuração atual lida do aparelho (`core.DEVICE_SETTINGS`); `report` = o ensaio
  (`tools/report.py`): veredito, aparelho, ambiente, firmware, configuração alterada e os 15 ensaios com critério,
  situação, valor medido e as medidas (estatísticas, calibração, curvas dos testes reais).
- **Veredito** (os 15 ensaios e critérios em `tools/quality.py` `STEPS`): **APTO PARA PRODUÇÃO** só com todos feitos
  e aprovados, firmware no mínimo e sensor de produção; **REPROVADO — NÃO LIBERAR** com os que falharam; **ENSAIO
  INCOMPLETO — NÃO LIBERAR** com os que faltam; **ENSAIO NÃO REALIZADO** sem nenhum teste.
- O **servidor** gera o PDF a partir do `report` e o portal oferece o download: especificação, template, exemplo e
  código foram entregues ao Jean (time do servidor) em 30/10/2026 (`README.md`, `default_settings_exemplo.json`,
  `relatorio.html`, `relatorio_exemplo.pdf`). Mudou o formato do `report`: suba `VERSION` em `tools/report.py` e
  avise o Jean com o JSON novo.

## 5. Validado na bancada (29/10/2026, aparelho de debug com build v6.5.3)

`init` (`ok`) → `qualidade` (23 s: serial, temperatura, pressão OK; sensor reprovado pelo bypass da build de
debug) → `autodiagnostico` (pressão, sopro, temperatura OK pela tela; sensor reprovado pelo bypass) →
`sem-alcool` em Suntech (`$NOBLOW!` → `$ETEV05!` → `$ETEV29!`, 48 s) → `com-alcool` (com `testalc$1`: `$ETEV30`
lido, tela da contrassenha) → `register` de aparelho já cadastrado (código 4, nada gravado) → `recover`/reset
pelo RTS. Flash pela USB com o protocolo novo: 1090 blocos, 0 reenvios, `_UPDATE_OK_`, ~290 s.
Não validado com cartucho real: `com-alcool` com álcool de verdade (a build de debug fixa o analog em 23000).

## 6. Armadilhas vistas na bancada (29/10/2026)

- **Mais de uma placa USB-serial ligada** (ex.: um CH340 e um ESP32 com USB nativa): o `scan` antigo pegava a última
  porta com "usb" no nome. Agora, com mais de uma candidata, a CLI sonda cada uma com `$ETKA!` (DTR/RTS soltos, não
  reinicia) e fica com a que responde `$ETKAACK!`; se nenhuma responder (aparelho ainda no boot), tenta o CP210x.
- **Servidor fora do ar** (o hook avisa "sighir.com:8000 INACESSÍVEL"): testes e flash de aparelho novo pela build já
  baixada seguem, mas `register`, `flash` de aparelho cadastrado e o `relatorio` (gravam no servidor) não. Avise o
  usuário e não cadastre até voltar.

- **Wi-Fi ligado na bancada** (`settings wifi` = `true`): o aparelho faz `check-update` pela rede e, com
  `need_update` ligado no servidor (a publicação das builds liga para a empresa toda), **se atualiza sozinho**
  para a build de produção da empresa e aplica os parâmetros dela (telemetria, câmera…). Enquanto isso a USB
  fica muda. As chamadas HTTP do firmware também travam o loop: sync lenta (5–6 tentativas).
- **Build de produção sem cartucho válido = USB muda depois do boot**: o firmware fica preso na checagem do
  cartucho (tela de falha do sensor) antes do parser serial rodar. `recover` não adianta — encaixe o cartucho ou
  grave a build de debug pelo bootloader (`python Etilometro/hardware/Config/index.py upload`, só com o ok do
  usuário).
- O boot da v6.5.x leva ~45 s (logos, aquecimento, servidor): `robustSync` com 5–6 tentativas logo depois de um
  reset é normal.
