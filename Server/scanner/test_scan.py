import datetime as dt
from collections import Counter

from scan import (Scanner, getAge, getLabel, getDate, getVersion,
                  SEM_COMUNICACAO, INSTALACAO_PENDENTE, CALIBRACAO, DEFEITO_APARELHO,
                  TESTE_INCONCLUSIVO, ALCOOL, CONDUTA_MOTORISTA, CADASTRO_INCONSISTENTE,
                  BURLA_BLOQUEIO, FALHA_INTEGRACAO, DADO_CORROMPIDO, FIRMWARE_DESATUALIZADO)


NOW = dt.datetime(2026, 9, 1)


# MONTA UM SCANNER SEM REDE E SEM SNAPSHOT, COM A FROTA E OS LOGS DADOS NA MAO
def build(fleet, logs, sensors=None, ever=(), copies=None):
    s             = Scanner()
    s.now         = NOW
    s.floor       = NOW - dt.timedelta(days=90)
    s.fleet       = {p: {'vehicle': p, 'company': '1', 'telemetry': 'T', 'telemetry_label': 'SUNTECH',
                         'installation_date': '2026-01-10T00:00:00'} for p in fleet}
    s.copies      = Counter(copies or {})
    s.companies   = {'1': 'EMPRESA TESTE', '2': 'EXPRESSO PREDILETO', 'T': 'SUNTECH', 'M': 'MIX TELEMATICS (NOVO)'}
    s.telemetries = {'T', 'M'}
    s.sensors     = sensors or {}
    s.logs        = logs
    s.getEver     = lambda plate: plate in ever
    s.check()
    return s


# UM LOG NO FORMATO ENXUTO QUE O CACHE GUARDA. seconds DESEMPATA A ORDEM DENTRO DO MESMO DIA
def log(plate, event, days, seconds=0, created=None):
    t = (NOW - dt.timedelta(days=days) + dt.timedelta(seconds=seconds)).isoformat()
    return {'k': f'{plate}|{event}|{t}', 'v': plate, 'e': event, 't': t, 'c': t if created is None else created}


# A SEQUENCIA DE UMA SESSAO, UM EVENTO POR SEGUNDO, A PARTIR DE UM OFFSET
def session(plate, events, days, start=0):
    return [log(plate, e, days, start + n) for n, e in enumerate(events)]


def texts(s, plate):
    return ' '.join(t for cat in s.problems.get(plate, {}).values() for t in cat)


# A CHAVE NATURAL SUBSTITUI O id QUE O LogSerializer NAO EXPOE
def testRowKey():
    row = Scanner().getRow({'vehicle': 'AAA1B23', 'event': '$ETEV11!', 'timestamp': '2026-08-01T10:00:00.123456Z'})
    assert row['k'] == 'AAA1B23|$ETEV11!|2026-08-01T10:00:00.123456'
    assert Scanner().getRow({})['k'] == '||', 'log sem placa/evento/data não explode'


def testSilence():
    s = build(['A', 'B'], [log('A', '$ETEV05!', 1), log('B', '$ETEV11!', 40)])
    assert 'A' not in s.problems, 'veículo ativo não pode alertar'
    assert '[SILÊNCIO — 40 dias]' in s.problems['B'][SEM_COMUNICACAO][0]
    assert 'Sem Sopro ($ETEV11!)' in s.problems['B'][SEM_COMUNICACAO][0], 'usa o rótulo do painel'

    # FRONTEIRA EXATA DO LIMIAR: 6 DIAS NAO ALERTA, 7 ALERTA
    assert 'C' not in build(['C'], [log('C', '$ETEV05!', 6)]).problems
    assert 'C' in build(['C'], [log('C', '$ETEV05!', 7)]).problems


def testNeverSpoke():
    s = build(['A', 'B'], [], ever=['B'])
    assert '[NUNCA ENVIOU LOG]' in s.problems['A'][INSTALACAO_PENDENTE][0]
    assert '[SUMIU ANTES DA JANELA]' in s.problems['B'][SEM_COMUNICACAO][0], 'já falou um dia, some por ser velho demais'


