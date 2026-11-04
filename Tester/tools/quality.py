import re, json, math, statistics
from time import sleep, time
from datetime import datetime, timedelta
from tools import core
from tools.core import device, log
from tools.session import record

STT_KEY = 'STT;0360000001;3FFFFF;36;1.0.14;1;20161117;08:37:39;0000004F;450;0;0014;20;+37.479323;_______{}___;0;65.43;10;1;00000101;00001000;1;2;0492'

# IGNIÇÃO DE CADA TELEMETRIA (CÓDIGO DA SETTING telemetry): O TESTE COMPLETO SÓ DISPARA NA TRANSIÇÃO DESLIGADA → LIGADA
IGNITION = {
    '0': {'on': ['$ETAT01!'], 'off': ['$ETEV04!']},
    '5': {'on': ['$ETAT01!'], 'off': ['$ETEV04!']},
    '2': {'on': [STT_KEY.format(1)]*5, 'off': [STT_KEY.format(0)]*5},      # PELO DB9 (PORTA 2) VALE A MÉDIA DAS 4 ÚLTIMAS > 0,90
    '6': {'on': ['+QACC:high']*5, 'off': ['+QACC:low']*5}                 # MÉDIA DAS 4 ÚLTIMAS AMOSTRAS > 0,75 LIGA
}

# DIAGNÓSTICO DO FIRMWARE: COMANDO, RESPOSTA OK E RESPOSTA DE FALHA
DIAGNOSTICS = {
    'temperatura': ('TST_TEMP', 'tempworking', 'ERROR'),
    'sensor': ('TST_SENS', '$ETEV20!', '$ETEV24!'),
    'pressao': ('TST_PRESS', 'pressworking', '$ERROR!')
}

RESULTS    = {'none': 'nenhum', 'cut': 'incompleto', 'full': 'completo'}    # TIPO DO SOPRO NA LINHA DO FIRMWARE
FORCES     = {'weak': ('fraco', 'fraco'), 'medium': ('medio', 'médio'), 'strong': ('forte', 'forte')}    # FORÇA NA LINHA → ID E NOME NO ENSAIO
OUTCOMES   = {'none': 'sem sopro', 'cut': 'recusados como incompletos', 'full': 'aceitos como completos'}
DIAGNOSTIC = {'serial': 'serial', 'temperature': 'temperatura', 'alcohol': 'sensor', 'eeprom': 'memoria', 'pressure': 'pressao', 'blow': 'sopro', 'relay': 'rele'}    # LINHA FINAL DO DIAGNÓSTICO COMPLETO, NA ORDEM DA TELA
VERDICTS   = {True: 'OK', False: 'FALHOU', None: 'IGNORADO'}    # ETAPA NA LINHA FINAL DO DIAGNÓSTICO COMPLETO
RESULT_RE  = re.compile(r'\$ETEV(29|30(\d*))!')
JSON_RE    = re.compile(r'\{[^{}]*\}')
CURVE_RE   = re.compile(r'\[\s*(\d+(?:\s*,\s*\d+)*)\s*,?\s*\]')    # CURVA DO TESTE QUE O FIRMWARE MANDA ANTES DO RESULTADO
DATE_FORMATS = ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d', '%d/%m/%Y %H:%M:%S', '%d/%m/%Y')


def br(value, decimals=0):
    return f'{value:,.{decimals}f}'.replace(',', ' ').replace('.', ',').replace(' ', '.')


def readJson(command, timeout=2.0):
    device.send(command)
    deadline = time() + timeout

    while time() < deadline:
        match = JSON_RE.search(device.get(timeout=deadline - time()) or '')

        if match:
            try:
                return json.loads(match.group())
            except ValueError:
                return None

    return None


def readData(timeout=2.0):
    return readJson('/get-data', timeout)


def readSeries(seconds, dt=0.2, stop=None):
    rows      = []
    startTime = time()
    device.clear()

    while time() - startTime < seconds:
        data = readData()

        if data is not None:
            rows.append({'t': round(time() - startTime, 1), **data})

        if stop and stop(rows):
            break

        sleep(dt)

    return rows


