import datetime as dt

from scan import Scanner, getAge, getLabel, getDate


NOW = dt.datetime(2026, 9, 1)


# MONTA UM SCANNER SEM REDE E SEM SNAPSHOT, COM A FROTA E OS LOGS DADOS NA MAO
def build(fleet, logs, sensors=None, ever=()):
    s           = Scanner()
    s.now       = NOW
    s.floor     = NOW - dt.timedelta(days=90)
    s.fleet     = {p: {'vehicle': p, 'company': '1', 'installation_date': '2026-01-10T00:00:00'} for p in fleet}
    s.companies = {'1': 'EMPRESA TESTE'}
    s.sensors   = sensors or {}
    s.logs      = logs
    s.getEver   = lambda plate: plate in ever
    s.check()
    return s


# UM LOG NO FORMATO ENXUTO QUE O CACHE GUARDA
def log(plate, event, days):
    t = (NOW - dt.timedelta(days=days)).isoformat()
    return {'k': f'{plate}|{event}|{t}', 'v': plate, 'e': event, 't': t}


# A CHAVE NATURAL SUBSTITUI O id QUE O LogSerializer NAO EXPOE
def testRowKey():
    from scan import Scanner
    row = Scanner().getRow({'vehicle': 'AAA1B23', 'event': '$ETEV11!', 'timestamp': '2026-08-01T10:00:00.123456Z'})
    assert row['k'] == 'AAA1B23|$ETEV11!|2026-08-01T10:00:00.123456'
    assert Scanner().getRow({})['k'] == '||', 'log sem placa/evento/data não explode'


def testSilence():
    s = build(['A', 'B'], [log('A', '$ETEV05!', 1), log('B', '$ETEV11!', 40)])
    assert 'A' not in s.problems, 'veículo ativo não pode alertar'
    assert '[SILÊNCIO — 40 dias]' in s.problems['B'][0]
    assert 'Sem Sopro ($ETEV11!)' in s.problems['B'][0], 'usa o rótulo do painel'

    # FRONTEIRA EXATA DO LIMIAR: 6 DIAS NAO ALERTA, 7 ALERTA
    assert 'C' not in build(['C'], [log('C', '$ETEV05!', 6)]).problems
    assert 'C' in build(['C'], [log('C', '$ETEV05!', 7)]).problems


def testNeverSpoke():
    s = build(['A', 'B'], [], ever=['B'])
    assert '[NUNCA ENVIOU LOG]' in s.problems['A'][0]
    assert '[SUMIU ANTES DA JANELA]' in s.problems['B'][0], 'já falou um dia, some por ser velho demais'


def testSensor():
    old  = (NOW - dt.timedelta(days=400)).isoformat()
    bad  = (NOW - dt.timedelta(days=800)).isoformat()
    good = (NOW - dt.timedelta(days=100)).isoformat()
    s = build(['A', 'B', 'C', 'D'], [log(p, '$ETEV05!', 1) for p in 'ABCD'],
              sensors={'A': ('ETL1', old), 'B': ('ETL2', bad), 'C': ('ETL3', good), 'D': ('ETL4', None)})
    assert '[SENSOR VENCIDO — 1 ano e 1 meses]' in s.problems['A'][0]
    assert 'Grave.' not in s.problems['A'][0]
    assert 'Grave.' in s.problems['B'][0], 'acima de 2 anos é grave'
    assert 'C' not in s.problems, 'sensor dentro da validade não alerta'
    assert '[SENSOR SEM CALIBRAÇÃO]' in s.problems['D'][0]

    # FRONTEIRA EXATA DA VALIDADE: 365 DIAS NAO VENCE, 366 VENCE
    edge = lambda d: build(['X'], [log('X', '$ETEV05!', 1)],
                           sensors={'X': ('ETL', (NOW - dt.timedelta(days=d)).isoformat())}).problems
    assert 'X' not in edge(365)
    assert 'X' in edge(366)


