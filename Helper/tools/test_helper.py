"""
Testes do Sighir Helper AI — sem rede e sem escrever nada.

    python tools/test_helper.py

Cobrem a decodificação de eventos, as pistas automáticas do `veiculo`, as travas de escrita da API e a
ligação com a base: todo `$ETEVnn` que o firmware em ../docs/hardware/Main emite precisa ter tradução.
"""

import os
import re
import sys
import argparse
import subprocess
from datetime import datetime, timedelta, timezone

TOOLS = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, TOOLS)

import helper  # noqa: E402  (já se re-executa no .venv)
from api import Api, WRITABLE  # noqa: E402

DOCS = os.environ.get('SIGHIR_DOCS') or os.path.join(os.path.dirname(TOOLS), '..', 'docs')


def testDecode():
    assert helper.decode('$ETEV300420!') == ('$ETEV30', 'Álcool Detectado', '0.420 mg/L')
    assert helper.decode('$ETEV300000!')[2].startswith('SEM COEFICIENTES')
    assert helper.decode('$ETEV131980!')[2] == '1980 sopros'
    assert helper.decode('$ETEV09ETL5405249717821081!')[2] == 'sensor ETL5405249717821081'
    assert helper.decode('$ETEV404821!')[2] == 'digitou 4821'
    assert helper.decode('!ETEV23$')[0] == '!ETEV23'
    assert helper.decode('$ETEV01!') == ('$ETEV01', 'Veículo Desbloqueado', '')
    assert helper.decode('lixo serial')[0] is None


def testHelpers():
    assert helper.plateKey(' abc-1d23 ') == 'ABC1D23'
    assert helper.brt('2026-09-23T15:02:07Z') == '23/09 12:02:07'
    assert helper.brt(None) == '?'
    assert helper.parseValue('true') is True and helper.parseValue('False') is False
    assert helper.parseValue('5') == 5 and helper.parseValue('null') is None
    assert helper.parseValue('6.4.8') == '6.4.8'


def testHints():
    now = datetime.now(timezone.utc)
    recent = {'timestamp': now.isoformat()}
    old = {'timestamp': (now - timedelta(days=20)).isoformat()}

    def run(tel='SUNTECH', logs=(), last=recent, counts=None, cal=100, version='6.4.8', anomalies=()):
        return ' | '.join(helper.hints(tel, list(logs), last, counts or {}, cal, version, list(anomalies)))

    assert 'S6' in run(counts={'$ETEV08': 4})
    assert 'S7' in run(counts={'$ETEV24': 1})
    assert 'S11' in run(counts={'$ETEV35': 2})
    assert 'S10' in run(logs=[{'event': '$ETEV300000!'}])
    assert 'S9' in run(counts={'$ETEV11': 9, '$ETEV05': 1})
    assert 'S13' in run(last=None) and 'S13' in run(last=old)
    assert 'S18' in run(cal=400)
    assert 'S14' in run(version='1.0.0')
    assert 'S19' in run(tel='FELKA TRANSPORTES E LOGISTICA')
    assert 'S1 hip. 1' in run(counts={'$ETEV01': 12})
    assert 'normal na MiX' in run(tel='MIX TELEMATICS (NOVO)', counts={'$ETEV16': 3})
    assert run() == ''  # aparelho saudável: nenhuma pista
    steps = helper.checklists(['x (S6)', 'y (S1 hip. 1, S3)'], 'SUNTECH')
    assert steps == ['Reiniciamentos Inesperados', 'Problemas de Requisição de Teste › Suntech',
                     'Problemas de Bloqueio › Suntech'], steps


def testChecklistsExist():
    """toda seção citada em CHECKLISTS precisa existir no troubleshooting.md (vem do Notion)."""
    path = os.path.join(DOCS, 'troubleshooting.md')
    if not os.path.isfile(path):
        print('   (../docs/troubleshooting.md ausente — pulado)')
        return
    text = open(path, encoding='utf-8').read()
    missing = sorted({n for n in helper.CHECKLISTS.values() if f'## {n}' not in text})
    assert not missing, f'seções sumiram do troubleshooting.md (renomeadas no Notion?): {missing}'


def testWriteGuards():
    client = Api()
    for resource, data in (('logs', {'event': 'x'}), ('anomalies', {'desc': 'x'}), ('devices', {'id': 'x'})):
        try:
            client.patch(resource, 'X', data)
        except PermissionError:
            continue
        raise AssertionError(f'escrita em {resource} com {data} deveria ser bloqueada')
    try:
        client.get('logs/', limit='all')
    except ValueError:
        pass
    else:
        raise AssertionError('limit=all deveria ser recusado')
    assert 'need_update' in WRITABLE['devices'] and 'plate' in WRITABLE['devices']
    assert 'chip' in WRITABLE['telemetries'] and 'chip' not in WRITABLE['devices']
    assert 'etilometers' not in WRITABLE        # instalação se edita no device desde 24/09/2026


def testPatchNeedsConfirmation():
    """sem --sim o patch só mostra — confere isso sem rede, trocando o get da API."""
    client = helper.api()
    original = client.get
    client.get = lambda endpoint, **p: {'need_update': False}
    try:
        args = argparse.Namespace(recurso='devices', id='MIC1', campos=['need_update=true'], sim=False)
        assert helper.cmdPatch(args) == 3
    finally:
        client.get = original


def testFirmwareEventsCovered():
    firmware = os.path.join(DOCS, 'hardware', 'Main')
    if not os.path.isdir(firmware):
        print('   (firmware ausente em ../docs/hardware/Main — pulado)')
        return
    found = set()
    for root, dirs, files in os.walk(firmware):
        dirs[:] = [d for d in dirs if d != 'assets']
        for name in files:
            if name.endswith(('.h', '.ino')):
                text = open(os.path.join(root, name), encoding='utf-8', errors='replace').read()
                found |= {f'$ETEV{n}' for n in re.findall(r'\$ETEV(\d{2})', text)}
    missing = sorted(code for code in found if code not in helper.EVENTS)
    assert not missing, f'eventos do firmware sem tradução no helper.py: {missing}'


def testKnowledgeBase():
    kb = os.path.join(DOCS, 'tools', 'kb.py')
    if not os.path.isfile(kb):
        print('   (../docs/tools/kb.py ausente — pulado)')
        return
    res = subprocess.run([sys.executable, kb, 'busca', 'contrassenha', '-n', '1'], capture_output=True,
                         env=dict(os.environ, PYTHONIOENCODING='utf-8'), timeout=120)
    assert res.returncode == 0 and b'contrassenha' in res.stdout.lower(), res.stdout[-300:]


if __name__ == '__main__':
    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith('test') and callable(fn):
            try:
                fn()
                print(f'ok  {name}')
            except Exception as err:
                failed += 1
                print(f'FALHOU  {name}: {err}')
    print('\ntodos passaram' if not failed else f'\n{failed} teste(s) falharam')
    sys.exit(1 if failed else 0)
