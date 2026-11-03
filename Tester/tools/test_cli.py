#!/usr/bin/env python3
"""Testes da CLI (tools/sighir.py) sem aparelho e sem rede: a API é trocada por uma falsa em memória.
Cobre o cadastro/instalação no modelo do servidor de 24/09/2026 (instalação = PATCH /devices com a placa;
módulo e chip em /telemetries) e de 07/10/2026 (telemetria = marca do módulo; MiX usa o módulo MIX-<esp>).
Rodar: python tools/test_cli.py"""

import os
import sys
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from tools import sighir, report, session  # noqa: E402
import json, tempfile  # noqa: E402
from datetime import datetime, timedelta  # noqa: E402

session.SESSIONS = tempfile.mkdtemp()    # O register/flash ANOTAM A SESSÃO: FORA DA PASTA REAL
report.OUTPUT    = tempfile.mkdtemp()

MIX2, MIX, SUNTECH, ENTRACK = '17131425000130', '17131425000132', '44922499000', '12729135000171'
COMPANIES = [{'id': MIX2, 'type': 'telemetry', 'value': '5', 'label': 'MIX TELEMATICS (NOVO)'},
             {'id': MIX, 'type': 'telemetry', 'value': '0', 'label': 'MIX TELEMATICS'},
             {'id': SUNTECH, 'type': 'telemetry', 'value': '2', 'label': 'SUNTECH'},
             {'id': ENTRACK, 'type': 'telemetry', 'value': '6', 'label': 'ENTRACK'},
             {'id': '29863420000930', 'type': 'transportation', 'value': 'predileto', 'label': 'EXPRESSO PREDILETO'},
             {'id': '40000000000100', 'type': 'transportation', 'value': 'logika', 'label': 'LOGIKA TRANSPORTES',
              'data': {'settings': {'comm_type': 2, 'operation_mode': 0, 'maneuver_time': 5, 'postpone_time': 5,
                                    'max_postpone': 2, 'telemetry': 2, 'enable_random': 1}}}]
CONFIG = {'company': 'logika', 'telemetry': 2, 'vehicle_type': 0, 'maneuver_time': 5, 'postpone_time': 5,
          'max_postpone': 2, 'enable_random': 1, 'camera': 5, 'blowProb': 0.5, 'passwd': '12345678'}
PREDILETO, LOGIKA = '29863420000930', '40000000000100'


class FakeServer:
    def __init__(self):
        self.devices = {'MICLIVRE': {'id': 'MICLIVRE', 'plate': None, 'telemetry': None, 'installation_data': {}},
                        'MICINST': {'id': 'MICINST', 'plate': 'RJT5E02', 'telemetry': '1700006560',
                                    'installation_data': {'observation': 'x'},
                                    'company': PREDILETO, 'series_num': '00032', 'sensor_id': 'ETL111',
                                    'installer': 'Paulo', 'installation_date': '2026-02-06T00:00:00Z',
                                    'nickname': '', 'need_update': False}}
        self.modules = {'1700006560': {'id': '1700006560', 'chip': '', 'vehicle': 'RJT5E02', 'brand': SUNTECH}}
        self.labels = {c['id']: c['label'] for c in COMPANIES}
        self.calls = []

    def etilometers(self):
        return [{'esp_id': d['id'], 'vehicle': d['plate'], 'telemetry_label': 'X', 'installation_date': '2026-01-01'}
                for d in self.devices.values() if d.get('plate')]

    def get(self, endpoint, **_):
        self.calls.append(('GET', endpoint))
        parts = [p for p in endpoint.split('?')[0].split('/') if p]
        if parts[0] == 'companies':
            return {'status': 'success', 'data': COMPANIES}
        if parts[0] == 'etilometers':
            return {'status': 'success', 'data': self.etilometers()}
        table = {'devices': self.devices, 'telemetries': self.modules}[parts[0]]
        if len(parts) > 1:
            row = table.get(parts[1])
            return {'status': 'success', 'data': self.view(parts[0], row)} if row else {'status': 'error', 'data': '404'}
        return {'status': 'success', 'data': [self.view(parts[0], r) for r in table.values()]}

    def view(self, kind, row):
        """como a API devolve: o device mostra a marca do módulo (telemetry_brand, só leitura)."""
        row = dict(row)
        if kind == 'devices':
            brand = (self.modules.get(row.get('telemetry')) or {}).get('brand')
            row.update(telemetry_brand=brand, telemetry_brand_label=self.labels.get(brand))
        return row

    def post(self, endpoint, data, type='POST', **_):
        self.calls.append((type, endpoint, dict(data)))
        parts = [p for p in endpoint.split('/') if p]
        table = {'devices': self.devices, 'telemetries': self.modules}[parts[0]]
        if type == 'POST':
            table[data['id']] = dict(data)
        else:
            row = table[parts[1]]
            row.update(data)
            if parts[0] == 'devices' and data.get('telemetry'):
                self.modules[data['telemetry']]['vehicle'] = row.get('plate')
        return {'status': 'success', 'data': dict(data)}

    def writes(self):
        return [c for c in self.calls if c[0] != 'GET']


def install(server, *argv):
    sighir.get_req, sighir.post_req = server.get, server.post
    args = sighir.build().parse_args(['install', *argv])
    return args.func(args)


def testPlacaENulos():
    assert sighir.normPlate(' rjt5e02 ') == 'RJT5E02' and sighir.normPlate('abc1234') == 'ABC1234'
    assert sighir.normPlate('Portaria Predileto') == 'Portaria Predileto'
    assert sighir.optional('N/A') is None and sighir.optional(' none ') is None and sighir.optional('17') == '17'


def testAliasesDosArgumentos():
    a = sighir.build().parse_args(['register', '--company', 'x', '--suntech', '1700'])
    assert a.modulo == '1700' and a.chip == 'N/A'
    a = sighir.build().parse_args(['install', 'MIC', '--placa', 'P', '--telemetria', 'mix2', '--duplicar'])
    assert a.forcar and not a.yes


def testPreviaNaoGrava():
    s = FakeServer()
    assert install(s, 'MICLIVRE', '--placa', 'abc1d23', '--telemetria', 'mix2') == 3
    assert not s.writes()


