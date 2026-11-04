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
   bloqueados (código 2) até o aparelho estar na v6.5.3. `autodiagnostico` e `sopro` exigem a **v6.5.4**
   (`core.DIAG_FIRMWARE`): abaixo dela saem com código 2 e o relatório fica incompleto até atualizar.
3. **Atualizar** — §2.
4. **Testes de qualidade** — §3, todos, nesta ordem: `qualidade` → `autodiagnostico` → `sopro` → `sem-alcool` →
   `com-alcool`. Antes do `sopro`, confirme com o usuário o `blowProb` do protocolo (0,3 a 1,5 s). Reprovou em algo →
   mostre a tabela e pergunte se segue; não cadastre aparelho reprovado sem o "sim" dele.
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
   Diga ao usuário o veredito que o `register`/`relatorio` imprimiu e o **aviso de campo** que vem logo depois: o cadastro
   está certo e os testes da bancada valem para o etilômetro e a serial, mas o funcionamento com a telemetria é com a
   instalação (ligar no módulo, pedir um teste pela telemetria, bloquear e desbloquear, conferir se o relé comuta).

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
| autodiagnóstico (v6.5.4+) | `qualidade autodiagnostico` | "Na tela: Menu → Configurações (pág. 2) → **Autodiagnóstico** → **Diagnóstico Completo** (o botão verde). Ele roda serial, temperatura, álcool, memória e pressão sozinho (~1 min); depois pede **não sopre** (25 s), um sopro **curto** (pare quando o bipe começar) e um **contínuo até o bipe parar**; no fim, o **relé**: sem módulo na bancada toque **Não** em "Deseja Mesmo Continuar?" (fica Ignorado); com o módulo ligado toque Sim, veja se o relé comuta e responda "O Relé Comutou?". A tabela fica 6 s" — ~3 min | a linha final do aparelho (`{"diagnostic":"full",…}`): serial, temperatura, álcool, memória (EEPROM: ID `ETL` + coeficientes), pressão e sopro aprovados, com os 3 sopros classificados certo; relé aprovado **ou ignorado** (`null`: MIX, "Não" ou 20 s sem toque). O teste serial da tela passa com qualquer comando em 10 s: a CLI responde o `$ETKA!` que ele manda. Sem sensor de pressão a tela pula os sopros. Build v6.5.4 anterior a 04/11/2026 (só 4 etapas) ainda é lida: entram só as etapas que vierem |
| sem álcool | `qualidade sem-alcool [--vezes N]` | "Quando a tela pedir, sopre **sem álcool**, contínuo até o bipe parar" | `$ETEV29!` em todos |
| com álcool | `qualidade com-alcool [--vezes N]` | "Quando a tela pedir, sopre **com o álcool**; no resultado, toque em **Desligar Display**" | `$ETEV30<mg/L>!` em todos |

- **Testes de sopro** — `qualidade sopro [--blowprob X]` (firmware **v6.5.4+**). O protocolo da Sighir roda **no
  aparelho** (`TST_BLOW`), guiado pela tela, com a mesma detecção do teste real (25 s para começar; caiu antes de
  1,8 s = incompleto; 3 s de bipe = completo). A CLI grava o `blowProb` com `CF:blowProb$X!` (a v6.5.4 aplica **sem
  reiniciar**), põe `press$0` e escuta uma linha por sopro. O `blowProb` tem que estar entre **0,3 e 1,5 s** (maior =
  mais fácil): sem `--blowprob` vale o do aparelho, e fora da faixa a CLI não roda. Leva ~5 min: rode em background e
  leia a saída no fim.

  | Etapa na tela | Operador (avise antes) | Passa quando |
  |---|---|---|
  | Sem Sopro (3×) | **não** sopra durante os 25 s de cada | os 3 terminam sem sopro |
  | Sopro Incompleto Fraco, Médio e Forte (3× cada) | sopra na força pedida e **para assim que o bipe começa** | os 3 classificados como incompletos (recusados) |
  | Sopro Completo Fraco, Médio e Forte (3× cada) | sopra na força pedida, **contínuo até o bipe parar** | os 3 classificados como completos (aceitos) |

  - Cada etapa abre com a instrução e a suavização em uso (um toque começa antes dos 8 s). Cada sopro mostra o
    resultado (verde = o esperado, vermelho = não) com o **pico** e a duração. Etapa com erro pergunta "Tentar
    Novamente?" (10 s): **Sim** refaz só aquela etapa e o relatório anota `refeita N vez(es)`. No fim, a tabela
    `n/3` por etapa.
  - Cada etapa vira um ensaio (`sopro-nenhum`, `sopro-incompleto-<força>`, `sopro-completo-<força>`) com os 3 sopros
    (resultado, pico, duração em ms). Pico = maior degrau acima da linha de base do detector, na escala do `pressure`
    do `/get-data` (na bancada, um sopro subia de +12 fraco a +110 forte): confere se a força pedida foi a soprada.
  - O mesmo protocolo está no menu (Autodiagnóstico → **Teste de Sopro**) para testar sem o Tester. Sem o sensor de
    pressão (HX711) ele não roda: as 7 etapas reprovam.
  - Protocolo confirmado pelo usuário em 29/10/2026 e 03/11/2026: ajuste do `blowProb`, 3 sem soprar, 3 incompletos e
    3 completos em cada força (fraco, médio, forte).
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
- **Formato 2** (03/11/2026, protocolo de sopro no firmware) — o que muda para o Jean:
  - Os 7 ensaios de sopro têm os mesmos `id`, com `dados` = `forca` (`fraco`/`medio`/`forte` ou `null`), `esperado`
    (`nenhum`/`incompleto`/`completo`), `esperados`, `aprovados`, `repeticoes`, `blowProb` (número) e `sopros`: lista
    de `{resultado, pico, duracao_ms, ok}`. Saíram `testes`, `cortados` e `aceito`.
  - O sopro completo não passa mais pela análise de álcool: `sopro-completo-*` não tem `testes`/`curva` (as curvas
    ficam no `sem-alcool` e no `com-alcool`), e o "esperado" dele é **aceito**, não "aceito e analisado".
  - `autodiagnostico.dados.etapas` mantém `pressao`, `sopro`, `temperatura` e `sensor`; o `sopro` agora é "um sopro de
    cada tipo classificado certo". Entrou `sopros` (`{tipo, resultado, pico, duracao_ms, ok}`).
  - `sem-alcool`/`com-alcool` perderam `forca` (era sempre `null`).