def testSensor():
    old  = (NOW - dt.timedelta(days=400)).isoformat()
    bad  = (NOW - dt.timedelta(days=800)).isoformat()
    good = (NOW - dt.timedelta(days=100)).isoformat()
    s = build(['A', 'B', 'C', 'D'], [log(p, '$ETEV05!', 1) for p in 'ABCD'],
              sensors={'A': ('ETL1', old), 'B': ('ETL2', bad), 'C': ('ETL3', good), 'D': ('ETL4', None)})
    assert '[SENSOR VENCIDO — 1 ano e 1 meses]' in s.problems['A'][CALIBRACAO][0]
    assert 'Grave.' not in s.problems['A'][CALIBRACAO][0]
    assert 'Grave.' in s.problems['B'][CALIBRACAO][0], 'acima de 2 anos é grave'
    assert 'C' not in s.problems, 'sensor dentro da validade não alerta'
    assert '[SENSOR SEM CALIBRAÇÃO]' in s.problems['D'][CALIBRACAO][0]

    # FRONTEIRA EXATA DA VALIDADE: 365 DIAS NAO VENCE, 366 VENCE
    edge = lambda d: build(['X'], [log('X', '$ETEV05!', 1)],
                           sensors={'X': ('ETL', (NOW - dt.timedelta(days=d)).isoformat())}).problems
    assert 'X' not in edge(365)
    assert 'X' in edge(366)


def testBehaviour():
    flood = [log('A', '$ETEV24!', 1)] * 99 + [log('A', '$ETEV24!', 2)]
    flood = [dict(r, k=str(n)) for n, r in enumerate(flood)]
    s = build(['A'], flood)
    assert '[SENSOR DEFEITUOSO] 100 eventos' in s.problems['A'][DEFEITO_APARELHO][0], 'limiar de enxurrada é 100'

    noblow = [dict(log('B', '$ETEV11!', 1), k=str(n)) for n in range(30)]
    s = build(['B'], noblow)
    assert '[SOPRO NUNCA CONCLUÍDO] 30 de 30 tentativas' in s.problems['B'][TESTE_INCONCLUSIVO][0]

    # AMOSTRA PEQUENA NAO VIRA ALERTA, POR MAIS RUIM QUE SEJA A TAXA
    small = [dict(log('C', '$ETEV11!', 1), k=str(n)) for n in range(29)]
    assert 'C' not in build(['C'], small).problems

    postpone = [dict(log('D', '$ETEV15!', 1), k=f'p{n}') for n in range(20)] + \
               [dict(log('D', '$ETEV05!', 1), k=f'o{n}') for n in range(20)]
    s = build(['D'], postpone)
    assert '[ADIAMENTO EXCESSIVO] Adia 50% dos testes' in s.problems['D'][CONDUTA_MOTORISTA][0]


def testAlcohol():
    s = build(['A', 'B'], [log('A', '$ETEV301198!', 5), log('A', '$ETEV30!', 2), log('B', '$ETEV29!', 1)])
    d = s.problems['A'][ALCOOL][0]
    assert d.startswith('[ÁLCOOL DETECTADO] 2 leituras'), 'uma leitura já basta, payload não atrapalha'
    assert 'a última em 30/08/2026' in d
    assert 'B' not in s.problems, 'leitura sem álcool não é problema'

    # 0,000 mg/L NAO E ALCOOL: SAI DA CONTAGEM E VIRA DADO CORROMPIDO
    s = build(['C', 'D'], [log('C', '$ETEV300000!', 3), log('C', '$ETEV300000!', 2),
                           log('D', '$ETEV300000!', 3), log('D', '$ETEV300021!', 1)])
    assert ALCOOL not in s.problems['C'], 'só leituras zeradas não é álcool'
    assert s.problems['C'][DADO_CORROMPIDO][0].startswith('[ÁLCOOL COM VALOR ZERO] 2 leituras')
    assert s.problems['D'][ALCOOL][0].startswith('[ÁLCOOL DETECTADO] 1 leitura '), 'a zerada não infla a contagem'
    assert DADO_CORROMPIDO in s.problems['D']