def testPlacaEmOutroAparelhoBloqueia():
    s = FakeServer()
    assert install(s, 'MICLIVRE', '--placa', 'RJT5E02', '--telemetria', 'mix2', '--yes') == 2
    assert not s.writes()


def testAparelhoEmOutraPlacaBloqueia():
    s = FakeServer()
    assert install(s, 'MICINST', '--placa', 'ZZZ9Z99', '--telemetria', 'suntech', '--yes') == 2
    assert not s.writes()


def testInstalaComModuloNovo():
    s = FakeServer()
    rc = install(s, 'MICLIVRE', '--placa', 'abc1d23', '--telemetria', 'suntech', '--modulo', '1700099999',
                 '--chip', '8955', '--instalador', 'Fulano', '--maleta', '--yes')
    assert rc == 0, s.calls
    writes = s.writes()
    assert writes[0] == ('POST', '/telemetries', {'id': '1700099999', 'chip': '8955', 'brand': SUNTECH}), writes
    kind, endpoint, payload = writes[1]
    assert (kind, endpoint) == ('PATCH', '/devices/MICLIVRE'), writes
    assert payload['plate'] == 'ABC1D23' and 'telemetry_company' not in payload    # campo removido em 07/10/2026
    assert payload['telemetry'] == '1700099999' and payload['vehicle_type'] == 0 and payload['is_operating']
    assert payload['installer'] == 'Fulano' and payload['installation_data'] == {'suitcase': 1}
    assert 'installation_date' in payload
    assert not any(k in payload for k in ('chip', 'suntech', 'vehicle_plate'))   # campos do modelo antigo


def testReinstalarMantemDataEDados():
    s = FakeServer()
    assert install(s, 'MICINST', '--placa', 'rjt5e02', '--telemetria', 'suntech', '--tipo', 'carro', '--yes') == 0
    payload = s.writes()[-1][2]
    assert 'installation_date' not in payload and payload['vehicle_type'] == 1
    assert payload['installation_data'] == {'observation': 'x'}


def testModuloComIdDeAparelhoRecusado():
    s = FakeServer()
    rc = install(s, 'MICLIVRE', '--placa', 'abc1d23', '--telemetria', 'suntech', '--modulo', 'MIC2757626176655517',
                 '--yes')
    assert rc == 1 and not s.writes()


def testModuloEmOutraPlacaRecusado():
    s = FakeServer()
    s.devices['MICINST']['plate'] = None             # libera a placa, mas o módulo continua no RJT5E02
    rc = install(s, 'MICLIVRE', '--placa', 'abc1d23', '--telemetria', 'suntech', '--modulo', '1700006560', '--yes')
    assert rc == 2 and not s.writes()                # barrado antes de gravar, com as opções


def testMixNaoAceitaModulo():
    s = FakeServer()
    assert install(s, 'MICLIVRE', '--placa', 'abc1d23', '--telemetria', 'mix2', '--modulo', '1700', '--yes') == 1


def testInstalaMixCriaModuloMix():
    s = FakeServer()
    assert install(s, 'MICLIVRE', '--placa', 'abc1d23', '--telemetria', 'mix2', '--yes') == 0, s.calls
    writes = s.writes()
    assert writes[0] == ('POST', '/telemetries', {'id': 'MIX-MICLIVRE', 'brand': MIX2}), writes
    assert writes[1][1] == '/devices/MICLIVRE' and writes[1][2]['telemetry'] == 'MIX-MICLIVRE'


def testMixAntigoParaMix2TrocaSoAMarca():
    s = FakeServer()
    s.modules['MIX-MICLIVRE'] = {'id': 'MIX-MICLIVRE', 'chip': '', 'vehicle': None, 'brand': MIX}
    s.devices['MICLIVRE']['telemetry'] = 'MIX-MICLIVRE'
    assert install(s, 'MICLIVRE', '--placa', 'abc1d23', '--telemetria', 'mix2', '--yes') == 0, s.calls
    writes = s.writes()
    assert writes[0] == ('PATCH', '/telemetries/MIX-MICLIVRE', {'brand': MIX2}), writes
    assert 'telemetry' not in writes[1][2]                     # já aponta para o módulo certo


def testSuntechSemModuloNumAparelhoMixRecusa():
    s = FakeServer()
    s.modules['MIX-MICLIVRE'] = {'id': 'MIX-MICLIVRE', 'chip': '', 'vehicle': None, 'brand': MIX2}
    s.devices['MICLIVRE']['telemetry'] = 'MIX-MICLIVRE'
    assert install(s, 'MICLIVRE', '--placa', 'abc1d23', '--telemetria', 'suntech', '--yes') == 1
    assert not s.writes()


def testModuloDeOutraMarcaRecusado():
    s = FakeServer()
    s.modules['1700055555'] = {'id': '1700055555', 'chip': '', 'vehicle': None, 'brand': SUNTECH}
    rc = install(s, 'MICLIVRE', '--placa', 'abc1d23', '--telemetria', 'entrack', '--modulo', '1700055555', '--yes')
    assert rc == 1 and not s.writes()


def testSuntechNoModuloAtualGravaAMarca():
    s = FakeServer()
    s.modules['1700006560']['brand'] = ''                      # módulo sem marca: o install completa
    assert install(s, 'MICINST', '--placa', 'rjt5e02', '--telemetria', 'suntech', '--yes') == 0, s.calls
    assert s.writes()[0] == ('PATCH', '/telemetries/1700006560', {'brand': SUNTECH}), s.writes()


def edit(server, *argv):
    sighir.get_req, sighir.post_req = server.get, server.post
    args = sighir.build().parse_args(['edit', *argv])
    return args.func(args)


def testEditPreviaNaoGrava():
    s = FakeServer()
    assert edit(s, 'MICINST', '--company', 'logika', '--desinstalar') == 3
    assert not s.writes()


