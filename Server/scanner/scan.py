import os
import re
import sys
import json
import sqlite3
import argparse
import datetime as dt
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# RODA NO .venv PREPARADO PELO tools/boot.py (MESMO SE O AGENTE FOI ABERTO SEM O LAUNCHER)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import _venv  # noqa: E402
_venv.ensure(ROOT)

from api import api  # noqa: E402


# O SNAPSHOT MORA NA BASE COMPARTILHADA ../docs (ANTES FICAVA EM Server/docs); SIGHIR_DOCS SOBRESCREVE
def findSnapshot():
    parts = ('ServerAnalysis', 'files', 'db.sqlite3')
    for docs in (os.environ.get('SIGHIR_DOCS'), os.path.join(ROOT, '..', 'docs'), os.path.join(ROOT, 'docs')):
        if docs and os.path.isfile(os.path.join(docs, *parts)):
            return os.path.abspath(os.path.join(docs, *parts))
    return os.path.abspath(os.path.join(ROOT, '..', 'docs', *parts))


SNAPSHOT = findSnapshot()

# ROTULOS DO PAINEL, EXTRAIDOS DOS Monitoramento_Inicio_a_Fim*.csv; OS QUE O PAINEL NAO
# MOSTRA ($ETEV06/07/09/10/13/14/31/40) VEM DO PPTC 0001-01 (../docs/firmware_reference.md)
LABELS = {
    '$ETEV01': 'Veículo Desbloqueado',   '$ETEV02': 'Veículo Bloqueado',
    '$ETEV03': 'Veículo ligado',         '$ETEV04': 'Veículo desligado',
    '$ETEV05': 'Sopro Realizado',        '$ETEV06': 'Falha de Comunicação',
    '$ETEV07': 'Parâmetros Atualizados', '$ETEV08': 'Dispositivo Inicializado',
    '$ETEV09': 'Sensor Inicializado',    '$ETEV10': 'Firmware Atualizado',
    '$ETEV11': 'Sem Sopro',              '$ETEV12': 'Teste Randômico',
    '$ETEV13': 'Sensor Quase Vencido',   '$ETEV14': 'Sensor Vencido (sopros)',
    '$ETEV15': 'Teste Adiado',           '$ETEV16': 'Teste Realizado',
    '$ETEV17': 'Início do Tempo de Manobra', '$ETEV18': 'Fim do Tempo de Manobra',
    '$ETEV20': 'Sensor Próximo do Vencimento', '$ETEV21': 'Sensor Vencido',
    '$ETEV22': 'Modo Manobrista Ativado', '$ETEV24': 'Sensor Defeituoso',
    '$ETEV25': 'Teste Randômico Realizado', '$ETEV26': 'Código Inserido',
    '$ETEV27': 'Temperatura Alta',       '$ETEV28': 'Temperatura Alta',
    '$ETEV29': 'Leitura Sem Álcool',     '$ETEV30': 'Álcool Detectado',
    '$ETEV31': 'Ignição em Veículo Leve',
    '$ETEV32': 'Desbloqueio em Modo Manobrista', '$ETEV33': 'Teste Randômico Não Realizado',
    '$ETEV34': 'Teste Randômico Adiado', '$ETEV35': 'Motorista Não Autorizado',
    '$ETEV36': 'Sensor Substituído',     '$ETEV37': 'Bloqueio Remoto',
    '$ETEV38': 'Desbloqueio Remoto',     '$ETEV39': 'Firmware Atualizado',
    '$ETEV40': 'Contrassenha Digitada',
}

# FORMATO DE EVENTO DO PROTOCOLO: $ETEVnn!, COM PAYLOAD NUMERICO OPCIONAL ($ETEV300021!).
# !ETEV23$ E O MODO MANOBRISTA DESATIVADO, QUE O FIRMWARE EMITE COM OS DELIMITADORES INVERTIDOS
EVENT = re.compile(r'^\$ETEV\d{2}\w*!$|^!ETEV23\$$')

# VOCABULARIO DA COLUNA category, DEFINIDO PELO USUARIO EM 21/09/2026
SEM_COMUNICACAO        = 'sem_comunicacao'
INSTALACAO_PENDENTE    = 'instalacao_pendente'
CALIBRACAO             = 'calibracao'
DEFEITO_APARELHO       = 'defeito_aparelho'
TESTE_INCONCLUSIVO     = 'teste_inconclusivo'
ALCOOL                 = 'alcool'
CONDUTA_MOTORISTA      = 'conduta_motorista'
CADASTRO_INCONSISTENTE = 'cadastro_inconsistente'
BURLA_BLOQUEIO         = 'burla_bloqueio'
FALHA_INTEGRACAO       = 'falha_integracao'
DADO_CORROMPIDO        = 'dado_corrompido'
FIRMWARE_DESATUALIZADO = 'firmware_desatualizado'


# TRADUZ O EVENTO CRU DO PROTOCOLO PARA O ROTULO QUE O PAINEL JA USA
def getLabel(event):
    code = (event or '')[:7]
    return LABELS.get(code, event)


# dd/mm/aaaa HH:MM A PARTIR DO ISO DA API
def getDate(value, hour=True):
    if not value:
        return '?'

    d = dt.datetime.fromisoformat(str(value).replace('Z', '+00:00')).replace(tzinfo=None)
    return d.strftime('%d/%m/%Y %H:%M' if hour else '%d/%m/%Y')


# NUMERO NO FORMATO BRASILEIRO: MILHAR COM PONTO, DECIMAL COM VIRGULA
def getNum(value, casas=0):
    return f'{value:,.{casas}f}'.translate(str.maketrans(',.', '.,'))


