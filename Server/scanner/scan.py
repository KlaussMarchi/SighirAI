import os
import json
import sqlite3
import argparse
import datetime as dt
from collections import Counter, defaultdict

from api import api


HERE     = os.path.dirname(os.path.abspath(__file__))
SNAPSHOT = os.path.join(HERE, '..', 'docs', 'ServerAnalysis', 'files', 'db.sqlite3')

# ROTULOS DO PAINEL, EXTRAIDOS DOS Monitoramento_Inicio_a_Fim*.csv
LABELS = {
    '$ETEV01': 'Veículo Desbloqueado',   '$ETEV02': 'Veículo Bloqueado',
    '$ETEV03': 'Veículo ligado',         '$ETEV04': 'Veículo desligado',
    '$ETEV05': 'Sopro Realizado',        '$ETEV08': 'Dispositivo Inicializado',
    '$ETEV11': 'Sem Sopro',              '$ETEV12': 'Teste Randômico',
    '$ETEV15': 'Teste Adiado',           '$ETEV16': 'Teste Realizado',
    '$ETEV17': 'Início do Tempo de Manobra', '$ETEV18': 'Fim do Tempo de Manobra',
    '$ETEV20': 'Sensor Próximo do Vencimento', '$ETEV21': 'Sensor Vencido',
    '$ETEV22': 'Modo Manobrista Ativado', '$ETEV24': 'Sensor Defeituoso',
    '$ETEV25': 'Teste Randômico Realizado', '$ETEV26': 'Código Inserido',
    '$ETEV27': 'Temperatura Alta',       '$ETEV28': 'Temperatura Alta',
    '$ETEV29': 'Leitura Sem Álcool',     '$ETEV30': 'Álcool Detectado',
    '$ETEV32': 'Desbloqueio em Modo Manobrista', '$ETEV33': 'Teste Randômico Não Realizado',
    '$ETEV34': 'Teste Randômico Adiado', '$ETEV35': 'Motorista Não Autorizado',
    '$ETEV36': 'Sensor Substituído',     '$ETEV37': 'Bloqueio Remoto',
    '$ETEV38': 'Desbloqueio Remoto',     '$ETEV39': 'Firmware Atualizado',
}


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