def testEditVoltouDaPrediletoVaiParaLogika():
    s = FakeServer()
    rc = edit(s, 'MICINST', '--company', 'logika', '--desinstalar', '--modulo', '1700077777', '--chip', '8955',
              '--rearmar', '--yes')
    assert rc == 0, s.calls
    writes = s.writes()
    assert writes[0] == ('POST', '/telemetries', {'id': '1700077777', 'chip': '8955'}), writes
    kind, endpoint, payload = writes[1]
    assert (kind, endpoint) == ('PATCH', '/devices/MICINST')
    assert payload == {'company': LOGIKA, 'telemetry': '1700077777', 'plate': None,
                       'installation_date': None, 'installer': '', 'installation_data': {}, 'need_update': True}, payload
    assert 'series_num' not in payload and 'sensor_id' not in payload    # só o que mudou


def testEditEmpresaComPlacaExigeDesinstalar():
    s = FakeServer()
    assert edit(s, 'MICINST', '--company', 'logika', '--yes') == 2
    assert not s.writes()


def testEditDesvinculaModulo():
    s = FakeServer()
    assert edit(s, 'MICINST', '--modulo', 'none', '--yes') == 0
    assert s.writes() == [('PATCH', '/devices/MICINST', {'telemetry': None})], s.writes()


def testEditSoChipDoModuloAtual():
    s = FakeServer()
    assert edit(s, 'MICINST', '--chip', '8955000', '--yes') == 0
    assert s.writes() == [('PATCH', '/telemetries/1700006560', {'chip': '8955000'})], s.writes()


def testEditNadaAMudar():
    s = FakeServer()
    assert edit(s, 'MICINST', '--company', 'predileto', '--series', '32', '--yes') == 0
    assert not s.writes()


def testEditSerieDuplicada():
    s = FakeServer()
    s.devices['MICLIVRE']['series_num'] = '00099'
    assert edit(s, 'MICINST', '--series', '99', '--yes') == 1 and not s.writes()


def testEditSensorPelaUsbConfereOAparelho():
    s = FakeServer()
    sighir.get_req, sighir.post_req = s.get, s.post
    args = sighir.build().parse_args(['edit', 'MICINST', '--sensor', 'usb', '--yes'])
    disconnect = types.SimpleNamespace(disconnect=lambda: None)
    real = sighir.core
    try:
        sighir.core = types.SimpleNamespace(robustSync=lambda: True, readEspId=lambda: 'MICOUTRO',
                                            readSensorId=lambda: 'ETL222', device=disconnect)
        assert args.func(args) == 1 and not s.writes()                 # aparelho errado na USB
        sighir.core = types.SimpleNamespace(robustSync=lambda: True, readEspId=lambda: 'MICINST',
                                            readSensorId=lambda: 'ETL222', device=disconnect)
        assert args.func(args) == 0
    finally:
        sighir.core = real
    assert s.writes() == [('PATCH', '/devices/MICINST', {'sensor_id': 'ETL222'})], s.writes()


def fakeCore(esp, sensor):
    return types.SimpleNamespace(
        robustSync=lambda: True, readFirmware=lambda: {'status': 'ok', 'version': (6, 4, 8)},
        ensureNativeEspId=lambda: esp, readSensorId=lambda: sensor, readEspId=lambda: esp, readConfig=lambda: dict(CONFIG),
        device=types.SimpleNamespace(disconnect=lambda: None), versionStr=str, MIN_FIRMWARE=(6, 0, 0))


def register(server, esp, sensor, *argv):
    sighir.get_req, sighir.post_req = server.get, server.post
    args = sighir.build().parse_args(['register', '--company', 'logika', '--tecnico', 'Fulano', *argv])
    real, sighir.core = sighir.core, fakeCore(esp, sensor)
    try:
        return args.func(args)
    finally:
        sighir.core = real


def output(fn):
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = fn()
    return rc, buf.getvalue()


def testRegisterAparelhoJaCadastradoMostraOpcoes():
    s = FakeServer()
    rc, out = output(lambda: register(s, 'MICINST', 'ETL111', '--modulo', '1700077777'))
    assert rc == 4 and not s.writes(), s.writes()
    assert 'JÁ ESTÁ CADASTRADO' in out and 'EXPRESSO PREDILETO' in out and 'placa RJT5E02' in out, out
    assert 'opção 1' in out and 'edit MICINST --company logika --desinstalar --modulo 1700077777' in out, out
    assert 'opção 3' in out and 'server-delete' in out


def testRegisterModuloDeOutroAparelho():
    s = FakeServer()
    rc, out = output(lambda: register(s, 'MICNOVO', 'ETL999', '--modulo', '1700006560'))
    assert rc == 4 and not s.writes()
    assert 'O Suntech 1700006560 já pertence ao aparelho MICINST' in out and 'edit MICINST --modulo none' in out, out


def testRegisterSensorDeOutroAparelho():
    s = FakeServer()
    rc, out = output(lambda: register(s, 'MICNOVO', 'ETL111'))
    assert rc == 4 and 'O sensor ETL111 já pertence ao aparelho MICINST' in out, out
    rc, _ = output(lambda: register(s, 'MICNOVO', 'ETL111', '--forcar'))
    assert rc == 0 and s.writes()[-1][1] == '/devices'


def testRegisterModuloLivreReaproveita():
    s = FakeServer()
    s.modules['1700055555'] = {'id': '1700055555', 'chip': '', 'vehicle': None}
    rc, out = output(lambda: register(s, 'MICNOVO', 'ETL999', '--modulo', '1700055555'))
    assert rc == 0 and 'livre' in out, out
    assert s.writes()[-1][2]['telemetry'] == '1700055555'


def testRegisterComSensorManualERandom():
    s = FakeServer()
    rc, _ = output(lambda: register(s, 'MICNOVO', 'ETL_USB', '--sensor', 'ETL888'))
    assert rc == 0 and s.writes()[-1][2]['sensor_id'] == 'ETL888'

    s2 = FakeServer()
    rc2, _ = output(lambda: register(s2, 'MICNOVO2', 'ETL_USB', '--sensor', 'random'))
    assert rc2 == 0
    randId = s2.writes()[-1][2]['sensor_id']
    assert randId.startswith('ETL') and len(randId) == 19 and randId != 'ETL_USB'