def stats(values):
    values = [v for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]

    if not values:
        return None

    return {'n': len(values), 'min': min(values), 'media': statistics.mean(values), 'max': max(values), 'desvio': statistics.pstdev(values)}


def parseDate(text):
    for pattern in DATE_FORMATS:
        try:
            return datetime.strptime(text.strip()[:19], pattern)
        except ValueError:
            continue

    return None


# CURVA DE CALIBRAÇÃO DO FIRMWARE (AlcoholSensor::analyze): mg/L = a·b^(c·x+d), ACIMA DE 2,5 SATURA E ABAIXO DE 0,010 É ZERO
def curveMgl(coefs, x):
    a, b, c, d = coefs

    try:
        mgl = a*math.exp((c*x + d)*math.log(b))
    except (OverflowError, ValueError):
        return 2.5

    return 2.5 if mgl > 2.5 else 0.0 if mgl < 0.010 else mgl


# OBJETOS JSON COMPLETOS DO TEXTO E O RESTO A PARTIR DO ÚLTIMO "{" (LINHA QUE CHEGOU PELA METADE)
def readLines(text):
    lines, end = [], 0

    for match in JSON_RE.finditer(text):
        end = match.end()

        try:
            lines.append(json.loads(match.group()))
        except ValueError:
            continue

    rest = text[end:]
    return lines, rest[rest.rfind('{'):] if '{' in rest else ''


# ENSAIO DE UMA LINHA DE SOPRO: sopro-<tipo pedido>[-<força>], E A FORÇA
def blowTest(line):
    force = FORCES.get(line.get('force'), (None,))[0]
    return '-'.join(['sopro', RESULTS[line['blow']]] + ([force] if force else [])), force


def blowText(attempt):
    seconds = f", {br(attempt['duracao_ms']/1000, 1)} s" if attempt['resultado'] != 'nenhum' else ''
    return f"{attempt['resultado']} (pico {br(attempt['pico'], 1)}{seconds})"