def testBehaviour():
    flood = [log('A', '$ETEV24!', 1)] * 99 + [log('A', '$ETEV24!', 2)]
    flood = [dict(r, k=str(n)) for n, r in enumerate(flood)]
    s = build(['A'], flood)
    assert '[SENSOR DEFEITUOSO] 100 eventos' in s.problems['A'][0], 'limiar de enxurrada é 100'

    noblow = [dict(log('B', '$ETEV11!', 1), k=str(n)) for n in range(30)]
    s = build(['B'], noblow)
    assert '[SOPRO NUNCA CONCLUÍDO] 30 de 30 tentativas' in ' '.join(s.problems['B'])

    # AMOSTRA PEQUENA NAO VIRA ALERTA, POR MAIS RUIM QUE SEJA A TAXA
    small = [dict(log('C', '$ETEV11!', 1), k=str(n)) for n in range(29)]
    assert 'C' not in build(['C'], small).problems

    postpone = [dict(log('D', '$ETEV15!', 1), k=f'p{n}') for n in range(20)] + \
               [dict(log('D', '$ETEV05!', 1), k=f'o{n}') for n in range(20)]
    s = build(['D'], postpone)
    assert 'adia 50% dos testes' in s.notes['D'][0], 'adiamento é nota, não problema separado'
    assert 'D' not in s.problems


def testDesc():
    old = (NOW - dt.timedelta(days=800)).isoformat()
    s   = build(['A'], [log('A', '$ETEV11!', 40)], sensors={'A': ('ETL9', old)})
    d   = s.getDesc('A')
    assert d.startswith('EMPRESA TESTE · 2 problemas'), 'cabeçalho traz a empresa e a contagem'
    assert '[SILÊNCIO' in d and '[SENSOR VENCIDO' in d, 'um veículo, uma linha, todos os problemas'
    assert d.rstrip().endswith('regras: sensor_vencido, silêncio'), 'rodapé técnico fecha o desc'
    assert 'janela 03/06/2026–01/09/2026' in d

    # UM PROBLEMA SO FICA NO SINGULAR
    assert build(['B'], [log('B', '$ETEV11!', 40)]).getDesc('B').startswith('EMPRESA TESTE · 1 problema\n')


def testIdempotent():
    s = build(['A'], [log('A', '$ETEV11!', 40)])
    assert s.getDesc('A') == s.getDesc('A'), 'mesmo estado, mesmo texto — senão todo run vira PATCH'
    assert len(s.getDesc('A')) < 20000, 'desc cabe num TextField sem sustos'


def testDuplicatePlate():
    s = build(['A'], [log('A', '$ETEV11!', 40)])
    s.fleet['A2'] = dict(s.fleet['A'], vehicle='A')
    assert 'mais de um etilômetro cadastrado' in s.getDesc('A'), 'placa duplicada é dita, não escondida'


def testReconcile():
    s = build(['A', 'B'], [log('A', '$ETEV11!', 40), log('B', '$ETEV05!', 1)])
    feito = []
    s.write = lambda dry, m, e, d, p: feito.append((m, p))

    # A TEM PROBLEMA E NAO ESTA NA TABELA -> POST
    # B ESTA LIMPO MAS TEM LINHA ANTIGA   -> DELETE (foi resolvido)
    # C SAIU DA FROTA E TEM LINHA         -> DELETE (alerta órfão)
    import api as mod
    mod.api.getData = lambda *a, **k: [{'id': 10, 'vehicle': 'B', 'desc': 'velho'},
                                       {'id': 11, 'vehicle': 'C', 'desc': 'órfão'}]
    s.send(dry=True)
    assert ('POST', 'A') in feito
    assert ('DELETE', 'B') in feito, 'problema resolvido some da tabela'
    assert ('DELETE', 'C') in feito, 'veículo que saiu da frota não deixa alerta órfão'

    # MESMO TEXTO NA TABELA -> NAO TOCA
    feito.clear()
    s.report.clear()
    mod.api.getData = lambda *a, **k: [{'id': 10, 'vehicle': 'A', 'desc': s.getDesc('A')}]
    s.send(dry=True)
    assert not feito and s.report['iguais'] == 1, 'rodar duas vezes seguidas não mexe em nada'


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