def testOndeAchaCadaIdentificador():
    s = FakeServer()
    sighir.get_req = s.get
    for value, expect in (('MICINST', 'aparelho:'), ('ETL111', 'sensor:'), ('1700006560', 'módulo:'),
                          ('rjt5e02', 'placa:'), ('32', 'série:')):
        rc, out = output(lambda: sighir.build().parse_args(['onde', value]).func(sighir.build().parse_args(['onde', value])))
        assert rc == 0 and expect in out and 'MICINST' in out, (value, out)
    rc, out = output(lambda: sighir.build().parse_args(['onde', 'XYZ']).func(sighir.build().parse_args(['onde', 'XYZ'])))
    assert rc == 1 and 'não está cadastrado' in out


def testInstallModuloEmUsoMostraOpcoes():
    s = FakeServer()
    rc, out = output(lambda: install(s, 'MICLIVRE', '--placa', 'abc1d23', '--telemetria', 'suntech',
                                     '--modulo', '1700006560', '--yes'))
    assert rc == 2 and not s.writes() and 'já pertence ao aparelho MICINST' in out and 'opção 1' in out, out


def testProgressoDoFlash():
    import json, time, tempfile, os
    tmp = tempfile.mkdtemp()
    real = sighir.FLASH_STATE
    sighir.FLASH_STATE = os.path.join(tmp, 'flash.json')
    try:
        args = sighir.build().parse_args(['progresso', '--espera', '1'])
        rc, out = output(lambda: args.func(args))
        assert rc == 1 and 'nenhum flash' in out
        now = time.time()
        sighir.flashState('gravando', 42.4, now - 95)
        rc, out = output(lambda: args.func(args))
        assert rc == 0 and 'flash gravando: 42%' in out and '1 min 35 s' in out, out
        json.dump({'estado': 'gravando', 'porcentagem': 50, 'inicio': now - 300, 'atualizado': now - 120},
                  open(sighir.FLASH_STATE, 'w'))
        rc, out = output(lambda: args.func(args))
        assert rc == 2 and 'SEM ATUALIZAÇÃO' in out, out
        sighir.flashState('concluído', 100, now - 240, detalhe='firmware 6.4.8 [ok]')
        rc, out = output(lambda: args.func(args))
        assert rc == 0 and 'flash concluído: 100%' in out and '6.4.8' in out, out
    finally:
        sighir.FLASH_STATE = real


def testProgressoLoopEscreveA20s():
    import tempfile, os, threading, time
    tmp = tempfile.mkdtemp()
    real, realEvery, realCore = sighir.FLASH_STATE, sighir.PROGRESS_EVERY, sighir.core
    sighir.FLASH_STATE, sighir.PROGRESS_EVERY = os.path.join(tmp, 'flash.json'), 0.05
    sighir.core = types.SimpleNamespace(updater=types.SimpleNamespace(percentage=61.7))
    stop = threading.Event()
    try:
        def run():
            t = threading.Thread(target=sighir.progressLoop, args=(stop, time.time()))
            t.start()
            time.sleep(0.2)
            stop.set()
            t.join()
        rc, out = output(run)
        assert 'PROGRESSO DO FLASH: 62% (gravando' in out, out
        import json
        assert json.load(open(sighir.FLASH_STATE))['porcentagem'] == 61.7
    finally:
        sighir.FLASH_STATE, sighir.PROGRESS_EVERY, sighir.core = real, realEvery, realCore


def testRegisterPayloadModeloNovo():
    """o register lê o aparelho pela USB: aqui o core é trocado por um falso."""
    s = FakeServer()
    sighir.get_req, sighir.post_req = s.get, s.post
    fake = types.SimpleNamespace(
        robustSync=lambda: True, readFirmware=lambda: {'status': 'ok', 'version': (6, 4, 8)},
        ensureNativeEspId=lambda: 'MICNOVO', readSensorId=lambda: 'ETL123', readConfig=lambda: {**CONFIG, 'company': 'sighir'},
        device=types.SimpleNamespace(disconnect=lambda: None), versionStr=str, MIN_FIRMWARE=(6, 0, 0))
    args = sighir.build().parse_args(['register', '--company', 'predileto', '--series', '7',
                                      '--modulo', '1700088888', '--chip', 'N/A', '--tecnico', 'Paulo', '--obs', 'lote 12'])
    real, sighir.core = sighir.core, fake
    try:
        assert args.func(args) == 0, s.calls
    finally:
        sighir.core = real
    writes = s.writes()
    assert writes[0] == ('POST', '/telemetries', {'id': '1700088888'}), writes
    kind, endpoint, payload = writes[1]
    assert (kind, endpoint) == ('POST', '/devices')
    settings = json.loads(payload.pop('default_settings'))                    # TEXTO JSON: O CAMPO É TextField NO SERVIDOR
    assert payload == {'company': '29863420000930', 'series_num': '00007', 'id': 'MICNOVO', 'sensor_id': 'ETL123',
                       'need_update': True, 'telemetry': '1700088888'}, payload
    assert settings['settings'] == {**CONFIG, 'company': 'sighir'} and settings['settings']['passwd'] == '12345678'
    assert settings['report']['versao'] == 1 and settings['report']['tecnico'] == 'Paulo' and settings['report']['observacoes'] == 'lote 12'
    assert len(settings['report']['ensaios']) == 15 and settings['report']['aparelho']['esp_id'] == 'MICNOVO'


def testRegisterSemTecnicoNaoGrava():
    s = FakeServer()
    sighir.get_req, sighir.post_req = s.get, s.post
    args = sighir.build().parse_args(['register', '--company', 'logika'])
    rc, out = output(lambda: args.func(args))
    assert rc == 1 and '--tecnico' in out and not s.writes()


def testRegisterLembraBuildDaEmpresa():
    s = FakeServer()
    rc, out = output(lambda: register(s, 'MICNOVO', 'ETL123'))
    assert rc == 0 and 'rode flash' not in out, out
    sighir.get_req, sighir.post_req = s.get, s.post
    args = sighir.build().parse_args(['register', '--company', 'predileto', '--tecnico', 'Fulano'])
    real, sighir.core = sighir.core, fakeCore('MICNOVO3', 'ETL124')
    try:
        rc, out = output(lambda: args.func(args))
    finally:
        sighir.core = real
    assert rc == 0 and "build 'logika', não a da predileto: rode flash" in out, out