# AUDITOR DA FROTA: LE, APLICA AS REGRAS E RECONCILIA A TABELA anomalies
class Scanner:
    MONTHS      = 3
    SILENCE     = 7
    SENSOR_DAYS = 365
    SENSOR_BAD  = 730
    FLOOD       = 100
    POSTPONE    = 0.50
    NOBLOW      = 0.90
    MIN_TRIES   = 30
    PAGE        = 2000
    STATE       = os.path.join(HERE, 'state.json')
    CACHE       = os.path.join(HERE, 'logs.json')

    def __init__(self):
        self.now       = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None, microsecond=0)
        self.floor     = self.now - dt.timedelta(days=30 * self.MONTHS)
        self.state     = {}
        self.logs      = []
        self.fleet     = {}
        self.companies = {}
        self.sensors   = {}
        self.spoke     = None
        self.problems  = defaultdict(list)
        self.notes     = defaultdict(list)
        self.gaps      = []
        self.report    = Counter()

    # ESTADO DA VARREDURA ANTERIOR E CACHE DOS LOGS DA JANELA
    def get(self):
        if os.path.exists(self.STATE):
            self.state = json.load(open(self.STATE))

        if os.path.exists(self.CACHE):
            self.logs = json.load(open(self.CACHE))

        return bool(self.state)

    # LE FROTA E EMPRESAS DA API, E OS LOGS NOVOS DESDE A ULTIMA VARREDURA
    def update(self):
        self.companies = {c['id']: c['label'] for c in api.getData('companies/', limit=500)}
        self.fleet     = {e['vehicle']: e for e in api.getData('etilometers/', limit=500)}

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
    # timestamp SOZINHO JA E UNICO (auto_now_add COM MICROSSEGUNDO), placa+evento SO REFORCAM
    def getRow(self, row):
        v = row.get('vehicle') or ''
        e = row.get('event') or ''
        t = (row.get('timestamp') or '').replace('Z', '')
        return {'k': f'{v}|{e}|{t}', 'v': v, 'e': e, 't': t}

    # SENSOR E CALIBRACAO VEM DO SNAPSHOT: A API NAO EXPOE HISTORICO DE CALIBRACAO
    def getSensors(self):
        if not os.path.exists(SNAPSHOT):
            self.gaps.append(f'snapshot ausente em {SNAPSHOT} — regras de sensor não rodaram')
            return

        db  = sqlite3.connect(SNAPSHOT)
        cal = dict(db.execute('select product_num, max(timestamp) from Etilometros_calibration group by product_num'))

        for plate, sensor in db.execute('''select e.vehicle_plate, d.sensor_id
                                           from Etilometros_etilometro e
                                           left join Etilometros_device d on d.id = e.device_id'''):
            self.sensors[plate] = (sensor, cal.get(sensor))

        idade = (self.now - dt.datetime.fromtimestamp(os.path.getmtime(SNAPSHOT))).days

        if idade > 30:
            self.gaps.append(f'snapshot com {idade} dias — validade de sensor pode estar desatualizada')

        db.close()

    # APLICA AS REGRAS SOBRE A JANELA E MONTA UM BLOCO DE TEXTO POR PROBLEMA
    def check(self):
        ultimo = {}
        evento = {}
        conta  = defaultdict(Counter)

        for row in self.logs:
            plate = row['v']

            if not plate:
                continue

            conta[plate][row['e'][:7]] += 1

            if plate not in ultimo or row['t'] > ultimo[plate]:
                ultimo[plate] = row['t']
                evento[plate] = row['e']

        for plate in self.fleet:
            self.checkSilence(plate, ultimo.get(plate), evento.get(plate), conta[plate])
            self.checkSensor(plate)
            self.checkBehaviour(plate, conta[plate])

        self.report['achados'] = sum(len(v) for v in self.problems.values())
        self.report['linhas']  = len(self.problems)

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
                self.problems[plate].append(
                    f'[SUMIU ANTES DA JANELA] Nenhum log nos últimos {self.MONTHS} meses, mas o veículo já '
                    f'enviou logs no passado. Parou antes de {getDate(self.floor.isoformat(), hour=False)} — '
                    f'a janela de {self.MONTHS} meses não alcança a data em que parou.')
            else:
                self.problems[plate].append(
                    f'[NUNCA ENVIOU LOG] Etilômetro cadastrado em {inst}, sem um único log em toda a base. '
                    f'Ou a instalação nunca foi concluída, ou o cadastro não corresponde a um veículo em operação.')
            return

        days = (self.now - dt.datetime.fromisoformat(last)).days

        if days < self.SILENCE:
            return

        ritmo = len(self.logs) and round(sum(counter.values()) / max((self.MONTHS * 30) - days, 1), 1)

        self.problems[plate].append(
            f'[SILÊNCIO — {getAge(days)}] Sem enviar log desde {getDate(last)}. '
            f'Último evento: {getLabel(event)} ({event}). '
            f'Antes disso enviava ~{getNum(ritmo, 1)} logs/dia ({getNum(sum(counter.values()))} na janela).')

    # VALIDADE DE 1 ANO A PARTIR DA ULTIMA CALIBRACAO, MESMO CRITERIO QUE O PAINEL JA APLICA
    def checkSensor(self, plate):
        sensor, last = self.sensors.get(plate, (None, None))

        if not sensor:
            return

        if not last:
            self.problems[plate].append(
                '[SENSOR SEM CALIBRAÇÃO] O sensor deste veículo não tem nenhuma calibração registrada. '
                'O painel mostra esse caso como "A Vencer" por falta de data, o que esconde o problema.')
            return

        days = (self.now - dt.datetime.fromisoformat(last)).days

        if days <= self.SENSOR_DAYS:
            return

        grave = ' Mais que o dobro da validade. Grave.' if days > self.SENSOR_BAD else ''

        self.problems[plate].append(
            f'[SENSOR VENCIDO — {getAge(days)}] Última calibração do sensor {sensor} em '
            f'{getDate(last, hour=False)}. Vencido há {getAge(days - self.SENSOR_DAYS)} '
            f'(validade de 1 ano).{grave}')

    # ENXURRADA DE FALHA DE SENSOR, ADIAMENTO E SOPRO QUE NUNCA ACONTECE
    def checkBehaviour(self, plate, counter):
        flood = counter['$ETEV24']

        if flood >= self.FLOOD:
            self.problems[plate].append(
                f'[SENSOR DEFEITUOSO] {getNum(flood)} eventos {getLabel("$ETEV24")} ($ETEV24!) na janela — '
                f'{round(100 * flood / max(sum(counter.values()), 1))}% de tudo que este veículo enviou. '
                f'O firmware entra em laço sem saída quando a EEPROM do sensor não responde '
                f'(objects/sensors/alcohol/index.h), emitindo o evento a cada iteração.')

        tries = counter['$ETEV11'] + counter['$ETEV05']

        if tries >= self.MIN_TRIES and counter['$ETEV11'] / tries >= self.NOBLOW:
            self.problems[plate].append(
                f'[SOPRO NUNCA CONCLUÍDO] {getNum(counter["$ETEV11"])} de {getNum(tries)} tentativas terminaram em '
                f'{getLabel("$ETEV11")} ($ETEV11!), {round(100 * counter["$ETEV11"] / tries)}%. '
                f'Testes concluídos na janela: {getNum(counter["$ETEV16"])}. O log não distingue sensor que não lê '
                f'de motorista que não sopra — precisa de verificação em campo.')

        total = counter['$ETEV15'] + counter['$ETEV05']

        if total >= self.MIN_TRIES and counter['$ETEV15'] / total >= self.POSTPONE:
            self.notes[plate].append(
                f'adia {round(100 * counter["$ETEV15"] / total)}% dos testes '
                f'({counter["$ETEV15"]} adiamentos contra {counter["$ETEV16"]} testes realizados)')

    # O SNAPSHOT E A UNICA FONTE QUE ENXERGA LOG ANTERIOR A JANELA.
    # UMA VARREDURA SO: POR PLACA SERIAM 76 JOINS NUMA TABELA DE 230 MIL LINHAS SEM INDICE
    def getEver(self, plate):
        if self.spoke is None:
            self.spoke = set()

            if os.path.exists(SNAPSHOT):
                db = sqlite3.connect(SNAPSHOT)
                self.spoke = {p for (p,) in db.execute(
                    '''select distinct e.vehicle_plate from Etilometros_log l
                       join Etilometros_etilometro e on e.id = l.etilometro_id''')}
                db.close()

        return plate in self.spoke

    # O TEXTO QUE VAI PRA COLUNA desc, LIDO POR UM HUMANO SEM ABRIR O BANCO
    def getDesc(self, plate):
        items = self.problems.get(plate) or []
        label = self.companies.get(self.fleet[plate].get('company'), self.fleet[plate].get('company') or 'empresa não identificada')
        head  = f'{label} · {len(items)} problema' + ('s' if len(items) > 1 else '')
        body  = '\n\n'.join(items)
        notas = self.notes.get(plate) or []
        note  = ('\n\nObs: ' + '; '.join(notas) + '.') if notas else ''
        dupe  = ''

        if sum(1 for e in self.fleet.values() if e['vehicle'] == plate) > 1:
            dupe = '\n\nAtenção: esta placa tem mais de um etilômetro cadastrado — os problemas acima podem vir de aparelhos diferentes.'

        rules = ', '.join(sorted({i[1:i.index(']')].split(' —')[0].lower().replace(' ', '_') for i in items}))
        foot  = (f'\n\n— janela {getDate(self.floor.isoformat(), hour=False)}'
                 f'–{getDate(self.now.isoformat(), hour=False)} · regras: {rules}')

        return f'{head}\n\n{body}{note}{dupe}{foot}'

    # RECONCILIA NOS DOIS SENTIDOS: CRIA, ATUALIZA, E APAGA O QUE FOI RESOLVIDO
    def send(self, dry=True):
        atual = {}

        for row in api.getData('anomalies/', limit=self.PAGE):
            atual.setdefault(row['vehicle'], []).append(row)

        for plate in sorted(self.problems):
            desc = self.getDesc(plate)
            rows = atual.pop(plate, [])

            if not rows:
                self.write(dry, 'POST', 'anomalies/', {'vehicle': plate, 'desc': desc}, plate)
                continue

            # PLACA COM MAIS DE UMA LINHA E RESIDUO: MANTENHO A PRIMEIRA, APAGO O RESTO
            for extra in rows[1:]:
                self.write(dry, 'DELETE', f'anomalies/{extra["id"]}/', None, plate)

            if rows[0]['desc'] != desc:
                self.write(dry, 'PATCH', f'anomalies/{rows[0]["id"]}/', {'desc': desc}, plate)
            else:
                self.report['iguais'] += 1

        # SOBROU NA TABELA E NAO TEM MAIS PROBLEMA (OU SAIU DA FROTA) -> RESOLVIDO, APAGA
        for plate, rows in atual.items():
            for row in rows:
                self.write(dry, 'DELETE', f'anomalies/{row["id"]}/', None, plate)

    # UMA UNICA PORTA DE ESCRITA, PRA O MODO SECO NAO PRECISAR SER LEMBRADO EM CADA CHAMADA
    def write(self, dry, method, endpoint, data, plate):
        self.report[method.lower()] += 1

        if dry:
            return

        api.send(method, endpoint, data)

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
        print(f'achados: {r["achados"]} em {r["linhas"]} veículos')

        regras = Counter(i[1:i.index(']')].split(' —')[0] for v in self.problems.values() for i in v)

        for regra, n in regras.most_common():
            print(f'  {regra:24} {n:4}')

        if self.notes:
            print(f'  {"(nota) adiamento alto":24} {sum(1 for v in self.notes.values() if v):4}')
        print(f'\ntabela anomalies{"  [MODO SECO — nada foi escrito]" if dry else ""}:')
        print(f'  criar     {r["post"]:5}')
        print(f'  atualizar {r["patch"]:5}')
        print(f'  apagar    {r["delete"]:5}')
        print(f'  inalterado{r["iguais"]:5}')

        print('\nnão alcançado:')
        for gap in self.gaps or ['(nada)']:
            print(f'  - {gap}')

    # PIPELINE COMPLETO. dry=True NAO ESCREVE NADA, SO MOSTRA O QUE SAIRIA
    def start(self, dry=True):
        self.get()
        self.update()
        self.getSensors()
        self.check()
        self.gaps.append('logs sem etilômetro vinculado são invisíveis pela API '
                         '(LogViewSet filtra etilometer__is_active=True) — no snapshot são ~7,7% da janela')
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
    parser.add_argument('--show', metavar='PLACA', help='mostra o desc que sairia para uma placa')
    args = parser.parse_args()

    scanner.start(dry=not args.write)

    if args.show:
        print('\n' + '-' * 70)
        print(scanner.getDesc(args.show) if args.show in scanner.problems else f'{args.show}: sem problemas')
