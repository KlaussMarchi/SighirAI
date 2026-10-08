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
from tools import sighir  # noqa: E402

MIX2, MIX, SUNTECH, ENTRACK = '17131425000130', '17131425000132', '44922499000', '12729135000171'
COMPANIES = [{'id': MIX2, 'type': 'telemetry', 'value': '5', 'label': 'MIX TELEMATICS (NOVO)'},
             {'id': MIX, 'type': 'telemetry', 'value': '0', 'label': 'MIX TELEMATICS'},
             {'id': SUNTECH, 'type': 'telemetry', 'value': '2', 'label': 'SUNTECH'},
             {'id': ENTRACK, 'type': 'telemetry', 'value': '6', 'label': 'ENTRACK'},
             {'id': '29863420000930', 'type': 'transportation', 'value': 'predileto', 'label': 'EXPRESSO PREDILETO'},
             {'id': '40000000000100', 'type': 'transportation', 'value': 'logika', 'label': 'LOGIKA TRANSPORTES'}]
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
        ensureNativeEspId=lambda: esp, readSensorId=lambda: sensor, readEspId=lambda: esp,
        device=types.SimpleNamespace(disconnect=lambda: None), versionStr=str, MIN_FIRMWARE=(6, 0, 0))


def register(server, esp, sensor, *argv):
    sighir.get_req, sighir.post_req = server.get, server.post
    args = sighir.build().parse_args(['register', '--company', 'logika', *argv])
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
        ensureNativeEspId=lambda: 'MICNOVO', readSensorId=lambda: 'ETL123',
        device=types.SimpleNamespace(disconnect=lambda: None), versionStr=str, MIN_FIRMWARE=(6, 0, 0))
    args = sighir.build().parse_args(['register', '--company', 'predileto', '--series', '7',
                                      '--modulo', '1700088888', '--chip', 'N/A'])
    real, sighir.core = sighir.core, fake
    try:
        assert args.func(args) == 0, s.calls
    finally:
        sighir.core = real
    writes = s.writes()
    assert writes[0] == ('POST', '/telemetries', {'id': '1700088888'}), writes
    kind, endpoint, payload = writes[1]
    assert (kind, endpoint) == ('POST', '/devices')
    assert payload == {'company': '29863420000930', 'series_num': '00007', 'id': 'MICNOVO', 'sensor_id': 'ETL123',
                       'need_update': True, 'telemetry': '1700088888'}, payload


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