def testVersaoDaBuild():
    data = b'\x00ESP-IDF v5.5.5\x00 in Internet\x00v6.5.3\x00,CH:\x00 lib v1.2.3-dirty'
    assert sighir.buildVersion(data) == (6, 5, 3)
    assert sighir.buildVersion(b'sem versao') is None and sighir.buildVersion(None) is None


def testVereditosDoAutodiagnostico():
    from tools.quality import parseDiagnostic
    ok = ['pressworking', 'pressworking', 'tempworking', '$ETEV20!']
    assert parseDiagnostic(ok) == {'pressao': True, 'sopro': True, 'temperatura': True, 'sensor': True}
    assert parseDiagnostic(['pressworking', '$NOBLOW!', '$ERROR!', 'tempworking', '$ETEV24!']) == \
        {'pressao': True, 'sopro': False, 'temperatura': True, 'sensor': False}
    assert parseDiagnostic(['$ERROR!', 'ERROR', '$ETEV20!']) == \
        {'pressao': False, 'sopro': False, 'temperatura': False, 'sensor': True}          # SEM PRESSÃO A TELA PULA O SOPRO
    assert parseDiagnostic(['pressworking']) == {'pressao': True} and parseDiagnostic([]) == {}


def testVereditosLidosDaSerial():
    from tools.quality import VERDICT_RE
    line = '$ETEV08! pressworking SttReq $ERROR! ERROR tempworking $ETEV24! $ETKAACK!'
    assert VERDICT_RE.findall(line) == ['pressworking', '$ERROR!', 'ERROR', 'tempworking', '$ETEV24!']


def flashCore(fwVersion, company, esp='MICINST'):
    calls    = []
    firmware = types.SimpleNamespace(file=None)

    def download(target):
        calls.append(('download', target))
        firmware.file = {'bytes': b'x\x00v5.5.5\x00v6.5.3\x00'}
        return True

    firmware.download = download
    fake = types.SimpleNamespace(
        robustSync=lambda: True, readEspId=lambda: esp, readSetting=lambda key: company,
        readFirmware=lambda: {'status': 'ok', 'version': fwVersion}, versionStr=str, MIN_FIRMWARE=(6, 5, 3),
        rearmUpdate=lambda e: calls.append(('rearm', e)) or True, recover=lambda: True,
        server=types.SimpleNamespace(firmware=firmware),
        updater=types.SimpleNamespace(percentage=-1, setup=lambda: None, start=lambda: calls.append(('flash',)) or True),
        device=types.SimpleNamespace(disconnect=lambda: None))
    return fake, calls


def runFlash(fake, server, *argv):
    import tempfile
    sighir.get_req, sighir.post_req = server.get, server.post
    args = sighir.build().parse_args(['flash', *argv])
    real, realState, sighir.core = sighir.core, sighir.FLASH_STATE, fake
    sighir.FLASH_STATE = os.path.join(tempfile.mkdtemp(), 'flash.json')
    try:
        return output(lambda: args.func(args))
    finally:
        sighir.core, sighir.FLASH_STATE = real, realState


def testFlashAparelhoNovoUsaBuildGenerica():
    fake, calls = flashCore((6, 5, 2), 'fat', esp='MICNOVO')
    rc, out = runFlash(fake, FakeServer())
    assert ('download', 'admin_sighir') in calls and not [c for c in calls if c[0] == 'rearm'], calls
    assert ('flash',) in calls and rc == 0, (rc, out)


def testFlashCadastradoReArmaEPulaQuandoAtualizado():
    s = FakeServer()
    s.devices['MICINST']['company'] = LOGIKA
    fake, calls = flashCore((6, 5, 3), 'logika')
    rc, out = runFlash(fake, s)
    assert calls == [('rearm', 'MICINST'), ('download', 'MICINST')] and rc == 0 and 'já atualizado' in out, (calls, out)
    fake, calls = flashCore((6, 5, 3), 'fat')
    rc, out = runFlash(fake, s)
    assert ('flash',) in calls and rc == 0, (calls, out)


def testFlashRecusaBuildAbaixoDoMinimo():
    fake, calls = flashCore((6, 5, 2), 'fat', esp='MICNOVO')
    fake.MIN_FIRMWARE = (6, 6, 0)
    rc, out = runFlash(fake, FakeServer())
    assert rc == 2 and ('flash',) not in calls and 'abaixo do mínimo' in out, (rc, calls)
    rc, out = runFlash(fake, FakeServer(), '--forcar')
    assert ('flash',) in calls, calls


def testQualidadeRecusaEtapaDesconhecida():
    args = sighir.build().parse_args(['qualidade', 'serial', 'banana'])
    rc, out = output(lambda: args.func(args))
    assert rc == 1 and 'banana' in out


def testSessaoEmOrdemEVereditoDoRelatorio():
    esp = 'MICREL1'
    session.record(esp, 'aparelho', firmware='v6.5.3', status='ok', minimo='v6.5.3', sensor_id='ETL1', debug=False)
    session.record(esp, 'qualidade', etapa='sensor', ok=False, detalhe='primeira', medido='primeira')
    session.record(esp, 'qualidade', etapa='sensor', ok=True, detalhe='refeito', medido='refeito')
    session.record(esp, 'qualidade', etapa='sopro-incompleto-fraco', ok=True, detalhe='3/3', medido='3/3 recusados')
    data = report.Report(esp, 'Fulano <de Tal>', 'obs & nota').update()
    tests = {t['id']: t for t in data['ensaios']}
    assert data['veredito']['codigo'] == 'incompleto' and (data['veredito']['aprovados'], data['veredito']['total']) == (2, 15)
    assert tests['sensor']['medido'] == 'refeito' and tests['sensor']['situacao'] == 'aprovado'      # VALE A ÚLTIMA RODADA
    assert tests['serial']['situacao'] == 'nao_realizado' and tests['sopro-incompleto-fraco']['nome'] == 'Sopro incompleto fraco'
    assert data['tecnico'] == 'Fulano <de Tal>' and data['observacoes'] == 'obs & nota' and data['numero'].endswith('REL1')
    assert json.loads(json.dumps(data)) == data                                                      # VAI COMO JSON PARA O SERVIDOR