# BATERIA DE QUALIDADE NA BANCADA: CADA ETAPA GUARDA O RESULTADO E AS MEDIDAS, E O print() FECHA COM A TABELA
class Quality:
    DIAG_TIMEOUT    = 15.0        # s, TST_* RESPONDE EM ~10 S (OBSERVA 10 S; O CARTÃO DO RESULTADO VEM DEPOIS DA RESPOSTA)
    TEMP_RANGE      = (-10, 70)   # ºC
    HUMIDITY_RANGE  = (1, 100)    # %
    TEMP_WINDOW     = 4.0         # s DE LEITURAS: O DHT22 SÓ MEDE DE NOVO A CADA 2 S
    TEMP_DT         = 0.4         # s
    BYPASS_ANALOG   = 23000       # analog FIXO DO alcohol.bypass (BUILD DE DEBUG)
    SENSOR_READY    = 5000        # analog MÍNIMO DO SENSOR AQUECIDO EM AR LIMPO (Calibration::prepare)
    SENSOR_WINDOW   = 2.0         # s
    CALIBRATION_DAYS = 365        # VALIDADE DA CALIBRAÇÃO (PPTC 0001-02 §6.1)
    CLEAN_AIR_MGL   = 0.020       # mg/L: ACIMA DISSO O FIRMWARE JÁ CONSIDERA ÁLCOOL (Test::process)
    REST_SAMPLES    = 10
    REST_NOISE      = 0.5         # VARIAÇÃO MÁXIMA DA PRESSÃO PARADA: DERIVA ~0,1, SOPRO SOBE 12 A 110 (BANCADA 29/10/2026)
    SAMPLE_DT       = 0.15        # s ENTRE LEITURAS DO /get-data
    DIAGNOSTIC_TIMEOUT = 240      # s ATÉ A PRIMEIRA LINHA: ABRIR O MENU, SERIAL E SENSORES (~60 S) E O PRIMEIRO SOPRO (~40 S)
    BLOW_FIRST      = 90          # s ATÉ A PRIMEIRA LINHA DO TST_BLOW: INSTRUÇÃO 8 + CALIBRAÇÃO 1,5 + 25 SEM SOPRAR + RESULTADO
    BLOW_IDLE       = 120         # s SEM LINHA ENCERRAM: A MAIOR ESPERA ENTRE DUAS É O "TENTAR NOVAMENTE?" + UMA ETAPA SEM SOPRO
    IGNITION_DT     = 0.3         # s ENTRE LINHAS: O FIRMWARE JUNTA O QUE CHEGA EM MENOS DE 100 MS
    START_TIMEOUT   = 150         # s ATÉ O $ETEV05!: LOGOS, CÂMERA, AQUECIMENTO, 25 S POR SOPRO E O "TENTAR NOVAMENTE?"
    RESULT_TIMEOUT  = 60          # s DO $ETEV05! (ANALISANDO ~20 S) AO RESULTADO
    RELEASE_TIMEOUT = 130         # s ATÉ VOLTAR A RESPONDER: A TELA DA CONTRASSENHA ESPERA 120 S
    REST_BETWEEN    = 5           # s ENTRE TESTES REPETIDOS
    BLOW_PROB       = (0.3, 1.5)  # s, FAIXA DO blowProb NO PROTOCOLO DE SOPRO DA SIGHIR

    def __init__(self, fw, espId, sensorId):
        self.fw       = fw
        self.espId    = espId
        self.sensorId = sensorId
        self.results  = []

    def add(self, step, ok, detail, measured=None, **data):
        self.results.append({'etapa': step, 'ok': bool(ok), 'detalhe': detail})
        record(self.espId, 'qualidade', etapa=step, ok=bool(ok), detalhe=detail, medido=measured or detail, dados=data)
        log('ok' if ok else 'err', f"{step}: {'OK' if ok else 'FALHOU'} — {detail}")
        return bool(ok)

    def debug(self):
        return self.sensorId in core.DEBUG_SENSORS

    def diagnostic(self, name):
        command, target, fail = DIAGNOSTICS[name]
        device.clear()
        result = device.expect(target=target, command=command, fail=fail, timeout=self.DIAG_TIMEOUT)
        return {True: target, False: fail, None: 'sem resposta'}[result], result is True

    def serial(self):
        device.clear()
        startTime = time()
        acked     = bool(device.expect(target='ETKAACK', command='$ETKA!', timeout=3))
        latency   = round((time() - startTime)*1000)
        data      = readData()
        firmware  = core.versionStr(self.fw['version'])
        ok        = acked and bool(self.fw['version']) and data is not None and core.isNativeId(self.espId)
        detail    = f"$ETKA!→$ETKAACK! em {latency} ms, firmware {firmware}, esp_id {self.espId}, /get-data {'ok' if data is not None else 'SEM RESPOSTA'}"
        return self.add('serial', ok, detail, f'{latency} ms · {firmware} · /get-data {"ok" if data is not None else "mudo"}',
                        latencia_ms=latency, ack=acked, firmware=firmware, get_data=data is not None)

    def temperature(self):
        rows         = readSeries(self.TEMP_WINDOW, self.TEMP_DT)
        temp         = stats([row.get('temperature') for row in rows])
        humidity     = stats([row.get('humidity') for row in rows])
        answer, diag = self.diagnostic('temperatura')
        inRange      = (temp is not None and humidity is not None and
                        self.TEMP_RANGE[0] <= temp['min'] and temp['max'] <= self.TEMP_RANGE[1] and
                        self.HUMIDITY_RANGE[0] <= humidity['min'] and humidity['max'] <= self.HUMIDITY_RANGE[1])
        reading      = f"{temp['media']:.1f} ºC, {humidity['media']:.1f} % de umidade" if temp and humidity else 'sem leitura no /get-data'
        return self.add('temperatura', diag and inRange, f'TST_TEMP → {answer}, {reading}' + ('' if inRange else ' (FORA DA FAIXA)'),
                        f"{br(temp['media'], 1)} °C · {br(humidity['media'])} % UR" if temp and humidity else 'sem leitura',
                        temperatura=temp, umidade=humidity, faixa_temperatura=list(self.TEMP_RANGE),
                        faixa_umidade=list(self.HUMIDITY_RANGE), tst=answer)

    def sensor(self):
        analogs      = [row.get('analog') for row in readSeries(self.SENSOR_WINDOW, self.SAMPLE_DT)]
        answer, diag = self.diagnostic('sensor')
        level        = stats([a for a in analogs if isinstance(a, (int, float)) and a > 0])
        invalid      = not analogs or level is None or level['n'] < len(analogs)
        bypass       = bool(analogs) and all(a == self.BYPASS_ANALOG for a in analogs)
        ready        = level is not None and level['media'] >= self.SENSOR_READY
        notes        = (' — analog -1: sensor fora do I2C/ADS sem resposta' if invalid else '') + \
                       (f' — analog fixo {self.BYPASS_ANALOG} e sensor de debug: build de DEBUG (bypass), o cartucho não é lido' if bypass else '') + \
                       (f' — abaixo de {self.SENSOR_READY}: sensor frio ou sem aquecer' if level and not ready else '')
        return self.add('sensor', diag and not invalid and not bypass and ready,
                        f"TST_SENS → {answer}, analog {min(analogs, default='-')}…{max(analogs, default='-')}{notes}",
                        f"analog {br(level['media'])} (σ {br(level['desvio'])})" if level else 'sem leitura',
                        analog=level, tst=answer, pronto_min=self.SENSOR_READY, bypass=bypass)

    # CALIBRAÇÃO GRAVADA NO CARTUCHO: COEFICIENTES DA CURVA, DATA (VALE 365 DIAS) E O AR LIMPO LIDO COMO ZERO PELA CURVA
    def calibration(self):
        device.clear()
        coefs    = readJson('coefs', timeout=6.0) or {}    # O FIRMWARE RELÊ 170 BYTES DA EEPROM A 10 MS CADA
        values   = [coefs.get(key) for key in ('c1', 'c2', 'c3', 'c4')]
        hasCoefs = all(isinstance(v, (int, float)) and v > 0 for v in values)
        date     = parseDate(str(coefs.get('timestamp') or ''))
        age      = (datetime.now() - date).days if date else None
        valid    = age is not None and 0 <= age <= self.CALIBRATION_DAYS
        air      = stats([row.get('analog') for row in readSeries(self.SENSOR_WINDOW, self.SAMPLE_DT) if (row.get('analog') or 0) > 0])
        mgl      = curveMgl(values, air['media']) if hasCoefs and air else None
        clean    = mgl is not None and mgl < self.CLEAN_AIR_MGL
        problems = [text for bad, text in [(not coefs, 'o cartucho não devolveu a calibração (coefs)'),
                                           (bool(coefs) and not hasCoefs, 'sem coeficientes válidos (c1–c4 > 0)'),
                                           (hasCoefs and date is None, 'data da calibração ilegível'),
                                           (age is not None and not valid, f'calibração com {age} dias: vencida (validade {self.CALIBRATION_DAYS})'),
                                           (mgl is not None and not clean, f'a curva lê {br(mgl or 0, 3)} mg/L em ar limpo'),
                                           (self.debug(), 'sensor de debug')] if bad]
        when     = f"calibrado em {date:%d/%m/%Y} ({age} dias)" if date else 'sem data de calibração'
        detail   = f"{when}, ar limpo {mgl:.3f} mg/L pela curva" if mgl is not None else when
        return self.add('calibracao', not problems, detail + (f" — {'; '.join(problems)}" if problems else ''),
                        f'{when} · ar limpo {br(mgl, 3)} mg/L' if mgl is not None else when,
                        coeficientes=dict(zip(('c1', 'c2', 'c3', 'c4'), values)), data=f'{date:%Y-%m-%d}' if date else None,
                        idade_dias=age, validade_dias=self.CALIBRATION_DAYS,
                        vence_em=f'{date + timedelta(days=self.CALIBRATION_DAYS):%Y-%m-%d}' if date else None,
                        zero=coefs.get('zero'), analog_ar_limpo=air, mgl_ar_limpo=mgl, limite_mgl=self.CLEAN_AIR_MGL,
                        sensor_id=self.sensorId, problemas=problems)

    def pressure(self):
        rest         = stats([row.get('pressure') for row in readSeries(self.REST_SAMPLES*self.SAMPLE_DT, self.SAMPLE_DT)])
        answer, diag = self.diagnostic('pressao')
        noise        = rest['max'] - rest['min'] if rest else None
        stable       = noise is not None and noise < self.REST_NOISE
        detail       = f"TST_PRESS → {answer}, parado {rest['media']:.3f} (variação {noise:.3f})" if rest else f'TST_PRESS → {answer}, /get-data sem pressão'
        return self.add('pressao', diag and stable, detail, f"repouso {br(rest['media'], 2)} (Δ {br(noise, 3)})" if rest else 'sem leitura',
                        repouso=rest, variacao=noise, limite_variacao=self.REST_NOISE, tst=answer)

    # LINHAS JSON DO DIAGNÓSTICO NO FIRMWARE ATÉ A FINAL ({"diagnostic": name}): first S PELA PRIMEIRA, DEPOIS idle S MUDO ENCERRAM;
    # O TESTE SERIAL DO DIAGNÓSTICO COMPLETO MANDA $ETKA! E PASSA COM QUALQUER COMANDO EM 10 S: A CLI RESPONDE COM OUTRO
    def lines(self, name, first, idle):
        text, lastTime, limit = '', time(), first

        while time() - lastTime < limit:
            chunk = device.get(timeout=1.0) or ''

            if '$ETKA!' in chunk:
                device.send('$ETKA!')

            found, text = readLines(text + chunk)

            for line in found:
                lastTime, limit = time(), idle
                yield line

                if line.get('diagnostic') == name:
                    return

    # UM SOPRO QUE O FIRMWARE CLASSIFICOU: CERTO QUANDO O RESULTADO É O TIPO PEDIDO
    def attempt(self, line):
        attempt = {'resultado': RESULTS.get(line.get('result'), line.get('result')), 'pico': round(line.get('peak', 0), 1),
                   'duracao_ms': line.get('ms', 0), 'ok': line.get('result') == line['blow']}
        log('ok' if attempt['ok'] else 'err', f"{blowTest(line)[0]} {line.get('attempt')}/{line.get('of')}: {blowText(attempt)}"
                                                + ('' if attempt['ok'] else f" — esperado {RESULTS[line['blow']]}"))
        return attempt

    # O OPERADOR RODA MENU → AUTODIAGNÓSTICO → DIAGNÓSTICO COMPLETO NA TELA; A CLI ESCUTA OS SOPROS E A LINHA FINAL DO FIRMWARE
    # (null = IGNORADO: RELÉ NO MIX OU PULADO; ETAPA QUE O FIRMWARE NÃO MANDA, DE ANTES DAS 7, FICA DE FORA)
    def selfDiagnostic(self):
        blows, end = [], None
        device.clear()
        log('info', 'aguardando o autodiagnóstico na tela: Menu → Configurações (pág. 2) → Autodiagnóstico → Diagnóstico Completo '
                    '(serial e sensores ~1 min, depois NÃO sopre, sopro incompleto, sopro completo e o relé: sem módulo na bancada '
                    'toque Não em "Deseja Mesmo Continuar?" e ele fica ignorado)')

        for line in self.lines('full', self.DIAGNOSTIC_TIMEOUT, self.BLOW_IDLE):
            if line.get('blow') in RESULTS:
                blows.append({'tipo': RESULTS[line['blow']], **self.attempt(line)})

            if line.get('diagnostic') == 'full':
                end = line

        if end is None:
            return self.add('autodiagnostico', False, f'sem o resultado do aparelho em {self.DIAGNOSTIC_TIMEOUT} s: o diagnóstico não foi '
                            'iniciado na tela ou não terminou', 'não concluído na tela', etapas={}, sopros=blows)

        steps   = {name: end[key] for key, name in DIAGNOSTIC.items() if key in end}
        counted = [ok for ok in steps.values() if ok is not None]
        text    = ', '.join(f"{step} {VERDICTS[ok]}" for step, ok in steps.items())
        text   += (' — sopros: ' + '; '.join(f"{b['tipo']} → {blowText(b)}" for b in blows)) if blows else ' — sem sopros (sensor de pressão reprovado)'
        return self.add('autodiagnostico', all(counted), text, f'{sum(counted)}/{len(counted)} aprovados na tela', etapas=steps, sopros=blows)

    def send(self, commands):
        for command in commands:
            device.send(command)
            sleep(self.IGNITION_DT)

    def prepare(self, ignition):
        self.send(ignition['off'])
        device.clear()

        if not device.expect(target='OFF', command='endTravel', timeout=5):
            return False

        return core.writeSetting('press', 0) and core.writeSetting('testalc', 0)

    # ESCUTA O TESTE DISPARADO PELA IGNIÇÃO ATÉ O RESULTADO $ETEV29!/$ETEV30<mg/L>!
    def listen(self):
        events    = {'noblow': 0, 'timeout': 0, 'analyzing': False, 'result': None, 'mgl': 0.0, 'curve': []}
        startTime = time()
        deadline  = startTime + self.START_TIMEOUT

        while time() < deadline:
            text   = device.get(timeout=1.0) or ''
            result = RESULT_RE.search(text)
            curve  = CURVE_RE.search(text)

            if text.count('$NOBLOW!'):
                events['noblow'] += text.count('$NOBLOW!')
                log('warn', f"sopro cortado antes de 1,8 s ({events['noblow']}): o aparelho pede de novo")

            if text.count('$ETEV11!'):
                events['timeout'] += text.count('$ETEV11!')
                log('warn', 'sem sopro em 25 s: a tela pergunta "Tentar novamente?"')

            if '$ETEV05!' in text and not events['analyzing']:
                events['analyzing'] = True
                deadline = time() + self.RESULT_TIMEOUT
                log('info', 'sopro aceito: analisando (~20 s)')

            if curve:
                events['curve'] = [int(value) for value in re.findall(r'\d+', curve.group(1))]

            if result:
                events['result'] = 'alcool' if result.group(1) != '29' else 'limpo'
                events['mgl']    = int(result.group(2))/1000 if result.group(2) else 0.0
                break

        events['seconds'] = round(time() - startTime)
        return events

    def release(self):
        deadline = time() + self.RELEASE_TIMEOUT

        while time() < deadline:
            device.clear()

            if device.expect(target='ETKAACK', command='$ETKA!', timeout=3):
                return True

        return False

    def start(self, what):
        ignition = IGNITION.get(str(core.readSetting('telemetry')))

        if ignition is None:
            log('err', 'telemetria desconhecida na setting telemetry: configure com o comando telemetry')
            return None

        if not self.prepare(ignition):
            log('err', 'o aparelho não confirmou endTravel/press/testalc: confira com status')
            return None

        log('info', f'teste disparado: {what}')
        self.send(ignition['on'])
        return ignition

    def end(self, ignition, hint):
        if not self.release():
            log('err', f'o aparelho não voltou a responder: {hint}')

        self.send(ignition['off'])
        device.clear()
        device.expect(target='OFF', command='endTravel', timeout=5)

    def alcohol(self, expected, times):
        step = 'com-alcool' if expected else 'sem-alcool'
        runs = []

        if self.debug():
            log('warn', 'sensor de debug: build com bypass (analog fixo), o resultado não vem do cartucho')

        for n in range(1, times + 1):
            sleep(self.REST_BETWEEN if n > 1 else 0)
            ignition = self.start(f"{n}/{times}, sopre {'COM' if expected else 'SEM'} álcool quando a tela pedir")

            if ignition is None:
                return self.add(step, False, 'o teste não disparou', 'não disparou', esperado='alcool' if expected else 'limpo', testes=[])

            run = self.listen()

            if run['result'] == 'alcool':
                log('warn', 'álcool: na tela, toque em "Desligar Display" para o aparelho voltar a responder')

            self.end(ignition, 'toque em "Desligar Display" (ou "Não" no "Tentar novamente?")')
            run['analog'] = self.lastAnalog() if run['result'] else '-'
            runs.append(run)

        want = 'alcool' if expected else 'limpo'
        good = [run for run in runs if run['result'] == want]
        text = '; '.join(f"#{n} " + (f"{'ÁLCOOL' if run['result'] == 'alcool' else 'sem álcool'} {run['mgl']:.3f} mg/L, "
                                     f"analog {run['analog']}" if run['result'] else 'sem resultado') +
                         f", {run['seconds']} s" + (f", {run['noblow']} sopro(s) cortado(s)" if run['noblow'] else '')
                         for n, run in enumerate(runs, 1))
        tests = [{'resultado': run['result'], 'mgl': run['mgl'], 'analog': run['analog'], 'segundos': run['seconds'],
                  'cortados': run['noblow'], 'curva': run['curve']} for run in runs]
        mgls  = ', '.join(br(run['mgl'], 3) for run in good)
        return self.add(step, len(good) == times, f'{len(good)}/{times} como esperado — {text}',
                        f'{len(good)}/{times} como esperado' + (f' · {mgls} mg/L' if mgls else ''),
                        esperado=want, testes=tests)

    # O PROTOCOLO COMEÇA PELA TOLERÂNCIA (CF:blowProb$X!, QUE A v6.5.4 APLICA SEM REINICIAR); FORA DA FAIXA ELE NÃO RODA
    def setBlowProb(self, value=None):
        text   = str(value) if value is not None else core.readSetting('blowProb')
        number = float(text) if text and text.replace('.', '', 1).isdigit() else None

        if number is None or not self.BLOW_PROB[0] <= number <= self.BLOW_PROB[1]:
            log('err', f'blowProb {text} fora da faixa do protocolo ({br(self.BLOW_PROB[0], 1)} a {br(self.BLOW_PROB[1], 1)} s): '
                       'rode qualidade sopro --blowprob X')
            return None

        if value is not None and not core.writeSetting('blowProb', number):
            return None

        return number

    # PROTOCOLO DE SOPRO DO FIRMWARE (TST_BLOW): A TELA GUIA O OPERADOR, CADA SOPRO VOLTA NUMA LINHA E CADA ETAPA VIRA UM ENSAIO
    def blows(self, blowProb=None):
        series, end = {}, None
        tolerance   = self.setBlowProb(blowProb)

        if tolerance is None or not core.writeSetting('press', 0):    # press$1 FINGE QUE SEMPRE HÁ SOPRO
            return False

        device.clear()
        device.send('TST_BLOW')
        log('info', f'protocolo de sopro na tela (blowProb {br(tolerance, 2)} s): 3 sem soprar, 3 incompletos e 3 completos em cada força')

        for line in self.lines('blow', self.BLOW_FIRST, self.BLOW_IDLE):
            step, force = blowTest(line) if line.get('blow') in RESULTS else (None, None)

            if step and line.get('attempt') == 1:    # A ETAPA REFEITA NA TELA RECOMEÇA DO 1
                series[step] = {'tipo': line['blow'], 'forca': force, 'repeticoes': series.get(step, {}).get('repeticoes', 0) + 1, 'sopros': []}

            if step in series:
                series[step]['sopros'].append(self.attempt(line))
                series[step]['of'] = line.get('of')

            if line.get('diagnostic') == 'blow':
                end = line

        steps = [step for step in STEPS if step.startswith('sopro-')]

        if end is not None and end.get('pressure') is False:
            for step in steps:
                self.add(step, False, 'sensor de pressão sem resposta (HX711): o protocolo não rodou', 'sem sensor de pressão')

            return False

        if end is None:
            log('err', f'o protocolo não terminou ({self.BLOW_IDLE} s sem linha do aparelho): só entram as etapas que fecharam')

        results = [self.blowStep(step, series[step], tolerance) for step in steps if step in series and len(series[step]['sopros']) == series[step]['of']]
        return end is not None and len(results) == len(steps) and all(results)

    def blowStep(self, step, run, tolerance):
        kind, force = run['tipo'], run['forca']
        attempts    = run['sopros']
        passed      = sum(attempt['ok'] for attempt in attempts)
        repeated    = f", refeita {run['repeticoes'] - 1} vez(es) na tela" if run['repeticoes'] > 1 else ''
        detail      = f"{passed}/{len(attempts)} {OUTCOMES[kind]} — " + '; '.join(f'#{n} {blowText(a)}' for n, a in enumerate(attempts, 1))
        return self.add(step, passed == len(attempts), detail + f', blowProb {br(tolerance, 2)} s' + repeated, f'{passed}/{len(attempts)} {OUTCOMES[kind]}',
                        forca=force, esperado=RESULTS[kind], esperados=len(attempts), aprovados=passed, repeticoes=run['repeticoes'],
                        blowProb=tolerance, sopros=attempts)

    # DEPOIS DO TESTE AINDA CHEGAM $ETEV16!/$ETEV01!: SÓ VALE A RESPOSTA NUMÉRICA
    def lastAnalog(self):
        for attempt in range(3):
            device.clear()
            value = core.extractValue(device.request('last_analog', timeout=3))

            if value and value.lstrip('-').isdigit():
                return value

        return '-'

    def failed(self):
        return [r['etapa'] for r in self.results if not r['ok']]

    def print(self):
        log('info', '----- QUALIDADE -----')

        for r in self.results:
            log('ok' if r['ok'] else 'err', f"{r['etapa']:12} {'OK' if r['ok'] else 'FALHOU':7} {r['detalhe']}")

        bad = self.failed()
        log('ok' if not bad else 'err', f"{self.espId}: " + ('APROVADO nas etapas feitas' if not bad else f"REPROVADO em {', '.join(bad)}"))