- **Formato 3** (04/11/2026, autodiagnóstico em 7 etapas no firmware) — o que muda para o Jean:
  - `autodiagnostico.dados.etapas` passa a ter, na ordem da tela, `serial`, `temperatura`, `sensor`, `memoria`,
    `pressao`, `sopro` e `rele`. Cada valor é `true`/`false` ou **`null` = ignorado** (só o `rele`: MIX, ou o técnico
    pulou na bancada sem módulo) — mostrar "Ignorado", não "Reprovado". Firmware v6.5.4 anterior manda só
    `temperatura`, `sensor`, `pressao` e `sopro`: as outras chaves não vêm.
  - O critério do ensaio `autodiagnostico` mudou (texto em `quality.py` `STEPS`); `medido` = `N/M aprovados na tela`, com os
    ignorados fora da conta.

## 5. Validado na bancada (29/10/2026, aparelho de debug com build v6.5.3)

`init` (`ok`) → `qualidade` (23 s: serial, temperatura, pressão OK; sensor reprovado pelo bypass da build de
debug) → `autodiagnostico` (pressão, sopro, temperatura OK pela tela; sensor reprovado pelo bypass) →
`sem-alcool` em Suntech (`$NOBLOW!` → `$ETEV05!` → `$ETEV29!`, 48 s) → `com-alcool` (com `testalc$1`: `$ETEV30`
lido, tela da contrassenha) → `register` de aparelho já cadastrado (código 4, nada gravado) → `recover`/reset
pelo RTS. Flash pela USB com o protocolo novo: 1090 blocos, 0 reenvios, `_UPDATE_OK_`, ~290 s.
Não validado com cartucho real: `com-alcool` com álcool de verdade (a build de debug fixa o analog em 23000).

**v6.5.4 (03/11/2026, sem aparelho)**: protocolo de sopro (`TST_BLOW`), lista de testes do Autodiagnóstico e
Diagnóstico Completo com os 3 sopros — compilado e telas conferidas com as fontes do firmware nos 3 idiomas (nenhum
texto estoura a linha nem encosta em outro); a CLI testada com as linhas simuladas (`test_cli.py`).
**v6.5.4 (04/11/2026, telas refeitas)**: Diagnóstico Completo em 7 etapas na ordem deste procedimento (serial,
temperatura, álcool, memória, pressão, sopros, relé), teste serial de 10 s com a barra até 100 %, cartão de resultado
no lugar da tela verde cheia, tabela por 6 s; as telas foram renderizadas com o código real do firmware (LovyanGFX no
Linux) nos 3 idiomas e a CLI testada com as linhas novas (`test_cli.py`).
**Bancada 04/11/2026** (MIC2702031054375407, cartucho real ETL2534221559775071, Suntech, pelo DB9): `flash --arquivo`
da build Sighir publicada (md5 igual ao do servidor) a 921600 em 1 min 52 s → `qualidade` 5/5 (serial 87 ms, temperatura,
sensor `$ETEV20!`, calibração, pressão) → `qualidade autodiagnostico` 7/7 pela tela (o teste serial passou com o `$ETKA!`
que a CLI devolve; sopros nenhum/incompleto/completo classificados certo; relé com "Sim" no "O Relé Comutou?").
**Falta**: `qualidade sopro --blowprob X` (protocolo completo) com a build nova e o relé com um módulo ligado.

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