def testRelatorioSemTestes():
    data = report.Report('MICREL2', 'X', None).update()
    assert data['veredito']['codigo'] == 'nao_realizado' and data['periodo'] is None and data['ambiente'] is None


def testRelatorioReprovadoListaAsEtapas():
    session.record('MICREL3', 'qualidade', etapa='com-alcool', ok=False, detalhe='0/1', medido='0/1 como esperado')
    session.record('MICREL3', 'flash', ok=False, antes='v6.5.2', build='v6.5.2', empresa='sighir', detalhe='abaixo do mínimo')
    data = report.Report('MICREL3', 'X', None).update()
    assert data['veredito']['codigo'] == 'reprovado' and 'Teste real com álcool' in data['veredito']['texto']
    assert data['firmware'][0]['detalhe'] == 'abaixo do mínimo' and data['firmware'][0]['ok'] is False


def testSessaoVelhaNaoEntraNoRelatorio():
    path = session.sessionPath('MICVELHO')
    old  = {'tipo': 'qualidade', 'etapa': 'serial', 'ok': True, 'quando': (datetime.now() - timedelta(hours=30)).isoformat(timespec='seconds')}
    json.dump([old], open(path, 'w'))
    session.record('MICVELHO', 'qualidade', etapa='sensor', ok=True)
    assert [e['etapa'] for e in session.load('MICVELHO')] == ['sensor']


def testCurvaDeCalibracaoEDatas():
    from tools.quality import curveMgl, parseDate
    assert curveMgl([2.0, 0.9995, 1.0, 0.0], 21340) == 0.0                          # AR LIMPO: ABAIXO DE 0,010 VIRA ZERO
    assert 0.03 < curveMgl([2.0, 0.9995, 1.0, 0.0], 8000) < 0.04
    assert curveMgl([2.0, 10.0, 1.0, 0.0], 50000) == 2.5                            # ESTOURO DO EXPOENTE SATURA COMO NO FIRMWARE
    assert parseDate('2026-05-12 14:33:21') == datetime(2026, 5, 12, 14, 33, 21)
    assert parseDate('12/05/2026') == datetime(2026, 5, 12) and parseDate('lixo') is None


def testPortaCertaComVariasPlacasUsb():
    from tools import core
    port = lambda name, vid: types.SimpleNamespace(device=name, vid=vid, description='USB')
    real = core.candidates, core.probe
    try:
        core.candidates = lambda: [port('/dev/ttyUSB0', 0x10c4), port('/dev/ttyACM0', 0x303a)]
        core.probe = lambda name: name == '/dev/ttyACM0'
        assert core.findPort() == '/dev/ttyACM0'
        core.probe = lambda name: False
        rc, out = output(core.findPort)
        assert rc == '/dev/ttyUSB0' and 'nenhuma das portas' in out
        asked = []
        core.candidates = lambda: [port('COM5', 0x10c4)]
        core.probe = lambda name: asked.append(name)
        assert core.findPort() == 'COM5' and not asked               # UMA PLACA SÓ: NEM SONDA
    finally:
        core.candidates, core.probe = real


def testOrdemDosConversores():
    from tools import core
    real = core.serial.tools.list_ports.comports
    ports = [types.SimpleNamespace(device=d, vid=v, description=t) for d, v, t in
             [('/dev/ttyACM0', 0x303a, 'USB JTAG'), ('/dev/ttyUSB1', 0x1a86, 'USB2.0-Ser!'), ('/dev/ttyUSB0', 0x10c4, 'CP2104'),
              ('/dev/rfcomm0', 0x1234, 'Bluetooth'), ('/dev/ttyS0', None, 'n/a')]]
    try:
        core.serial.tools.list_ports.comports = lambda: ports
        assert [p.device for p in core.candidates()] == ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyACM0']
    finally:
        core.serial.tools.list_ports.comports = real


class FakeDevice:
    """etilômetro simulado: devolve as linhas de evento vistas na bancada em 29/10/2026, uma por leitura."""
    def __init__(self, *runs):
        self.runs, self.lines, self.sent = list(runs), [], []

    def send(self, command, breakLine=True):
        self.sent.append(command)
        if command in ('$ETAT01!', 'STT') or command.startswith('STT;') and '_______1___' in command:
            self.lines = list(self.runs.pop(0)) if self.runs else []

    def get(self, timeout=1.0):
        return self.lines.pop(0) if self.lines else ''

    def clear(self, *a, **k):
        pass

    def expect(self, target='OK', command=None, fail=None, timeout=10):
        if command:
            self.send(command)
        return True

    def request(self, value, timeout=5.0):
        return '22999'


def fakeQuality(*runs, fake=None):
    from tools import quality
    fake = fake or FakeDevice(*runs)
    real = (quality.device, quality.sleep, quality.core.readSetting, quality.core.writeSetting)
    quality.device, quality.sleep = fake, (lambda s: None)
    quality.core.readSetting  = lambda key, **k: {'telemetry': '2', 'blowProb': '0.5'}.get(key)
    quality.core.writeSetting = lambda key, value, **k: True
    q = quality.Quality({'version': (6, 5, 3), 'status': 'ok'}, 'MICSIM', 'ETL999')
    restore = lambda: setattr(quality, 'device', real[0]) or setattr(quality, 'sleep', real[1]) or \
                      setattr(quality.core, 'readSetting', real[2]) or setattr(quality.core, 'writeSetting', real[3])
    return q, fake, restore


def testSoprosNenhumComTimeoutDaTela():
    q, fake, restore = fakeQuality(['$ETEV11!'], ['$ETEV11!'], ['$ETEV05!'])
    try:
        rc, out = output(lambda: q.noBlow(3))
    finally:
        restore()
    assert rc is False and '2/3 testes sem sopro' in out and 'blowProb 0.5 s' in out
    assert sum(1 for c in fake.sent if '_______1___' in c) == 3                 # 3 TESTES DISPARADOS PELA CHAVE SUNTECH


