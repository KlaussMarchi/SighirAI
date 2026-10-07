#!/usr/bin/env python3
"""Testes do contrato.py, sem rede: simula a migração de 24/09/2026 (suntechs → telemetries, chip saindo de
devices) e confere que o diff acusa e que o verificar pega campo que as IAs usam e sumiu."""

import io
import os
import sys
import copy
import contextlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import contrato as ct  # noqa: E402


def field(tipo='string', obrigatorio=False, so_leitura=False):
    return {'tipo': tipo, 'obrigatorio': obrigatorio, 'so_leitura': so_leitura}


def contract(when):
    api = {}
    for route, use in ct.USO.items():
        read = sorted({f for names in use.get('le', {}).values() for f in names})
        write = {}
        for names in use.get('grava', {}).values():
            if isinstance(names, str):
                names = ct.writable(names.split(':', 1)[1])
            for f in names:
                write[f] = field()
        api[route] = {'leitura': read, 'escrita': write, 'metodos': ['POST'], 'total': 1}
    return {'capturado': when, 'raiz_api': sorted(r.strip('/') for r in api), 'api': api,
            'banco': {'tabelas': {'Etilometros_device': ['id', 'chip', 'plate_id']},
                      'migracoes': ['Etilometros.0029_anomaly_category']}}


def run(fn, *args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        result = fn(*args)
    return result, out.getvalue()


def testDiffAcusaMigracao():
    old = contract('antes')
    old['api']['suntechs/'] = {'leitura': ['id', 'is_connected'], 'escrita': {'id': field()}, 'metodos': ['POST']}
    old['api']['devices/']['escrita']['chip'] = field()
    new = contract('depois')
    new['api']['devices/']['escrita']['company'] = field(tipo='field', obrigatorio=True)
    old['api']['devices/']['escrita']['company'] = field(tipo='field')
    new['banco']['tabelas']['Etilometros_device'] = ['id', 'plate_id', 'telemetry_id']
    new['banco']['migracoes'].append('Etilometros.0030_device_installation')
    n, out = run(ct.diff, old, new)
    assert '- rota SUMIU: suntechs/' in out, out
    assert '- campo de escrita SUMIU: chip' in out, out
    assert "~ campo de escrita mudou: company obrigatorio: False → True" in out, out
    assert '+telemetry_id' in out and '-chip' in out, out
    assert '+ migração nova: Etilometros.0030_device_installation' in out, out
    assert 'usado em:' in out          # aponta o código que ainda cita a rota/campo
    assert n == 5, n


def testDiffSemMudanca():
    n, out = run(ct.diff, contract('a'), contract('b'))
    assert n == 0 and 'nada mudou' in out, out


def testVerificarPegaCampoUsado():
    live = contract('agora')
    assert run(ct.verify, live)[0] == 0
    live['api']['devices/']['escrita'].pop('plate')                 # o install grava plate
    live['api']['telemetries/']['escrita']['chip']['so_leitura'] = True
    del live['api']['anomalies/']
    missing, out = run(ct.verify, live)
    assert missing == 6, out              # Tester install, Tester edit e Helper gravam plate; chip: Tester e Helper
    assert 'Tester install' in out and 'plate' in out and 'FALTA a rota anomalies/' in out, out


def testWritableDoHelper():
    assert 'plate' in ct.writable('devices') and 'chip' in ct.writable('telemetries')


if __name__ == '__main__':
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith('test') and callable(fn):
            try:
                fn()
                print(f'ok  {name}')
            except AssertionError as err:
                fails += 1
                print(f'FALHOU {name}: {str(err)[:600]}')
    print('\ntodos passaram' if not fails else f'\n{fails} falha(s)')
    sys.exit(1 if fails else 0)