def testRegistry():
    s = build(['A'], [log('A', '$ETEV05!', 1)], copies={'A': 2})
    assert '[PLACA DUPLICADA] Esta placa tem 2 etilômetros' in s.problems['A'][CADASTRO_INCONSISTENTE][0]

    s = build(['B'], [log('B', '$ETEV05!', 1)])
    s.fleet['B']['telemetry'] = '1'
    s.problems.clear()
    s.check()
    assert '[TELEMETRIA INVÁLIDA]' in s.problems['B'][CADASTRO_INCONSISTENTE][0], 'transportadora no lugar da telemetria'

    s.fleet['B']['telemetry'] = None
    s.problems.clear()
    s.check()
    assert '[SEM TELEMETRIA]' in s.problems['B'][CADASTRO_INCONSISTENTE][0]


# MIX FORA DA SIGHIR/PREDILETO NAO REPASSA EVENTO: AUSENCIA DE LOG NAO ALERTA, PRESENCA AINDA VALE
def testMix():
    old = (NOW - dt.timedelta(days=400)).isoformat()
    s   = build(['A', 'B'], [], sensors={'A': ('ETL1', old), 'B': ('ETL2', old)})
    s.fleet['A'].update(telemetry='M', telemetry_label='MIX TELEMATICS (NOVO)')
    s.fleet['B'].update(telemetry='M', telemetry_label='MIX TELEMATICS (NOVO)', company='2')
    s.problems.clear()
    s.report.clear()
    s.check()
    assert s.isMute('A') and not s.isMute('B')
    assert s.report['mudos'] == 1
    assert INSTALACAO_PENDENTE not in s.problems['A'], 'mudo por desenho não é instalação pendente'
    assert CALIBRACAO in s.problems['A'], 'sensor continua sendo avaliado'
    assert INSTALACAO_PENDENTE in s.problems['B'], 'MiX na Predileto repassa, então a regra vale'

    flood = [dict(log('A', '$ETEV24!', 1), k=str(n)) for n in range(100)]
    s.logs = flood
    s.problems.clear()
    s.check()
    assert DEFEITO_APARELHO in s.problems['A'], 'evento que chegou é evidência, mesmo na MiX muda'
    assert SEM_COMUNICACAO not in s.problems['A']


def testDesc():
    old = (NOW - dt.timedelta(days=800)).isoformat()
    s   = build(['A'], [log('A', '$ETEV11!', 40)], sensors={'A': ('ETL9', old)})
    assert set(s.problems['A']) == {SEM_COMUNICACAO, CALIBRACAO}, 'uma linha por categoria'
    assert s.getDesc('A', SEM_COMUNICACAO).startswith('[SILÊNCIO')
    assert s.getDesc('A', CALIBRACAO).startswith('[SENSOR VENCIDO')

    # DOIS PROBLEMAS NA MESMA CATEGORIA VAO NO MESMO desc
    s = build(['B'], [log('B', '$ETEV05!', 1)], copies={'B': 2})
    s.fleet['B']['telemetry'] = None
    s.problems.clear()
    s.check()
    d = s.getDesc('B', CADASTRO_INCONSISTENTE)
    assert '[PLACA DUPLICADA]' in d and '[SEM TELEMETRIA]' in d and '\n\n' in d


def testIdempotent():
    s = build(['A'], [log('A', '$ETEV11!', 40)])
    assert s.getDesc('A', SEM_COMUNICACAO) == s.getDesc('A', SEM_COMUNICACAO), 'mesmo estado, mesmo texto — senão todo run vira PATCH'
    assert len(s.getDesc('A', SEM_COMUNICACAO)) < 20000, 'desc cabe num TextField sem sustos'