def testSoprosIncompletosRecusadosEAceitoReprova():
    q, fake, restore = fakeQuality(['$NOBLOW!', '', '$NOBLOW!', '$NOBLOW!'])
    try:
        rc, out = output(lambda: q.shortBlows(3, 'fraco'))
        assert rc is True and '3/3 sopros cortados' in out
        q2, fake2, restore2 = fakeQuality(['$NOBLOW!', '$ETEV05!'])
        rc2, out2 = output(lambda: q2.shortBlows(3, 'forte'))
        restore2()
    finally:
        restore()
    assert rc2 is False and 'um sopro curto foi ACEITO' in out2
    assert q.results[-1]['etapa'] == 'sopro-incompleto-fraco'


def testSoprosCompletosEAlcool():
    q, fake, restore = fakeQuality(['$NOBLOW!', '$ETEV05!', '[23000,23000]', '$ETEV29!'], ['$ETEV05!', '$ETEV29!'])
    try:
        rc, out = output(lambda: q.fullBlows(2, 'medio'))
        q2, _, restore2 = fakeQuality(['$ETEV05!', '$ETEV300123!'])
        rc2, out2 = output(lambda: q2.alcohol(True, 1))
        restore2()
    finally:
        restore()
    assert rc is True and '2/2 como esperado' in out and '1 sopro(s) cortado(s)' in out and 'analog 22999' in out
    assert rc2 is True and 'ÁLCOOL 0.123 mg/L' in out2 and 'Desligar Display' in out2


def testAutodiagnosticoPelaSerial():
    q, fake, restore = fakeQuality()
    fake.lines = ['pressworking', 'SttReq', '$NOBLOW! pressworking', 'tempworking', '$ETEV20!']
    try:
        rc, out = output(q.selfDiagnostic)
    finally:
        restore()
    assert rc is True and 'pressao OK, sopro OK, temperatura OK, sensor OK' in out


class FakeBench(FakeDevice):
    """bancada simulada inteira: além dos testes roteirizados, responde /get-data, coefs, TST_* e $ETKA!."""
    DATA = {'temperature': 24.6, 'humidity': 58.2, 'analog': 21340, 'filtered': 21338.5, 'filtered_analog': 21338.5,
            'pressure': 37.04, 'driving': 0, 'chave': 0}

    def __init__(self, coefs, *runs):
        super().__init__(*runs)
        self.coefs = coefs

    def send(self, command, breakLine=True):
        super().send(command, breakLine)
        self.lines += [json.dumps(self.DATA)] if command == '/get-data' else [json.dumps(self.coefs)] if command == 'coefs' else []


CURVE_CLEAN   = '[21300,21290,21310,21280,21300,21295,21305,21290,21300,21310]'
CURVE_ALCOHOL = '[21300,20100,17600,14200,11800,10400,9900,10300,11600,13200]'
CALIBRATED    = {'c1': 2.0, 'c2': 0.9995, 'c3': 1.0, 'c4': 0.5, 'zero': 20450,
                 'timestamp': f'{datetime.now() - timedelta(days=120):%Y-%m-%d %H:%M:%S}'}


def benchSession(esp, coefs=CALIBRATED, debug=False):
    full = ['$NOBLOW!', '$ETEV05!', CURVE_CLEAN, '$ETEV29!']
    runs = [['$ETEV11!']]*3 + [['$NOBLOW!']*3]*3 + [full]*9 + [['$ETEV05!', CURVE_CLEAN, '$ETEV29!'], ['$ETEV05!', CURVE_ALCOHOL, '$ETEV300123!']]
    q, fake, restore = fakeQuality(fake=FakeBench(coefs, *runs))
    q.espId, q.sensorId = esp, 'ETL3550904305917103' if debug else 'ETL9988440764401997'
    q.TEMP_WINDOW = q.SENSOR_WINDOW = 0.05
    q.SAMPLE_DT, q.REST_SAMPLES = 0.01, 5
    session.record(esp, 'aparelho', firmware='v6.5.3', status='ok', minimo='v6.5.3', sensor_id=q.sensorId, debug=debug,
                   telemetria='suntech (configurada no aparelho)')
    try:
        def battery():
            q.serial(); q.temperature(); q.sensor(); q.calibration(); q.pressure()
            fake.lines = ['pressworking', '$NOBLOW! pressworking', 'tempworking', '$ETEV20!']
            q.selfDiagnostic(); q.noBlow(3)
            for force in ('fraco', 'medio', 'forte'):
                q.shortBlows(3, force)
            for force in ('fraco', 'medio', 'forte'):
                q.fullBlows(3, force)
            q.alcohol(False, 1); q.alcohol(True, 1)
        output(battery)
    finally:
        restore()
    return q


def testBancadaCompletaSaiAptaComOsNumeros():
    q = benchSession('MICAPTO')
    assert not q.failed(), q.failed()
    data  = report.Report('MICAPTO', 'Paulo Ricardo', 'bancada 2').update()
    tests = {t['id']: t for t in data['ensaios']}
    assert data['veredito']['codigo'] == 'apto' and data['veredito']['aprovados'] == 15, data['veredito']
    assert data['ambiente'] == {'temperatura': 24.6, 'umidade': 58.2} and data['blow_prob'] == 0.5
    assert tests['sensor']['dados']['analog']['media'] == 21340 and tests['pressao']['dados']['repouso']['media'] == 37.04
    assert tests['calibracao']['dados']['idade_dias'] == 120 and tests['calibracao']['dados']['mgl_ar_limpo'] == 0.0
    assert len(tests['sopro-completo-medio']['dados']['testes']) == 3 and tests['com-alcool']['dados']['testes'][0]['mgl'] == 0.123
    assert tests['com-alcool']['dados']['testes'][0]['curva'][3] == 14200 and data['aparelho']['sensor_producao'] is True
    assert all(t['situacao'] == 'aprovado' for t in data['ensaios'])


def testBancadaComSensorDeDebugNaoLibera():
    benchSession('MICDEBUG', coefs={}, debug=True)
    verdict = report.Report('MICDEBUG', 'X', None).update()['veredito']
    assert verdict['codigo'] == 'reprovado' and 'sensor de debug' in verdict['texto']
    assert 'Calibração do sensor' in verdict['texto']                                         # SEM COEFICIENTES NO CARTUCHO


