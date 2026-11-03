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
    '2': {'on': [STT_KEY.format(1)], 'off': [STT_KEY.format(0)]},          # PELA USB (PORTA 1) UM PACOTE BASTA
    '6': {'on': ['+QACC:high']*5, 'off': ['+QACC:low']*5}                 # MÉDIA DAS 4 ÚLTIMAS AMOSTRAS > 0,75 LIGA
}

# DIAGNÓSTICO DO FIRMWARE: COMANDO, RESPOSTA OK E RESPOSTA DE FALHA
DIAGNOSTICS = {
    'temperatura': ('TST_TEMP', 'tempworking', 'ERROR'),
    'sensor': ('TST_SENS', '$ETEV20!', '$ETEV24!'),
    'pressao': ('TST_PRESS', 'pressworking', '$ERROR!')
}

RESULT_RE  = re.compile(r'\$ETEV(29|30(\d*))!')
VERDICT_RE = re.compile(r'pressworking|tempworking|\$ETEV20!|\$ETEV24!|\$ERROR!|\$NOBLOW!|\bERROR\b')
PASSED     = ('pressworking', 'tempworking', '$ETEV20!')
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


# VEREDITOS DO AUTODIAGNÓSTICO COMPLETO NA ORDEM DA TELA; SEM O SENSOR DE PRESSÃO A TELA NÃO PEDE O SOPRO
def parseDiagnostic(tokens):
    tokens  = [token for token in tokens if token != '$NOBLOW!']
    steps   = ['pressao', 'sopro', 'temperatura', 'sensor']
    results = {}

    for token in tokens:
        step = steps.pop(0) if steps else None

        if step is None:
            break

        results[step] = token in PASSED

        if step == 'pressao' and not results[step]:
            results['sopro'] = False
            steps.remove('sopro')

    return results


# BATERIA DE QUALIDADE NA BANCADA: CADA ETAPA GUARDA O RESULTADO E AS MEDIDAS, E O print() FECHA COM A TABELA
class Quality:
    DIAG_TIMEOUT    = 15.0        # s, TST_* RESPONDE EM ~13 S (10 S OBSERVANDO + TELAS)
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
    DIAGNOSTIC_TIMEOUT = 240      # s PARA ABRIR O MENU E FAZER AS 4 ETAPAS DA TELA, COM NOVAS TENTATIVAS DE SOPRO
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

    # O OPERADOR RODA MENU → AUTODIAGNÓSTICO → DIAGNÓSTICO COMPLETO NA TELA (SOPRA QUANDO ELA PEDE); A CLI SÓ ESCUTA
    def selfDiagnostic(self):
        tokens   = []
        deadline = time() + self.DIAGNOSTIC_TIMEOUT
        device.clear()
        log('info', 'aguardando o autodiagnóstico na tela: Menu → Configurações (pág. 2) → Autodiagnóstico → Diagnóstico Completo')

        while time() < deadline and len(parseDiagnostic(tokens)) < 4:
            found = VERDICT_RE.findall(device.get(timeout=1.0) or '')
            tokens.extend(found)

            if '$NOBLOW!' in found:
                log('warn', 'sopro interrompido: na tela, "Sim" em "Tentar novamente?" e sopre contínuo')

        results = parseDiagnostic(tokens)

        if not results:
            return self.add('autodiagnostico', False, f'nenhum resultado em {self.DIAGNOSTIC_TIMEOUT} s: o diagnóstico não foi iniciado na tela',
                            'não iniciado na tela', etapas={})

        text = ', '.join(f"{step} {'OK' if ok else 'FALHOU'}" for step, ok in results.items())
        return self.add('autodiagnostico', len(results) == 4 and all(results.values()), text + ('' if len(results) == 4 else ' (incompleto)'),
                        f'{sum(results.values())}/4 aprovados na tela', etapas=results)

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

    # ESCUTA O TESTE DISPARADO PELA IGNIÇÃO ATÉ O RESULTADO $ETEV29!/$ETEV30<mg/L>! OU ATÉ stop(events)
    def listen(self, stop=None):
        events    = {'noblow': 0, 'timeout': 0, 'analyzing': False, 'result': None, 'mgl': 0.0, 'curve': []}
        startTime = time()
        deadline  = startTime + self.START_TIMEOUT

        while time() < deadline and not (stop and stop(events)):
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

    def alcohol(self, expected, times, step=None, force=None):
        step = step or ('com-alcool' if expected else 'sem-alcool')
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
                        esperado=want, forca=force, testes=tests)

    # SEM SOPRAR: CADA TESTE TEM QUE TERMINAR EM $ETEV11! (SEM SOPRO EM 25 S) SEM NUNCA ACEITAR SOPRO
    def noBlow(self, times):
        outcomes = []

        for n in range(1, times + 1):
            ignition = self.start(f'{n}/{times}, NÃO sopre; quando a tela perguntar "Tentar novamente?", toque em "Não"')

            if ignition is None:
                return self.add('sopro-nenhum', False, 'o teste não disparou', 'não disparou', testes=outcomes)

            run = self.listen(stop=lambda e: e['timeout'] or e['analyzing'])
            outcomes.append('ACEITO' if run['analyzing'] else 'sem sopro' if run['timeout'] else 'sem resposta')
            self.end(ignition, 'toque em "Não" no "Tentar novamente?"')

        passed      = outcomes.count('sem sopro')
        value, text = self.blowProb()
        return self.add('sopro-nenhum', passed == times, f'{passed}/{times} testes sem sopro terminaram em "sem sopro" ($ETEV11!), {text}',
                        f'{passed}/{times} terminaram em "sem sopro"', esperados=times, aprovados=passed, testes=outcomes, blowProb=value)

    # SOPRO INCOMPLETO: NUM TESTE SÓ, CADA SOPRO CURTO TEM QUE VIRAR $NOBLOW! E NENHUM PODE SER ACEITO COMO SOPRO
    def shortBlows(self, times, force):
        step     = f'sopro-incompleto-{force}'
        ignition = self.start(f'sopre {times} vezes CURTO e {force.upper()} (menos de 1 s); depois pare e toque em "Não" no "Tentar novamente?"')

        if ignition is None:
            return self.add(step, False, 'o teste não disparou', 'não disparou', forca=force, esperados=times, cortados=0, aceito=False)

        run         = self.listen(stop=lambda e: e['noblow'] >= times or e['analyzing'] or e['timeout'])
        self.end(ignition, 'pare de soprar e toque em "Não" no "Tentar novamente?"')
        ok          = run['noblow'] >= times and not run['analyzing']
        value, text = self.blowProb()
        return self.add(step, ok, f"{run['noblow']}/{times} sopros cortados detectados" + (' — um sopro curto foi ACEITO' if run['analyzing'] else '') + f', {text}',
                        f"{min(run['noblow'], times)}/{times} recusados" + (' · 1 aceito' if run['analyzing'] else ''),
                        forca=force, esperados=times, cortados=run['noblow'], aceito=run['analyzing'], blowProb=value)

    def blowProb(self):
        value  = core.readSetting('blowProb')
        inside = value is not None and value.replace('.', '', 1).isdigit() and self.BLOW_PROB[0] <= float(value) <= self.BLOW_PROB[1]

        if not inside:
            log('warn', f'blowProb {value} s fora da faixa do protocolo ({self.BLOW_PROB[0]} a {self.BLOW_PROB[1]} s): '
                        'ajuste com settings --set blowProb=X --restart se o usuário pedir')

        return value, f'blowProb {value} s' + ('' if inside else ' (fora da faixa 0,3–1,5)')

    def fullBlows(self, times, force):
        log('info', f'sopro COMPLETO e {force.upper()}: contínuo até o bipe parar, sem álcool ({self.blowProb()[1]})')
        return self.alcohol(False, times, f'sopro-completo-{force}', force)

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