def testReconcile():
    s = build(['A', 'B'], [log('A', '$ETEV11!', 40), log('B', '$ETEV05!', 1)])
    feito = []
    s.write = lambda dry, m, e, d, p, count=True: feito.append((m, p, d))

    # A TEM PROBLEMA E NAO ESTA NA TABELA   -> POST com categoria
    # B ESTA LIMPO MAS TEM LINHA ABERTA     -> solved (foi resolvido)
    # C SAIU DA FROTA E TEM LINHA ABERTA    -> solved (não há mais como verificar)
    # D JA ESTA solved                      -> não toca, é histórico
    import api as mod
    mod.api.getData = lambda *a, **k: [{'id': 10, 'vehicle': 'B', 'category': SEM_COMUNICACAO, 'desc': 'velho', 'solved': False, 'deleted': False},
                                       {'id': 11, 'vehicle': 'C', 'category': CALIBRACAO, 'desc': 'órfão', 'solved': False, 'deleted': False},
                                       {'id': 12, 'vehicle': 'A', 'category': SEM_COMUNICACAO, 'desc': 'antigo', 'solved': True, 'deleted': False}]
    s.send(dry=True)
    assert ('POST', 'A', {'vehicle': 'A', 'category': SEM_COMUNICACAO, 'desc': s.getDesc('A', SEM_COMUNICACAO)}) in feito
    assert ('PATCH', 'B', {'solved': True}) in feito, 'problema resolvido é marcado, não apagado'
    assert ('PATCH', 'C', {'solved': True}) in feito, 'veículo que saiu da frota não deixa alerta aberto'
    assert not any(p == 'A' and m == 'PATCH' for m, p, _ in feito), 'linha já resolvida é histórico, nasce outra'
    assert s.report['solved'] == 2

    # MESMO TEXTO NA TABELA -> NAO TOCA
    feito.clear()
    s.report.clear()
    mod.api.getData = lambda *a, **k: [{'id': 10, 'vehicle': 'A', 'category': SEM_COMUNICACAO,
                                        'desc': s.getDesc('A', SEM_COMUNICACAO), 'solved': False, 'deleted': False}]
    s.send(dry=True)
    assert not feito and s.report['iguais'] == 1, 'rodar duas vezes seguidas não mexe em nada'

    # MESMA PLACA, CATEGORIA DIFERENTE ABERTA -> A ANTIGA RESOLVE, A NOVA NASCE
    feito.clear()
    mod.api.getData = lambda *a, **k: [{'id': 10, 'vehicle': 'A', 'category': CALIBRACAO, 'desc': 'x', 'solved': False, 'deleted': False}]
    s.send(dry=True)
    assert ('PATCH', 'A', {'solved': True}) in feito and any(m == 'POST' for m, _, _ in feito)


# Anomaly.vehicle APONTA PRA Vehicle.plate: CAIXA DIFERENTE TRADUZ; PLACA QUE O SNAPSHOT NAO
# CONHECE VAI COMO ESTA E O SERVIDOR DECIDE (PEDIDO DO USUARIO EM 21/09/2026)
def testVehicleLookup():
    s = build(['Mosaic', 'RJN8B5'], [], ever=['Mosaic', 'RJN8B5'])
    assert s.getVehicle('Mosaic') == 'Mosaic', 'sem snapshot, a placa passa como está'

    s.vehicles = {'MOSAIC': 'MOSAIC'}
    feito = []
    s.write = lambda dry, m, e, d, p, count=True: feito.append((m, d['vehicle'] if d else None))
    import api as mod
    mod.api.getData = lambda *a, **k: []
    s.send(dry=True)
    assert ('POST', 'MOSAIC') in feito, 'grava com a placa que o Vehicle conhece'
    assert ('POST', 'RJN8B5') in feito, 'placa fora do snapshot é enviada como está, não pulada'

    # 400 DA API E LACUNA DE UMA PLACA, NAO QUEDA DA VARREDURA
    s = build(['A'], [log('A', '$ETEV11!', 40)])
    mod.api.send = lambda m, e, d=None: (_ for _ in ()).throw(RuntimeError('POST anomalies/ -> 400: {"vehicle":["não existe"]}'))
    s.write(False, 'POST', 'anomalies/', {'vehicle': 'A'}, 'A')
    assert s.report['falhas'] == 1 and any(g.startswith('A: POST recusado') for g in s.gaps)
    assert not any(c[1] == 'A' for c in s.changes), 'recusado não aparece como criado'