# ENSAIOS EXIGIDOS PARA LIBERAR O APARELHO, NA ORDEM DO PROCEDIMENTO: NOME E CRITÉRIO DE ACEITAÇÃO
STEPS = {
    'serial': ('Comunicação serial', 'responde ao $ETKA!, ao $firmware! e ao /get-data'),
    'temperatura': ('Temperatura e umidade (DHT22)', f'TST_TEMP aprovado; leituras entre {Quality.TEMP_RANGE[0]} e {Quality.TEMP_RANGE[1]} °C '
                                                     f'e {Quality.HUMIDITY_RANGE[0]} a {Quality.HUMIDITY_RANGE[1]} % UR'),
    'sensor': ('Sensor de álcool (ADS1115)', f'TST_SENS aprovado; analog ≥ {br(Quality.SENSOR_READY)} em ar limpo, sem leitura inválida'),
    'calibracao': ('Calibração do sensor', f'coeficientes gravados; calibração com até {Quality.CALIBRATION_DAYS} dias; '
                                           f'ar limpo < {br(Quality.CLEAN_AIR_MGL, 3)} mg/L pela curva'),
    'pressao': ('Sensor de pressão (HX711)', f'TST_PRESS aprovado; variação em repouso < {br(Quality.REST_NOISE, 1)}'),
    'autodiagnostico': ('Autodiagnóstico completo na tela', 'serial, temperatura, álcool, memória do sensor e pressão aprovados pelo aparelho, '
                                                       'um sopro de cada tipo (sem sopro, incompleto, completo) classificado certo e o relé '
                                                       'comutando (ignorado no MIX ou sem módulo)'),
    'sopro-nenhum': ('Teste sem soprar', '3 testes sem soprar terminam em "sem sopro" na janela de 25 s do teste real'),
    **{f'sopro-incompleto-{key}': (f'Sopro incompleto {label}', '3 sopros curtos classificados como incompletos (recusados)') for key, label in FORCES.values()},
    **{f'sopro-completo-{key}': (f'Sopro completo {label}', '3 sopros contínuos classificados como completos (aceitos)') for key, label in FORCES.values()},
    'sem-alcool': ('Teste real sem álcool', 'resultado sem álcool ($ETEV29!)'),
    'com-alcool': ('Teste real com álcool', 'álcool detectado ($ETEV30<mg/L>!)')
}