FORCES = {'fraco': 'fraco', 'medio': 'médio', 'forte': 'forte'}

# ENSAIOS EXIGIDOS PARA LIBERAR O APARELHO, NA ORDEM DO PROCEDIMENTO: NOME E CRITÉRIO DE ACEITAÇÃO
STEPS = {
    'serial': ('Comunicação serial', 'responde ao $ETKA!, ao $firmware! e ao /get-data'),
    'temperatura': ('Temperatura e umidade (DHT22)', f'TST_TEMP aprovado; leituras entre {Quality.TEMP_RANGE[0]} e {Quality.TEMP_RANGE[1]} °C '
                                                     f'e {Quality.HUMIDITY_RANGE[0]} a {Quality.HUMIDITY_RANGE[1]} % UR'),
    'sensor': ('Sensor de álcool (ADS1115)', f'TST_SENS aprovado; analog ≥ {br(Quality.SENSOR_READY)} em ar limpo, sem leitura inválida'),
    'calibracao': ('Calibração do sensor', f'coeficientes gravados; calibração com até {Quality.CALIBRATION_DAYS} dias; '
                                           f'ar limpo < {br(Quality.CLEAN_AIR_MGL, 3)} mg/L pela curva'),
    'pressao': ('Sensor de pressão (HX711)', f'TST_PRESS aprovado; variação em repouso < {br(Quality.REST_NOISE, 1)}'),
    'autodiagnostico': ('Autodiagnóstico completo na tela', 'pressão, sopro, temperatura e álcool aprovados pelo aparelho'),
    'sopro-nenhum': ('Teste sem soprar', '3 testes terminam em "sem sopro"; nenhum sopro aceito'),
    **{f'sopro-incompleto-{key}': (f'Sopro incompleto {label}', '3 sopros curtos recusados ($NOBLOW!); nenhum aceito') for key, label in FORCES.items()},
    **{f'sopro-completo-{key}': (f'Sopro completo {label}', '3 sopros aceitos e analisados; resultado sem álcool') for key, label in FORCES.items()},
    'sem-alcool': ('Teste real sem álcool', 'resultado sem álcool ($ETEV29!)'),
    'com-alcool': ('Teste real com álcool', 'álcool detectado ($ETEV30<mg/L>!)')
}