# DIAS INTEIROS ESCRITOS COMO UM HUMANO LE
def getAge(days):
    if days < 60:
        return f'{days} dias'

    years, rest = divmod(days, 365)
    months      = rest // 30

    if not years:
        return f'{months} meses'

    return f'{years} ano{"s" if years > 1 else ""}' + (f' e {months} meses' if months else '')


# 'v6.4.7' / '6.4.7' -> (6, 4, 7). '1.0.0' E O DEFAULT DO SERVIDOR PRA APARELHO QUE NUNCA
# REPORTOU VERSAO (SO REPORTA POR WI-FI), ENTAO NAO E VERSAO: VIRA None
def getVersion(value):
    parts = str(value or '').strip().lstrip('vV').split('.')

    if not all(p.isdigit() for p in parts) or len(parts) < 2:
        return None

    version = tuple(int(p) for p in parts)
    return None if version == (1, 0, 0) else version


# AUDITOR DA FROTA: LE, APLICA AS REGRAS E RECONCILIA A TABELA anomalies
class Scanner:
    MONTHS       = 3
    SILENCE      = 7
    SENSOR_DAYS  = 365
    SENSOR_BAD   = 730
    FLOOD        = 100
    POSTPONE     = 0.50
    NOBLOW       = 0.90
    MIN_TRIES    = 30
    UNAUTH       = 3      # $ETEV35 (motorista nao autorizado) na janela
    VALET        = 5      # $ETEV32 (partida em modo manobrista) na janela
    MIN_TESTS    = 10     # testes concluidos pra julgar se o resultado chega
    CLOCK        = 3      # logs com relogio do aparelho ausente/absurdo
    FIRMWARE_MIN = None   # ex.: '6.4.7'; None = linha major.minor da ultima release do catalogo
    PAGE         = 2000
    STATE        = os.path.join(HERE, 'state.json')
    CACHE        = os.path.join(HERE, 'logs.json')

    # A MIX SO REPASSA EVENTO PRO NOSSO SERVIDOR NESTAS EMPRESAS. NAS OUTRAS (MOSAIC, ATVOS…)
    # O VEICULO OPERA NORMALMENTE MAS O LOG NUNCA CHEGA — AUSENCIA DE LOG NAO E PROBLEMA LA.
    # SIGHIR E PREDILETO SAO DEFINICAO DO USUARIO; LOGIKA CONFIRMADA POR ELE EM 21/09/2026
    MIX_OK = {'EXPRESSO PREDILETO', 'SIGHIR ENTERPRISE LTDA', 'LOGIKA TRANSPORTES'}

    # EVENTOS DO PROTOCOLO QUE A MIX NUNCA REPASSOU EM NENHUM VEICULO (0 NA BASE INTEIRA):
    # RESULTADO DO TESTE, MOTORISTA NAO AUTORIZADO E SENSOR DEFEITUOSO. MEDIDO EM check()
    MIX_BLIND = ('$ETEV29', '$ETEV30', '$ETEV35', '$ETEV24')

    def __init__(self):
        self.now         = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None, microsecond=0)
        self.floor       = self.now - dt.timedelta(days=30 * self.MONTHS)
        self.state       = {}
        self.logs        = []
        self.fleet       = {}
        self.copies      = Counter()
        self.companies   = {}
        self.telemetries = set()
        self.firmwares   = []
        self.sensors     = {}
        self.vehicles    = {}
        self.spoke       = None
        self.ever        = {}
        self.problems    = defaultdict(lambda: defaultdict(list))
        self.gaps        = []
        self.changes     = []
        self.report      = Counter()

    # ESTADO DA VARREDURA ANTERIOR E CACHE DOS LOGS DA JANELA
    def get(self):
        if os.path.exists(self.STATE):
            self.state = json.load(open(self.STATE))

        if os.path.exists(self.CACHE):
            self.logs = json.load(open(self.CACHE))

        return bool(self.state)

    # LE FROTA E EMPRESAS DA API, E OS LOGS NOVOS DESDE A ULTIMA VARREDURA
    def update(self):
        companies        = api.getData('companies/', limit=500)
        self.companies   = {c['id']: c['label'] for c in companies}
        self.telemetries = {c['id'] for c in companies if c.get('type') == 'telemetry'}
        rows             = api.getData('etilometers/', limit=500)
        self.copies      = Counter(e['vehicle'] for e in rows)
        self.fleet       = {e['vehicle']: e for e in rows}

        # CATALOGO DE FIRMWARE DO SERVIDOR: A MAIOR VERSAO E A REFERENCIA DE "ATUAL"
        self.firmwares = [(getVersion(f.get('version')), f.get('version'), f.get('release_date'))
                          for f in api.getData('firmwares/', limit=500) if not f.get('deleted')]
        self.firmwares = sorted((f for f in self.firmwares if f[0]), reverse=True)

        # A JANELA SO ANDA PRA FRENTE; 3 MESES E TETO ABSOLUTO, NUNCA LEIO ALEM DELE
        last  = self.state.get('last_run')
        start = max(dt.datetime.fromisoformat(last), self.floor) if last else self.floor

        # LOG DA BORDA APARECE NAS DUAS JANELAS PORQUE start E gte, ENTAO DEDUPLICO POR id
        rows = api.getData('logs/',
                           start=start.strftime('%Y-%m-%d %H:%M:%S'),
                           end=self.now.strftime('%Y-%m-%d %H:%M:%S'),
                           limit=self.PAGE)

        seen      = {r['k'] for r in self.logs}
        novos     = [r for r in map(self.getRow, rows) if r['k'] not in seen]
        self.logs = [r for r in self.logs + novos if r['t'] >= self.floor.isoformat()]

        self.report['logs_novos']  = len(novos)
        self.report['logs_janela'] = len(self.logs)
        self.report['frota']       = len(self.fleet)

    # SO GUARDO O QUE AS REGRAS LEEM, PRA O CACHE NAO VIRAR UMA COPIA DO BANCO.
    # LogSerializer NAO EXPOE id, ENTAO A CHAVE E NATURAL: NOS 230 MIL LOGS DA BASE
    # timestamp SOZINHO JA E UNICO (auto_now_add COM MICROSSEGUNDO), placa+evento SO REFORCAM.
    # 'c' E O RELOGIO DO APARELHO (created_at), SO LIDO PELA REGRA DE RELOGIO — NUNCA PRA ORDENAR
    def getRow(self, row):
        v = row.get('vehicle') or ''
        e = row.get('event') or ''
        t = (row.get('timestamp') or '').replace('Z', '')
        c = (row.get('created_at') or '').replace('Z', '')
        return {'k': f'{v}|{e}|{t}', 'v': v, 'e': e, 't': t, 'c': c}

    # SENSOR E CALIBRACAO VEM DA API: sensors/<id>.timestamp E A DATA DA CALIBRACAO CORRENTE
    # (CONFERIDO EM 21/09/2026: BATE COM max(Etilometros_calibration.timestamp) NOS 131 SENSORES).
    # ASSIM UMA CALIBRACAO FEITA HOJE RESOLVE O ALERTA HOJE, SEM ESPERAR SNAPSHOT NOVO
    def getSensors(self):
        try:
            sensors = {s['id']: (s.get('timestamp') or '').replace('Z', '')
                       for s in api.getData('sensors/', limit=self.PAGE) if not s.get('deleted')}

            for plate, e in self.fleet.items():
                sensor = e.get('sensor_id')

                if sensor:
                    self.sensors[plate] = (sensor, sensors.get(sensor) or None)
        except RuntimeError as err:
            self.gaps.append(f'sensors/ indisponível ({str(err)[:80]}) — usando o snapshot')

        # O SNAPSHOT SO SERVE PRA CAIXA DA PLACA (Vehicle NAO TEM ROTA) E COMO RESERVA DOS SENSORES
        if not os.path.exists(SNAPSHOT):
            if not self.sensors:
                self.gaps.append('sem sensors/ e sem snapshot — regras de sensor não rodaram')
            return

        db = sqlite3.connect(SNAPSHOT)

        if not self.sensors:
            cal = dict(db.execute('select product_num, max(timestamp) from Etilometros_calibration group by product_num'))

            # DESDE A MIGRACAO DE 24/09/2026 A INSTALACAO E O PROPRIO Device (plate_id -> Vehicle);
            # Etilometros_etilometro FICOU CONGELADA EM 18/09/2026
            for plate, sensor in db.execute('''select v.plate, d.sensor_id
                                               from Etilometros_device d
                                               join Etilometros_vehicle v on v.id = d.plate_id'''):
                self.sensors[plate] = (sensor, cal.get(sensor))

            idade = (self.now - dt.datetime.fromtimestamp(os.path.getmtime(SNAPSHOT))).days

            if idade > 30:
                self.gaps.append(f'snapshot com {idade} dias — validade de sensor pode estar desatualizada')

        # Anomaly.vehicle E FK PRA Vehicle.plate, QUE NEM SEMPRE BATE COM Etilometro.vehicle_plate
        # (CAIXA DIFERENTE). SEM SNAPSHOT, write() TENTA A PLACA EM MAIUSCULAS QUANDO O POST RECUSA
        self.vehicles = {p.upper(): p for (p,) in db.execute('select plate from Etilometros_vehicle where deleted = 0')}
        db.close()

    # MIX FORA DA SIGHIR/PREDILETO: O VEICULO OPERA, MAS NENHUM EVENTO CHEGA AO SERVIDOR
    def isMute(self, plate):
        e = self.fleet[plate]
        return 'MIX' in (e.get('telemetry_label') or '').upper() \
            and self.companies.get(e.get('company')) not in self.MIX_OK

    def add(self, plate, category, text):
        self.problems[plate][category].append(text)

    # APLICA AS REGRAS SOBRE A JANELA E MONTA UM BLOCO DE TEXTO POR PROBLEMA
    def check(self):
        ultimo = {}
        evento = {}
        conta  = defaultdict(Counter)
        alcool = {}
        zero   = defaultdict(list)
        ruim   = defaultdict(list)
        relog  = defaultdict(list)
        seq    = defaultdict(list)
        mix    = Counter()

        for row in self.logs:
            plate = row['v']

            if not plate:
                continue

            code = row['e'][:7]
            conta[plate][code] += 1
            seq[plate].append((row['t'], code))

            if plate not in ultimo or row['t'] > ultimo[plate]:
                ultimo[plate] = row['t']
                evento[plate] = row['e']

            # $ETEV300000! E "ALCOOL DETECTADO" COM 0,000 mg/L: O FIRMWARE SO PRODUZ ISSO
            # QUANDO O SENSOR NAO TEM COEFICIENTES DE CALIBRACAO — NAO E LEITURA, E DADO RUIM
            if code == '$ETEV30':
                payload = row['e'].strip('!')[7:]

                if payload and not payload.strip('0'):
                    zero[plate].append(row['t'])
                elif row['t'] > alcool.get(plate, ''):
                    alcool[plate] = row['t']

            if not EVENT.match(row['e']):
                ruim[plate].append(row['e'])

            # 'c' SO EXISTE EM LOG BAIXADO DEPOIS DE 21/09/2026; SEM A CHAVE, NAO JULGO
            if 'c' in row and (not row['c'] or row['c'] < '2020'):
                relog[plate].append(row['c'] or 'ausente')

            if plate in self.fleet and 'MIX' in (self.fleet[plate].get('telemetry_label') or '').upper():
                mix[code] += 1

        # fleet E UM DICT POR PLACA, ENTAO A DUPLICATA JA COLAPSOU NELE: A CONTAGEM VEM DA LISTA CRUA
        plates = self.copies or Counter(self.fleet.keys())

        for plate in self.fleet:
            mute = self.isMute(plate)
            self.report['mudos'] += mute

            # AUSENCIA DE LOG SO E EVIDENCIA ONDE O LOG TERIA COMO CHEGAR
            if not mute:
                self.checkSilence(plate, ultimo.get(plate), evento.get(plate), conta[plate])
                self.checkConduct(plate, conta[plate])

            self.checkSensor(plate)
            self.checkFlood(plate, conta[plate])
            self.checkAlcohol(plate, conta[plate], alcool.get(plate), len(zero[plate]))
            self.checkRegistry(plate, plates[plate])
            self.checkBypass(plate, conta[plate], sorted(seq[plate]))
            self.checkIntegration(plate, conta[plate])
            self.checkData(plate, zero[plate], ruim[plate], relog[plate])
            self.checkFirmware(plate, conta[plate])

        # O QUE A MIX NAO REPASSA EM VEICULO NENHUM E LIMITE DA INTEGRACAO, NAO DE UM VEICULO
        if sum(mix.values()) >= 1000:
            cegos = [f'{getLabel(c)} ({c}!)' for c in self.MIX_BLIND if not mix[c]]

            if cegos:
                self.gaps.append(f'a MiX não repassou {", ".join(cegos)} em nenhum veículo na janela '
                                 f'({getNum(sum(mix.values()))} logs MiX) — álcool, condução não autorizada e '
                                 f'sensor defeituoso são invisíveis nos veículos MiX')

        self.report['achados'] = sum(len(t) for cats in self.problems.values() for t in cats.values())
        self.report['linhas']  = sum(len(cats) for cats in self.problems.values())

        # PLACA QUE A API CONHECE MAS O SNAPSHOT NAO: SEM SENSOR, A REGRA DE VALIDADE NAO RODA
        orfas = [p for p in self.fleet if p not in self.sensors]

        if orfas and self.sensors:
            self.gaps.append(f'{len(orfas)} etilômetros sem sensor no snapshot — validade não avaliada '
                             f'({", ".join(sorted(orfas)[:5])}{"…" if len(orfas) > 5 else ""})')

    # SILENCIO, NUNCA FALOU, E SUMIU ANTES DA JANELA — TRES ESTADOS DO MESMO EIXO
    def checkSilence(self, plate, last, event, counter):
        inst = getDate(self.fleet[plate].get('installation_date'), hour=False)

        if not last:
            if self.getEver(plate):
                self.add(plate, SEM_COMUNICACAO,
                    f'[SUMIU ANTES DA JANELA] Nenhum log nos últimos {self.MONTHS} meses, mas o veículo já '
                    f'enviou logs no passado. Parou antes de {getDate(self.floor.isoformat(), hour=False)} — '
                    f'a janela de {self.MONTHS} meses não alcança a data em que parou.')
            else:
                self.add(plate, INSTALACAO_PENDENTE,
                    f'[NUNCA ENVIOU LOG] Etilômetro cadastrado em {inst}, sem um único log em toda a base. '
                    f'Ou a instalação nunca foi concluída, ou o cadastro não corresponde a um veículo em operação.')
            return

        days = (self.now - dt.datetime.fromisoformat(last)).days

        if days < self.SILENCE:
            return

        ritmo = len(self.logs) and round(sum(counter.values()) / max((self.MONTHS * 30) - days, 1), 1)

        self.add(plate, SEM_COMUNICACAO,
            f'[SILÊNCIO — {getAge(days)}] Sem enviar log desde {getDate(last)}. '
            f'Último evento: {getLabel(event)} ({event}). '
            f'Antes disso enviava ~{getNum(ritmo, 1)} logs/dia ({getNum(sum(counter.values()))} na janela de {self.MONTHS} meses).')

    # VALIDADE DE 1 ANO A PARTIR DA ULTIMA CALIBRACAO, MESMO CRITERIO QUE O PAINEL JA APLICA
    def checkSensor(self, plate):
        sensor, last = self.sensors.get(plate, (None, None))

        if not sensor:
            return

        if not last:
            self.add(plate, CALIBRACAO,
                '[SENSOR SEM CALIBRAÇÃO] O sensor deste veículo não tem nenhuma calibração registrada. '
                'O painel mostra esse caso como "A Vencer" por falta de data, o que esconde o problema.')
            return

        days = (self.now - dt.datetime.fromisoformat(last)).days

        if days <= self.SENSOR_DAYS:
            return

        grave = ' Mais que o dobro da validade. Grave.' if days > self.SENSOR_BAD else ''

        self.add(plate, CALIBRACAO,
            f'[SENSOR VENCIDO — {getAge(days)}] Última calibração do sensor {sensor} em '
            f'{getDate(last, hour=False)}. Vencido há {getAge(days - self.SENSOR_DAYS)} '
            f'(validade de 1 ano).{grave}')

    # ENXURRADA DE FALHA DE SENSOR: PRESENCA DE EVENTO, VALE MESMO ONDE A MIX NAO REPASSA O RESTO
    def checkFlood(self, plate, counter):
        flood = counter['$ETEV24']

        if flood < self.FLOOD:
            return

        self.add(plate, DEFEITO_APARELHO,
            f'[SENSOR DEFEITUOSO] {getNum(flood)} eventos {getLabel("$ETEV24")} ($ETEV24!) na janela de {self.MONTHS} meses — '
            f'{round(100 * flood / max(sum(counter.values()), 1))}% de tudo que este veículo enviou. '
            f'O firmware entra em laço sem saída quando a EEPROM do sensor não responde '
            f'(objects/sensors/alcohol/index.h): até a v6.4.7 emite o evento a cada tentativa (~1,5 s), '
            f'da v6.4.8 em diante no máximo um a cada 10 min.')

    # SOPRO QUE NUNCA CONCLUI E ADIAMENTO SISTEMATICO — DEPENDEM DE CONTAR O QUE NAO ACONTECEU
    def checkConduct(self, plate, counter):
        tries = counter['$ETEV11'] + counter['$ETEV05']

        if tries >= self.MIN_TRIES and counter['$ETEV11'] / tries >= self.NOBLOW:
            self.add(plate, TESTE_INCONCLUSIVO,
                f'[SOPRO NUNCA CONCLUÍDO] {getNum(counter["$ETEV11"])} de {getNum(tries)} tentativas terminaram em '
                f'{getLabel("$ETEV11")} ($ETEV11!), {round(100 * counter["$ETEV11"] / tries)}%. '
                f'Testes concluídos na janela: {getNum(counter["$ETEV16"])}. O log não distingue sensor que não lê '
                f'de motorista que não sopra — precisa de verificação em campo.')

        total = counter['$ETEV15'] + counter['$ETEV05']

        if total >= self.MIN_TRIES and counter['$ETEV15'] / total >= self.POSTPONE:
            self.add(plate, CONDUTA_MOTORISTA,
                f'[ADIAMENTO EXCESSIVO] Adia {round(100 * counter["$ETEV15"] / total)}% dos testes '
                f'({getNum(counter["$ETEV15"])} adiamentos contra {getNum(counter["$ETEV16"])} testes realizados '
                f'na janela de {self.MONTHS} meses). O limite de adiamentos (max_postpone) é configuração por '
                f'aparelho que eu não leio — pode ser abuso ou pode ser a configuração permitindo.')

    # ALCOOL DETECTADO E FATO, NAO SUSPEITA: UMA LEITURA JA BASTA. LEITURA COM 0,000 mg/L NAO
    # CONTA (VAI PRA dado_corrompido), ENTAO last SO EXISTE SE HOUVE LEITURA COM VALOR
    def checkAlcohol(self, plate, counter, last, zeros=0):
        n = counter['$ETEV30'] - zeros

        if n <= 0 or not last:
            return

        self.add(plate, ALCOOL,
            f'[ÁLCOOL DETECTADO] {getNum(n)} leitura{"s" if n > 1 else ""} {getLabel("$ETEV30")} ($ETEV30!) '
            f'na janela de {self.MONTHS} meses, a última em {getDate(last)}. '
            f'Testes realizados no período: {getNum(counter["$ETEV16"])}.')

    # PLACA DUPLICADA E TELEMETRIA QUE NAO E TELEMETRIA
    def checkRegistry(self, plate, copies):
        e = self.fleet[plate]

        if copies > 1:
            self.add(plate, CADASTRO_INCONSISTENTE,
                f'[PLACA DUPLICADA] Esta placa tem {copies} etilômetros cadastrados. Como os logs e os alertas '
                f'são por placa, os problemas dos dois aparelhos se misturam numa leitura só.')

        tel = e.get('telemetry')

        if not tel:
            self.add(plate, CADASTRO_INCONSISTENTE,
                '[SEM TELEMETRIA] O etilômetro não tem telemetria cadastrada — sem ela, nenhum evento tem por onde chegar.')
        elif self.telemetries and tel not in self.telemetries:
            self.add(plate, CADASTRO_INCONSISTENTE,
                f'[TELEMETRIA INVÁLIDA] A telemetria cadastrada é "{e.get("telemetry_label") or tel}", '
                f'que é uma transportadora, não uma empresa de telemetria.')

    # O VEICULO CIRCULOU SEM PASSAR NO TESTE. $ETEV35 SAI EM objects/test/index.h:117 QUANDO O TESTE
    # TERMINA EM ALCOOL OU SEM SOPRO COM O VEICULO JA EM CONDUCAO (NA PRATICA: DEPOIS DE ADIAR, QUE
    # LIBERA O VEICULO E MARCA driving) — O ALARME SOA ATE A IGNICAO DESLIGAR E SO ENTAO BLOQUEIA.
    # $ETEV32 SAI EM objects/vehicle/valet/index.h:59: PARTIDA SEM TESTE COM MODO MANOBRISTA ATIVO
    def checkBypass(self, plate, counter, seq):
        n = counter['$ETEV35']

        if n >= self.UNAUTH:
            alcool = sopro = adiou = 0
            last   = None

            for i, (t, code) in enumerate(seq):
                if code != '$ETEV35':
                    continue

                antes = [c for _, c in seq[max(0, i - 6):i]]
                last  = t

                if '$ETEV30' in antes:
                    alcool += 1
                elif '$ETEV11' in antes:
                    sopro += 1

                if '$ETEV15' in antes or '$ETEV34' in antes:
                    adiou += 1

            self.add(plate, BURLA_BLOQUEIO,
                f'[CONDUÇÃO NÃO AUTORIZADA] {getNum(n)} vezes {getLabel("$ETEV35")} ($ETEV35!) na janela de '
                f'{self.MONTHS} meses: o veículo já estava em condução quando o teste terminou em '
                f'{getLabel("$ETEV30")} ({getNum(alcool)}) ou {getLabel("$ETEV11")} ({getNum(sopro)}). '
                f'{getNum(adiou)} vieram depois de um {getLabel("$ETEV15")} ($ETEV15!): o motorista adia, '
                f'dirige e ignora o teste quando ele volta. O aparelho soa o alarme até a ignição desligar '
                f'e só então bloqueia. Testes concluídos no período: {getNum(counter["$ETEV16"] + counter["$ETEV25"])}. '
                f'Última em {getDate(last)}.')

        n = counter['$ETEV32']

        if n >= self.VALET:
            testes = counter['$ETEV16'] + counter['$ETEV25']

            self.add(plate, BURLA_BLOQUEIO,
                f'[MODO MANOBRISTA] {getNum(n)} partidas sem teste em modo manobrista ($ETEV32!) contra '
                f'{getNum(testes)} testes realizados na janela de {self.MONTHS} meses — '
                f'{round(100 * n / max(n + testes, 1))}% das liberações. O modo é de uso administrativo, '
                f'ativado pelo menu do aparelho ({getLabel("$ETEV22")}, $ETEV22!: {getNum(counter["$ETEV22"])} vezes).')

    # TESTE CONCLUIDO SEM RESULTADO: O FIRMWARE EMITE $ETEV29/$ETEV30 ANTES DE CADA $ETEV16/$ETEV25
    # (objects/test/index.h:183 e :84). SE CHEGA O TESTE E NUNCA O RESULTADO, A TELEMETRIA ESTA
    # FILTRANDO O PROTOCOLO — E ALCOOL DETECTADO NESSE VEICULO NAO EXISTE PRO SERVIDOR
    def checkIntegration(self, plate, counter):
        testes = counter['$ETEV16'] + counter['$ETEV25']

        if testes < self.MIN_TESTS or counter['$ETEV29'] + counter['$ETEV30']:
            return

        e     = self.fleet[plate]
        tel   = (e.get('telemetry_label') or '').upper()
        texto = (f'[RESULTADO NÃO CHEGA] {getNum(testes)} testes concluídos ($ETEV16!/$ETEV25!) na janela de '
                 f'{self.MONTHS} meses e nenhum resultado ({getLabel("$ETEV29")}/{getLabel("$ETEV30")}, '
                 f'$ETEV29!/$ETEV30!). O aparelho emite o resultado antes de todo teste concluído, então a '
                 f'telemetria está filtrando o protocolo: álcool detectado neste veículo é invisível pro servidor.')

        if not counter['$ETEV01'] and not counter['$ETEV02']:
            texto += (f' Também não chegam {getLabel("$ETEV01")}/{getLabel("$ETEV02")} ($ETEV01!/$ETEV02!) — '
                      f'o bloqueio não pode ser auditado.')

        if 'MIX' not in tel:
            texto += (f' O cadastro diz {e.get("telemetry_label") or "?"}, que repassa o protocolo inteiro; '
                      f'esse padrão é o da MiX — confira a telemetria cadastrada.')

        self.add(plate, FALHA_INTEGRACAO, texto)

    # DADO QUE SE CONTRADIZ OU NAO SEGUE O PROTOCOLO. NENHUM DESTES AFETA OS OUTROS ALERTAS:
    # TODA REGRA USA A HORA DE CHEGADA NO SERVIDOR E O CODIGO DO EVENTO, NAO O PAYLOAD
    def checkData(self, plate, zeros, bad, clock):
        if zeros:
            self.add(plate, DADO_CORROMPIDO,
                f'[ÁLCOOL COM VALOR ZERO] {getNum(len(zeros))} leitura{"s" if len(zeros) > 1 else ""} '
                f'{getLabel("$ETEV30")} com 0,000 mg/L ($ETEV300000!) na janela de {self.MONTHS} meses, a última em '
                f'{getDate(max(zeros))}. O firmware só produz esse valor quando o sensor não tem coeficientes '
                f'de calibração gravados (objects/test/index.h: sem coefs, o modelo decide sem concentração). '
                f'Não contei como álcool — a leitura não sustenta a própria detecção. Confira a calibração do sensor.')

        if bad:
            exemplos = ', '.join(repr(b) for b in sorted(set(bad))[:4])
            self.add(plate, DADO_CORROMPIDO,
                f'[EVENTO MALFORMADO] {getNum(len(bad))} log{"s" if len(bad) > 1 else ""} fora do formato do '
                f'protocolo ($ETEVnn!) na janela de {self.MONTHS} meses, como {exemplos}. Nenhuma regra consegue '
                f'ler esses logs — se persistir, a linha serial ou a telemetria está corrompendo o texto.')

        if len(clock) >= self.CLOCK:
            self.add(plate, DADO_CORROMPIDO,
                f'[RELÓGIO DO APARELHO] {getNum(len(clock))} logs com data do aparelho ausente ou anterior a 2020 '
                f'(ex.: {clock[0][:10]}) na janela de {self.MONTHS} meses — RTC sem sincronizar. Os alertas usam a '
                f'hora de chegada no servidor e não são afetados, mas o painel mostra a data errada nesses eventos.')

    # A VERSAO VEM DE Device.software_version, QUE O APARELHO SO ATUALIZA QUANDO CONSULTA
    # check-update POR WI-FI: '1.0.0' E O DEFAULT DE QUEM NUNCA REPORTOU, NAO E VERSAO
    def checkFirmware(self, plate, counter):
        if not self.firmwares:
            return

        atual   = self.firmwares[0]
        version = getVersion(self.fleet[plate].get('software_version'))

        if not version:
            self.report['sem_versao'] += 1
            return

        minimo = getVersion(self.FIRMWARE_MIN) or atual[0][:2] + (0,)

        if version >= minimo:
            return

        texto = (f'[FIRMWARE ANTIGO] O aparelho reporta a versão {self.fleet[plate]["software_version"]}; a atual é '
                 f'{atual[1]} ({getDate(atual[2], hour=False)}). ')

        if self.FIRMWARE_MIN:
            texto += f'Mínimo aceito: {self.FIRMWARE_MIN}. '
        else:
            linhas = len({f[0][:2] for f in self.firmwares if version[:2] < f[0][:2] <= atual[0][:2]})
            texto += f'Está {linhas} linha{"s" if linhas > 1 else ""} atrás ({".".join(map(str, version[:2]))} → {".".join(map(str, atual[0][:2]))}). '

        texto += ('A versão só chega ao servidor quando o aparelho consulta atualização por Wi-Fi, então pode '
                  'estar defasada — confirme na tela ID do aparelho.')

        if counter['$ETEV10']:
            texto += (f' Este veículo enviou {getLabel("$ETEV10")} ($ETEV10!) {getNum(counter["$ETEV10"])} vez'
                      f'{"es" if counter["$ETEV10"] > 1 else ""} na janela — pode já estar em versão mais nova.')

        self.add(plate, FIRMWARE_DESATUALIZADO, texto)

    # O SNAPSHOT E A UNICA FONTE QUE ENXERGA LOG ANTERIOR A JANELA.
    # UMA VARREDURA SO: POR PLACA SERIAM 76 JOINS NUMA TABELA DE 230 MIL LINHAS SEM INDICE
    def getEver(self, plate):
        if self.spoke is None and os.path.exists(SNAPSHOT):
            db = sqlite3.connect(SNAPSHOT)
            self.spoke = {p for (p,) in db.execute(
                '''select distinct e.vehicle_plate from Etilometros_log l
                   join Etilometros_etilometro e on e.id = l.etilometro_id''')}
            db.close()

        if self.spoke is not None:
            return plate in self.spoke

        # SEM SNAPSHOT, UMA CONSULTA DE 1 LOG POR PLACA MUDA NA JANELA (~40 REQUISICOES)
        if plate not in self.ever:
            self.ever[plate] = bool(api.get('logs/', vehicle=plate, limit=1).get('count'))

        return self.ever[plate]

    # O TEXTO QUE VAI PRA COLUNA desc: UMA LINHA POR (PLACA, CATEGORIA), LIDA SEM ABRIR O BANCO
    def getDesc(self, plate, category):
        return '\n\n'.join(self.problems[plate][category])

    # A PLACA COMO Vehicle A CONHECE (A CAIXA PODE DIFERIR DA DO ETILOMETRO). PLACA QUE O SNAPSHOT
    # NAO CONHECE VAI COMO ESTA: O USUARIO PEDIU (21/09/2026) QUE A PLACA SEJA PREENCHIDA NORMALMENTE,
    # E O SERVIDOR E QUEM DECIDE — SE RECUSAR COM 400, write() REGISTRA A LACUNA E SEGUE
    def getVehicle(self, plate):
        return self.vehicles.get(plate.upper(), plate)

    # RECONCILIA NOS DOIS SENTIDOS: CRIA, ATUALIZA, E MARCA COMO RESOLVIDO O QUE SUMIU.
    # LINHA RESOLVIDA E HISTORICO: NUNCA E REABERTA, O MESMO PROBLEMA DE NOVO VIRA LINHA NOVA
    def send(self, dry=True):
        aberto   = {}
        fechado  = set()

        for row in api.getData('anomalies/', limit=self.PAGE):
            if row.get('deleted'):
                continue

            key = (row['vehicle'], row.get('category') or '')

            if row.get('solved'):
                fechado.add(key + (row.get('desc') or '',))
            else:
                aberto.setdefault(key, []).append(row)

        for plate in sorted(self.problems):
            vehicle = self.getVehicle(plate)

            for category in sorted(self.problems[plate]):
                desc = self.getDesc(plate, category)
                rows = aberto.pop((vehicle, category), [])

                if not rows:
                    # ALGUEM MARCOU COMO RESOLVIDO NO PAINEL E NADA MUDOU DESDE ENTAO (MESMO TEXTO):
                    # A DECISAO DELE VALE. SO NASCE LINHA NOVA QUANDO A EVIDENCIA MUDAR
                    if (vehicle, category, desc) in fechado:
                        self.report['mantidos'] += 1
                        continue

                    self.changes.append(('criado', plate, category, desc))
                    self.write(dry, 'POST', 'anomalies/', {'vehicle': vehicle, 'category': category, 'desc': desc}, plate)
                    continue

                # MAIS DE UMA LINHA ABERTA PRO MESMO PAR E RESIDUO: MANTENHO A PRIMEIRA, FECHO O RESTO
                for extra in rows[1:]:
                    self.solve(dry, extra, plate)

                if rows[0]['desc'] != desc:
                    self.write(dry, 'PATCH', f'anomalies/{rows[0]["id"]}/', {'desc': desc}, plate)
                else:
                    self.report['iguais'] += 1

        # SOBROU ABERTO E NAO TEM MAIS PROBLEMA (OU SAIU DA FROTA) -> RESOLVIDO
        for (plate, _), rows in aberto.items():
            for row in rows:
                self.solve(dry, row, plate)

        if self.report['sem_versao']:
            self.gaps.append(f'{self.report["sem_versao"]} aparelhos nunca reportaram versão de firmware '
                             f'(software_version = 1.0.0, só atualiza por Wi-Fi) — firmware não avaliado neles')

    def solve(self, dry, row, plate):
        self.report['solved'] += 1
        self.changes.append(('resolvido', plate, row.get('category') or '', row.get('desc') or ''))
        self.write(dry, 'PATCH', f'anomalies/{row["id"]}/', {'solved': True}, plate, count=False)

    # UMA UNICA PORTA DE ESCRITA, PRA O MODO SECO NAO PRECISAR SER LEMBRADO EM CADA CHAMADA.
    # 400 E ERRO DE DADO DE UMA PLACA, NAO DA VARREDURA: REGISTRO A LACUNA E SIGO
    def write(self, dry, method, endpoint, data, plate, count=True):
        if count:
            self.report[method.lower()] += 1

        if dry:
            return

        try:
            api.send(method, endpoint, data)
        except RuntimeError as e:
            if '-> 400' not in str(e):
                raise

            # Vehicle.plate PODE ESTAR EM OUTRA CAIXA (Mosaic -> MOSAIC): UMA SEGUNDA TENTATIVA
            vehicle = (data or {}).get('vehicle') or ''

            if 'plate=' in str(e) and vehicle != vehicle.upper():
                return self.write(dry, method, endpoint, dict(data, vehicle=vehicle.upper()), plate, count=False)

            self.report['falhas'] += 1
            self.gaps.append(f'{plate}: {method} recusado — {str(e).split(": ", 1)[-1][:160]}')

            # RECUSADO NAO NASCEU: SAI DA LISTA DE MUDANCAS, FICA SO NA LACUNA
            self.changes = [c for c in self.changes if not (c[1] == plate and c[3] == (data or {}).get('desc'))]

    # ESTADO E CACHE SO GRAVAM DEPOIS QUE A ESCRITA DEU CERTO, SENAO A JANELA PULA LOG
    def set(self):
        json.dump({'last_run': self.now.isoformat(),
                   'janela':   [self.floor.isoformat(), self.now.isoformat()],
                   'logs':     len(self.logs)}, open(self.STATE, 'w'), indent=2)

        json.dump(self.logs, open(self.CACHE, 'w'))

    # RELATORIO DA EXECUCAO, INCLUINDO O QUE NAO FOI ALCANCADO E POR QUE
    def showInfo(self, dry):
        r = self.report
        print(f'\njanela: {getDate(self.floor.isoformat(), hour=False)} a {getDate(self.now.isoformat(), hour=False)}'
              f'  ({self.MONTHS} meses, teto absoluto)')
        print(f'frota: {r["frota"]} etilômetros | logs novos: {r["logs_novos"]} | logs na janela: {r["logs_janela"]}')
        print(f'MiX fora de {"/".join(sorted(self.MIX_OK))}: {r["mudos"]} veículos — regras de ausência de log não rodam neles')
        print(f'achados: {r["achados"]} em {r["linhas"]} linhas (placa × categoria), {len(self.problems)} veículos')

        regras = Counter(t[1:t.index(']')].split(' —')[0]
                         for cats in self.problems.values() for texts in cats.values() for t in texts)
        cats   = Counter(c for cats in self.problems.values() for c in cats)

        for regra, n in regras.most_common():
            print(f'  {regra:24} {n:4}')

        print('\npor categoria:')
        for cat, n in cats.most_common():
            print(f'  {cat:24} {n:4}')

        print(f'\ntabela anomalies{"  [MODO SECO — nada foi escrito]" if dry else ""}:')
        print(f'  criar      {r["post"]:5}')
        print(f'  atualizar  {r["patch"]:5}')
        print(f'  resolver   {r["solved"]:5}')
        print(f'  inalterado {r["iguais"]:5}')

        if r['mantidos']:
            print(f'  mantido resolvido {r["mantidos"]:5}   (resolvido no painel, evidência não mudou)')

        if r['falhas']:
            print(f'  recusado   {r["falhas"]:5}')

        # O QUE NASCEU E O QUE FECHOU, PRA O RELATORIO DO CHECK CITAR PLACA POR PLACA
        if self.changes:
            print('\nmudanças (placa, categoria, regra):')

            for kind, plate, category, desc in self.changes[:60]:
                label = desc[1:desc.index(']')] if desc.startswith('[') and ']' in desc else desc[:30]
                print(f'  {kind:10} {plate:14} {category:24} {label}')

            if len(self.changes) > 60:
                print(f'  … e mais {len(self.changes) - 60}')

        print('\nnão alcançado:')
        for gap in self.gaps or ['(nada)']:
            print(f'  - {gap}')

    # PIPELINE COMPLETO. dry=True NAO ESCREVE NADA, SO MOSTRA O QUE SAIRIA
    def start(self, dry=True):
        self.get()
        self.update()
        self.getSensors()
        self.check()

        # DESDE 24/09/2026 A API DEVOLVE TODO LOG (O FILTRO etilometer__is_active SAIU), MAS LOG COM
        # device NULO CHEGA SEM PLACA E NAO TEM VEICULO A QUEM ATRIBUIR
        orfaos = sum(1 for r in self.logs if not r['v'])
        if orfaos:
            self.gaps.append(f'{orfaos} logs da janela ({orfaos / max(len(self.logs), 1):.1%}) chegam sem placa '
                             f'(log sem aparelho vinculado) — não entram em nenhuma regra')
        self.send(dry)

        # O CACHE DE LOG NAO DEPENDE DE TER ESCRITO NA TABELA: GRAVA SEMPRE, PRA CONFERENCIA
        # EM MODO SECO NAO REBAIXAR 3 MESES DE PRODUCAO A CADA VEZ
        self.set()
        self.showInfo(dry)
        return self


scanner = Scanner()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--write', action='store_true', help='escreve de verdade na tabela anomalies')
    parser.add_argument('--show', metavar='PLACA', help='mostra os desc que sairiam para uma placa')
    args = parser.parse_args()

    scanner.start(dry=not args.write)

    if args.show:
        print('\n' + '-' * 70)

        if args.show not in scanner.problems:
            print(f'{args.show}: sem problemas')

        for category in sorted(scanner.problems.get(args.show, {})):
            print(f'[{category}]\n{scanner.getDesc(args.show, category)}\n')