# $ETEV35 E O VEICULO EM CONDUCAO COM TESTE REPROVADO; $ETEV32 E PARTIDA SEM TESTE (MANOBRISTA)
def testBypass():
    # ADIA -> DIRIGE -> SEM SOPRO -> NAO AUTORIZADO -> BLOQUEIA (SEQUENCIA REAL DO RJK1D03)
    adiou = ['$ETEV01!', '$ETEV15!', '$ETEV11!', '$ETEV35!', '$ETEV02!']
    logs  = session('A', adiou, 10) + session('A', adiou, 8) + \
            session('A', ['$ETEV12!', '$ETEV05!', '$ETEV300210!', '$ETEV25!', '$ETEV35!', '$ETEV02!'], 5)
    s = build(['A', 'B'], logs + session('B', adiou, 3) + session('B', adiou, 2))
    d = s.problems['A'][BURLA_BLOQUEIO][0]
    assert d.startswith('[CONDUÇÃO NÃO AUTORIZADA] 3 vezes'), 'limiar é 3'
    assert 'Álcool Detectado (1) ou Sem Sopro (2)' in d, 'separa a causa pelo evento anterior'
    assert '2 vieram depois de um Teste Adiado' in d
    assert 'Última em 27/08/2026' in d
    assert 'B' not in s.problems, '2 ocorrências não alertam'

    # MANOBRISTA: 5 PARTIDAS SEM TESTE ALERTA, 4 NAO
    valet = [log('C', '$ETEV22!', 9)] + [log('C', '$ETEV32!', 9, n + 1) for n in range(5)] + \
            [log('C', '$ETEV16!', 8, n) for n in range(5)]
    s = build(['C', 'D'], valet + [log('D', '$ETEV32!', 2, n) for n in range(4)])
    d = s.problems['C'][BURLA_BLOQUEIO][0]
    assert d.startswith('[MODO MANOBRISTA] 5 partidas sem teste'), d
    assert 'contra 5 testes' in d and '50% das liberações' in d and '$ETEV22!: 1 vezes' in d
    assert BURLA_BLOQUEIO not in s.problems['D'], '4 partidas não alertam'


# TESTE CONCLUIDO SEM RESULTADO: A TELEMETRIA ESTA FILTRANDO O PROTOCOLO
def testIntegration():
    ok    = ['$ETEV05!', '$ETEV29!', '$ETEV16!', '$ETEV01!']
    mudo  = ['$ETEV05!', '$ETEV16!']
    logs  = [r for n in range(10) for r in session('A', ok, 10 - n)] + \
            [r for n in range(10) for r in session('B', mudo, 10 - n)] + \
            [r for n in range(9)  for r in session('C', mudo, 10 - n)] + \
            [r for n in range(10) for r in session('D', mudo + ['$ETEV01!'], 10 - n)]
    s = build(['A', 'B', 'C', 'D'], logs)
    s.fleet['B'].update(telemetry='M', telemetry_label='MIX TELEMATICS (NOVO)')
    s.problems.clear()
    s.check()
    assert 'A' not in s.problems, 'resultado chegando não é problema'
    d = s.problems['B'][FALHA_INTEGRACAO][0]
    assert d.startswith('[RESULTADO NÃO CHEGA] 10 testes concluídos'), d
    assert 'Também não chegam' in d, 'sem $ETEV01/$ETEV02 o bloqueio também fica cego'
    assert 'confira a telemetria' not in d, 'na MiX o padrão é esperado'
    assert 'C' not in s.problems, '9 testes é amostra pequena'
    d = s.problems['D'][FALHA_INTEGRACAO][0]
    assert 'Também não chegam' not in d and 'O cadastro diz SUNTECH' in d, 'Suntech repassa tudo: padrão MiX em Suntech é cadastro suspeito'