def testCalibracaoVencidaReprova():
    old = {**CALIBRATED, 'timestamp': f'{datetime.now() - timedelta(days=400):%Y-%m-%d %H:%M:%S}'}
    q, fake, restore = fakeQuality(fake=FakeBench(old))
    q.SAMPLE_DT, q.SENSOR_WINDOW = 0.01, 0.05
    try:
        rc, out = output(q.calibration)
    finally:
        restore()
    assert rc is False and 'vencida' in out


class FakeBenchCore:
    """aparelho para o configurar/relatorio: guarda as settings, grava pelo writeSetting e relê depois do restart."""
    def __init__(self, esp, config):
        self.esp, self.config, self.written, self.restarted = esp, dict(config), [], 0
        self.device = types.SimpleNamespace(disconnect=lambda: None)
        self.DEVICE_SETTINGS, self.TEXT_SETTINGS, self.typedValue = sighir.core.DEVICE_SETTINGS, sighir.core.TEXT_SETTINGS, sighir.core.typedValue

    def robustSync(self):
        return True

    def readEspId(self):
        return self.esp

    def readConfig(self):
        return dict(self.config)

    def writeSetting(self, key, value):
        self.written.append((key, value))
        self.config[key] = value if key in self.TEXT_SETTINGS or key == 'remote' else self.typedValue(value)
        return True

    def restart(self):
        self.restarted += 1
        return True


def runCli(fake, server, *argv):
    sighir.get_req, sighir.post_req = server.get, server.post
    args = sighir.build().parse_args(list(argv))
    real, sighir.core = sighir.core, fake
    try:
        return output(lambda: args.func(args))
    finally:
        sighir.core = real


def testConfigurarMostraEDepoisGravaComOPedido():
    fake = FakeBenchCore('MICCFG', {**CONFIG, 'company': 'sighir', 'maneuver_time': 1, 'max_postpone': 3})
    rc, out = runCli(fake, FakeServer(), 'configurar', '--company', 'logika', '--set', 'postpone_time=10')
    assert rc == 3 and not fake.written and 'maneuver_time' in out and '(pedido)' in out      # SEM --yes SÓ MOSTRA
    rc, out = runCli(fake, FakeServer(), 'configurar', '--company', 'logika', '--set', 'postpone_time=10', '--yes')
    assert rc == 0 and fake.restarted == 1 and 'gravada e conferida' in out, out
    assert dict(fake.written) == {'maneuver_time': '5', 'max_postpone': '2', 'postpone_time': '10', 'remote': '{"postpone_time":10}'}
    assert fake.config['company'] == 'sighir'                                                 # A BUILD QUE RODA NÃO É ESCONDIDA
    assert 'comm_type' not in dict(fake.written)                                              # CHAVE ANTIGA DO CADASTRO DA EMPRESA
    event = session.load('MICCFG')[-1]
    assert event['tipo'] == 'configuracao' and event['alteradas']['postpone_time'] == {'antes': 5, 'depois': 10}


def testConfigurarJaNaConfiguracaoDaEmpresa():
    fake = FakeBenchCore('MICCFG2', CONFIG)
    rc, out = runCli(fake, FakeServer(), 'configurar', '--company', 'logika', '--yes')
    assert rc == 0 and not fake.written and fake.restarted == 0 and 'já está' in out


def testConfigurarRecusaChaveForaDaConfiguracao():
    fake = FakeBenchCore('MICCFG3', CONFIG)
    rc, out = runCli(fake, FakeServer(), 'configurar', '--company', 'logika', '--set', 'last_alcohol=0', '--yes')
    assert rc == 1 and not fake.written and 'last_alcohol' in out, out


def testQualidadeRecusaEspIdNaoNativo():
    fake = FakeBenchCore('admin_sighir', CONFIG)
    fake.MIN_FIRMWARE, fake.versionStr, fake.isNativeId = sighir.core.MIN_FIRMWARE, sighir.core.versionStr, sighir.core.isNativeId
    fake.readFirmware, fake.readSensorId = lambda: {'status': 'ok', 'version': (6, 5, 3)}, lambda: 'ETL1'
    rc, out = runCli(fake, FakeServer(), 'qualidade', 'serial')
    assert rc == 2 and 'erase' in out and not session.load('admin_sighir'), out


def testUpdaterDesisteSemSincronia():
    from objects.Updater import index as up
    tries     = []
    fake      = types.SimpleNamespace(expect=lambda *a, **k: tries.append(1) and False)
    real      = up.device
    up.device = fake
    try:
        updater = up.SerialUpdater()
        updater.SYNC_TRIES = 3
        rc, out = output(updater.start)
    finally:
        up.device = real
    assert rc is False and len(tries) == 3 and 'nada foi gravado' in out, (rc, tries)


def testRelatorioReenviaDefaultSettings():
    s    = FakeServer()
    fake = FakeBenchCore('MICINST', CONFIG)
    session.record('MICINST', 'qualidade', etapa='serial', ok=True, medido='10 ms')
    rc, out = runCli(fake, s, 'relatorio', '--tecnico', 'Ana')
    assert rc == 3 and not s.writes()
    rc, out = runCli(fake, s, 'relatorio', '--tecnico', 'Ana', '--yes')
    kind, endpoint, payload = s.writes()[-1]
    data = json.loads(payload['default_settings'])
    assert rc == 0 and (kind, endpoint) == ('PATCH', '/devices/MICINST') and 'gravado e conferido' in out, out
    assert data['settings'] == CONFIG and data['report']['tecnico'] == 'Ana' and data['report']['veredito']['codigo'] == 'incompleto'
    rc, out = runCli(FakeBenchCore('MICNOVO', CONFIG), s, 'relatorio', '--tecnico', 'Ana', '--yes')
    assert rc == 1 and 'register' in out                                                       # NÃO CADASTRADO: VAI NO register


if __name__ == '__main__':
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith('test') and callable(fn):
            try:
                fn()
                print(f'ok  {name}')
            except AssertionError as err:
                fails += 1
                print(f'FALHOU {name}: {str(err)[:500]}')
    print('\ntodos passaram' if not fails else f'\n{fails} falha(s)')
    sys.exit(1 if fails else 0)