# EVENTO FORA DO PROTOCOLO E RELOGIO DO APARELHO PERDIDO
def testData():
    ruim = [log('A', 'CK!', 5), log('A', '$ETEV30 0343!', 4), log('A', '(rec) $ETKA!', 3), log('A', '!ETEV23$', 2),
            log('A', '$ETEV09ETL2608402025435219!', 1)]
    s = build(['A'], ruim)
    d = s.problems['A'][DADO_CORROMPIDO][0]
    assert d.startswith('[EVENTO MALFORMADO] 3 logs'), d
    assert "'CK!'" in d and '!ETEV23$' not in d, 'manobrista desativado tem delimitador invertido por desenho'

    relogio = [log('B', '$ETEV05!', 5, n, created='2003-12-31T21:00:00') for n in range(2)] + \
              [log('B', '$ETEV05!', 4, created='')] + [log('C', '$ETEV05!', 4, created='')]
    s = build(['B', 'C'], relogio)
    d = s.problems['B'][DADO_CORROMPIDO][0]
    assert d.startswith('[RELÓGIO DO APARELHO] 3 logs') and '2003-12-31' in d, d
    assert 'C' not in s.problems, 'abaixo do limiar'

    # LOG DO CACHE ANTIGO NAO TEM 'c': NAO E JULGADO
    velho = [dict(log('D', '$ETEV05!', 4, n), k=str(n)) for n in range(5)]
    for r in velho: r.pop('c')
    assert 'D' not in build(['D'], velho).problems


# VERSAO ATRAS DA LINHA ATUAL DO CATALOGO; 1.0.0 E "NUNCA REPORTOU", NAO VERSAO
def testFirmware():
    assert getVersion('v6.4.7') == (6, 4, 7) and getVersion('6.3.11') == (6, 3, 11)
    assert getVersion('1.0.0') is None and getVersion('') is None and getVersion('abc') is None

    s = build(['A', 'B', 'C', 'D', 'E'], [log(p, '$ETEV05!', 1) for p in 'ABCDE'] + [log('B', '$ETEV10!', 3)])
    s.firmwares = sorted([((6, 4, 7), 'v6.4.7', '2026-09-01'), ((6, 4, 2), 'v6.4.2', '2026-07-07'),
                          ((6, 3, 9), 'v6.3.9', '2026-05-12'), ((5, 3, 0), 'v5.3.0', '2025-05-08')], reverse=True)
    s.fleet['A']['software_version'] = '6.4.4'
    s.fleet['B']['software_version'] = '6.3.9'
    s.fleet['C']['software_version'] = 'v5.1.6'
    s.fleet['D']['software_version'] = '1.0.0'
    s.fleet['E']['software_version'] = '6.4.8'
    s.problems.clear()
    s.report.clear()
    s.check()
    assert 'A' not in s.problems, 'mesma linha 6.4, patch atrás não alerta por padrão'
    d = s.problems['B'][FIRMWARE_DESATUALIZADO][0]
    assert d.startswith('[FIRMWARE ANTIGO] O aparelho reporta a versão 6.3.9; a atual é v6.4.7 (01/09/2026)'), d
    assert 'Está 1 linha atrás (6.3 → 6.4)' in d and 'Firmware Atualizado ($ETEV10!) 1 vez ' in d
    assert 'Está 3 linhas atrás (5.1 → 6.4)' in s.problems['C'][FIRMWARE_DESATUALIZADO][0], '5.3, 6.3 e 6.4 no catálogo'
    assert 'D' not in s.problems and s.report['sem_versao'] == 1, '1.0.0 vira lacuna, não alerta'
    assert 'E' not in s.problems, 'mais novo que o catálogo não é antigo'

    # MINIMO EXPLICITO: TUDO ABAIXO DELE ALERTA, INCLUSIVE PATCH
    s.FIRMWARE_MIN = '6.4.7'
    s.problems.clear()
    s.check()
    assert 'Mínimo aceito: 6.4.7' in s.problems['A'][FIRMWARE_DESATUALIZADO][0]
    s.FIRMWARE_MIN = None


# RESOLVIDO NO PAINEL COM A MESMA EVIDENCIA FICA RESOLVIDO; EVIDENCIA NOVA VIRA LINHA NOVA
def testHumanSolved():
    s = build(['A', 'B'], [log('A', '$ETEV301198!', 5), log('B', '$ETEV301198!', 5)])
    feito = []
    s.write = lambda dry, m, e, d, p, count=True: feito.append((m, p))
    import api as mod
    mod.api.getData = lambda *a, **k: [
        {'id': 1, 'vehicle': 'A', 'category': ALCOOL, 'desc': s.getDesc('A', ALCOOL), 'solved': True, 'deleted': False},
        {'id': 2, 'vehicle': 'B', 'category': ALCOOL, 'desc': 'texto antigo, evidência mudou', 'solved': True, 'deleted': False}]
    s.send(dry=True)
    assert ('POST', 'A') not in feito and s.report['mantidos'] == 1, 'mesmo texto: a decisão humana vale'
    assert ('POST', 'B') in feito, 'texto diferente: nasce linha nova'


# PLACA RECUSADA POR CAIXA E TENTADA EM MAIUSCULAS UMA VEZ; OUTRA RECUSA VIRA LACUNA
def testPlateCase():
    import api as mod
    s = build(['Mosaic'], [log('Mosaic', '$ETEV11!', 40)])
    sent = []

    def fake(m, e, d=None):
        sent.append(d['vehicle'])
        if d['vehicle'] != 'MOSAIC':
            raise RuntimeError('POST anomalies/ -> 400: {"vehicle":["Object with plate=Mosaic does not exist."]}')

    mod.api.send = fake
    s.write(False, 'POST', 'anomalies/', {'vehicle': 'Mosaic', 'category': SEM_COMUNICACAO, 'desc': 'x'}, 'Mosaic')
    assert sent == ['Mosaic', 'MOSAIC'] and s.report['falhas'] == 0 and s.report['post'] == 1

    sent.clear()
    s.write(False, 'POST', 'anomalies/', {'vehicle': 'RJN8B5', 'category': SEM_COMUNICACAO, 'desc': 'x'}, 'RJN8B5')
    assert sent == ['RJN8B5', 'RJN8B5'.upper()] or sent == ['RJN8B5'], 'placa já maiúscula não repete'
    assert s.report['falhas'] == 1


# SEM SNAPSHOT, "JA FALOU UM DIA" VEM DE UMA CONSULTA DE 1 LOG NA API, UMA VEZ POR PLACA
def testEverFromApi():
    import scan as mod
    s = Scanner()
    s.spoke = None
    real = mod.SNAPSHOT
    mod.SNAPSHOT = 'nao-existe.sqlite3'
    calls = []
    import api as amod
    amod.api.get = lambda ep, **k: (calls.append(k['vehicle']), {'count': 3 if k['vehicle'] == 'A' else 0})[1]
    try:
        assert s.getEver('A') and not s.getEver('B') and s.getEver('A')
        assert calls == ['A', 'B'], 'uma consulta por placa, com cache'
    finally:
        mod.SNAPSHOT = real


def testHelpers():
    assert getAge(39) == '39 dias'
    assert getAge(400) == '1 ano e 1 meses'
    assert getAge(800) == '2 anos e 2 meses'
    assert getAge(90) == '3 meses'
    assert getLabel('$ETEV301198!') == 'Álcool Detectado', 'payload no evento não quebra o rótulo'
    assert getLabel('$XPTO!') == '$XPTO!', 'evento desconhecido passa cru, não vira None'
    assert getDate(None) == '?'
    assert getDate('2026-07-22T15:56:12Z') == '22/07/2026 15:56'


def testWriteGuard():
    import api as mod
    try:
        mod.Api().send('DELETE', 'logs/1/')
        assert False, 'escrita fora de anomalies/ tinha que ser bloqueada'
    except PermissionError:
        pass


if __name__ == '__main__':
    for name, fn in sorted(list(globals().items())):
        if name.startswith('test'):
            fn()
            print(f'ok  {name}')

    print('\ntodos passaram')
