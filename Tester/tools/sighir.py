#!/usr/bin/env python3
"""
Sighir Tester AI — CLI unificada de operações.

Ponto único de entrada, reutilizável e idempotente, usado tanto pelo
Claude Code quanto pelo Agy/Gemini, em Linux ou Windows. Cada subcomando
imprime saída clara e parseável.

Subcomandos:
  preflight [--quick]    checa/instala dependências (cross-platform)
  init                   init de sessão numa só chamada (preflight quick + status)
  status                 conecta, sincroniza, lê firmware/esp_id/sensor_id
  firmware               lê e classifica a versão de firmware
  settings [chaves]      lê as settings do device (--set chave=valor grava; --restart reinicia)
  telemetry [modo]       mostra/configura a telemetria (mix|suntech|mix2|entrack) + reinicia + confere
  block / unblock        bloqueia / desbloqueia o veículo (confirma pelo $ETEV02! / $ETEV01!)
  erase [--force]        garante esp_id nativo (--force = reset de fábrica mesmo se já for nativo)
  recover                tira o device de estado travado (reset+resync)
  register [opts]        cadastra o device no servidor (não-interativo)
  install <esp_id> ...   cria a instalação (aparelho ↔ placa ↔ telemetria) no servidor (exige --yes)
  server-device <id>     consulta o registro do device no servidor
  server-delete <id>     DELETA o device do servidor (hard delete, exige --yes)
  test [nome]            roda um teste do protocol.json (alcohol/blow/temp/sensor)
  flash                  re-arma + baixa + flasha firmware via serial (longo)

Exemplos:
  python tools/sighir.py init
  python tools/sighir.py settings telemetry vehicle_type
  python tools/sighir.py settings --set vehicle_type=1 --restart
  python tools/sighir.py telemetry entrack
  python tools/sighir.py register --company logika --series auto --suntech 1700023879 --chip N/A
  python tools/sighir.py install MIC123... --placa ABC1D23 --telemetria mix2 --instalador Fulano --yes
  python tools/sighir.py server-delete MIC123... --yes
  python tools/sighir.py flash
"""

import os
import sys
import argparse
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# roda no .venv preparado pelo tools/boot.py (mesmo se o agente foi aberto sem o launcher)
from tools import _venv
_venv.ensure(ROOT)

from tools import core
from tools.core import log
from utils.api import get_req, post_req


def cmdPreflight(args):
    from tools import preflight
    return 0 if preflight.run(quick=getattr(args, 'quick', False)) else 1


def cmdInit(args):
    """Init de sessão numa só chamada: preflight (quick) + status."""
    from tools import preflight
    if not preflight.run(quick=True):
        return 1
    return cmdStatus(args)


def cmdStatus(args):
    if not core.robustSync():
        return 1
    fw = core.readFirmware()
    espId = core.readEspId()
    sensorId = core.readSensorId()

    log('info', '----- STATUS -----')
    log('info', f"firmware  : {core.versionStr(fw['version'])} (raw={fw['raw']!r}) [{fw['status']}]")
    log('info', f"esp_id    : {espId}")
    log('info', f"sensor_id : {sensorId}")

    if fw['status'] == 'old':
        log('warn', 'FIRMWARE ANTIGO: $firmware! não respondeu formato válido. '
                    'Peça atualização (fluxo de versão antiga / WiFi).')
    elif fw['status'] == 'below_min':
        log('warn', f'firmware abaixo do mínimo ({core.versionStr(core.MIN_FIRMWARE)}). '
                    'Cadastro/telemetria bloqueados até atualizar.')
    else:
        log('ok', 'firmware OK — pronto para operar.')

    core.device.disconnect()
    return 0


def cmdFirmware(args):
    if not core.robustSync():
        return 1
    fw = core.readFirmware()
    log('info', f"firmware = {core.versionStr(fw['version'])} (raw={fw['raw']!r}) status={fw['status']}")
    if fw['status'] == 'old':
        log('warn', 'FIRMWARE ANTIGO — peça atualização ao usuário.')
    core.device.disconnect()
    return 0 if fw['status'] == 'ok' else 2


def cmdErase(args):
    if not core.robustSync():
        return 1

    # sem --force, o erase só age se o esp_id estiver sobrescrito (ensureNativeEspId
    # é no-op quando já é MIC...). Com --force, faz o reset de fábrica de qualquer jeito
    # (regenera o esp_id e volta TODAS as settings ao default — telemetry vira 2/Suntech).
    if getattr(args, 'force', False):
        log('warn', 'erase FORÇADO: o esp_id será REGENERADO e todas as settings voltam ao default')

        if not core.erase():
            core.device.disconnect()
            return 1

        espId = core.readEspId()
        log('ok', f'esp_id regenerado: {espId}')
    else:
        espId = core.ensureNativeEspId()

    core.device.disconnect()
    return 0 if espId else 1


def cmdRecover(args):
    ok = core.recover()
    if ok:
        fw = core.readFirmware()
        log('info', f"pós-recover: firmware {core.versionStr(fw['version'])} [{fw['status']}]")
    core.device.disconnect()
    return 0 if ok else 1


def resolveCompany(value):
    res = get_req('/companies?type=transportation')
    if res['status'] == 'error' or not res['data']:
        log('err', 'falha ao carregar empresas')
        return None, []
    # a API ignora o ?type= e devolve também as telemetrias (MIX '0', SUNTECH '2', MIX novo '5',
    # Entrack '6') — dono de aparelho é sempre transportadora, então filtro aqui
    companies = sorted((c for c in res['data'] if c.get('type') == 'transportation'),
                       key=lambda c: (c.get('label') or '').upper())
    match = next((c for c in companies if c.get('value') == value), None)
    return (match.get('id') if match else None), companies


def nextSeries():
    res = get_req('/devices')
    devices = res['data'] or []
    nums = [int(d['series_num']) for d in devices if str(d.get('series_num', '')).isdigit()]
    return str((max(nums) if nums else 0) + 1).zfill(5)


def cmdRegister(args):
    if not args.company:
        _, companies = resolveCompany('')
        log('info', 'empresas disponíveis (use --company <value>):')
        for c in companies:
            print(f"  {c.get('value')!r:14} -> {c.get('label')}")
        return 1

    if not core.robustSync():
        return 1

    fw = core.readFirmware()
    if fw['status'] != 'ok':
        log('err', f"cadastro BLOQUEADO: firmware {fw['status']} ({core.versionStr(fw['version'])}). "
                   f"Atualize para >= {core.versionStr(core.MIN_FIRMWARE)} antes de cadastrar.")
        core.device.disconnect()
        return 2

    companyId, companies = resolveCompany(args.company)
    if not companyId:
        log('err', f"empresa {args.company!r} não encontrada. Rode sem --company para listar.")
        core.device.disconnect()
        return 1

    espId = core.ensureNativeEspId()
    if not espId:
        core.device.disconnect()
        return 1
    sensorId = core.readSensorId()
    if not sensorId:
        log('err', 'não foi possível ler sensor_id')
        core.device.disconnect()
        return 1

    series = nextSeries() if (not args.series or args.series == 'auto') else args.series.zfill(5)

    suntech = args.suntech if (args.suntech and args.suntech.lower() != 'none') else None
    chip = args.chip if args.chip else 'N/A'

    core.device.disconnect()

    if suntech and suntech != 'N/A':
        log('info', f'registrando chip suntech {suntech}')
        sres = post_req('/suntechs', {'id': suntech})
        if sres['status'] == 'error':
            log('err', f"falha ao registrar suntech: {sres.get('data')}")
            return 1
        log('ok', 'suntech registrado')

    payload = {
        'company': companyId,
        'series_num': series,
        'id': espId,
        'sensor_id': sensorId,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'suntech': suntech,
        'chip': chip,
        'need_update': True,
    }

    log('info', f'POST /devices: {payload}')
    res = post_req('/devices', payload)
    if res['status'] == 'error':
        log('err', f"erro ao registrar: {res.get('data')}")
        return 1

    log('ok', f"DEVICE {espId} REGISTRADO (série {series}, empresa {args.company}).")
    log('warn', f'lembrete: cole a etiqueta {series} no aparelho.')
    return 0


# aliases amigáveis -> value real no protocol.json
TEST_ALIASES = {
    'alcohol': 'standard_test',
    'alcohol-blow': 'alcohol_test',
    'blow': 'blow_test',
    'temp': 'temperature_test',
    'sensor': 'sensor_test',
}


def listTests(checklist):
    log('info', 'testes disponíveis (use: test <nome>):')
    seen = {}
    for alias, value in TEST_ALIASES.items():
        seen.setdefault(value, []).append(alias)
    for item in checklist:
        aliases = ', '.join(seen.get(item['value'], [])) or '-'
        print(f"  {item['value']:18} [{aliases:14}] -> {item['label']}")


def cmdTest(args):
    from objects.Tester.protocol import Protocol

    proto = Protocol()
    if not args.name:
        listTests(proto.checklist)
        return 1

    key = TEST_ALIASES.get(args.name, args.name)
    target = next((t for t in proto.checklist if t['value'] == key), None)
    if not target:
        log('err', f"teste {args.name!r} não encontrado.")
        listTests(proto.checklist)
        return 1

    if not core.robustSync():
        return 1

    proto.telemetry = args.telemetry
    # não-interativo: nunca entra no loop de "tentar novamente?" (travaria headless)
    proto.forms.getBool = lambda *a, **k: False

    log('info', f"rodando \"{target['label']}\" (telemetria={proto.telemetry})")
    ok = False
    try:
        ok = proto.test(key)
    except AttributeError:
        # hiccup de USB: reconnect falhou e expect() acessou device None.
        # tratamos aqui (sem editar o core) para reportar em vez de crashar.
        log('err', 'device caiu da USB durante o teste (hiccup). Rode "recover" e tente de novo.')
        core.device.disconnect()
        return 3

    log('ok' if ok else 'err', f"RESULTADO {key}: {'OK' if ok else 'FALHOU'}")
    core.device.disconnect()
    return 0 if ok else 1


def cmdFlash(args):
    if not core.robustSync():
        return 1

    espId = core.readEspId()
    if not espId:
        log('err', 'não foi possível ler esp_id')
        core.device.disconnect()
        return 1

    # /update é one-shot — re-arma para garantir que o servidor sirva o firmware
    if not core.rearmUpdate(espId):
        core.device.disconnect()
        return 1

    log('info', 'baixando firmware (one-shot)...')
    if not core.server.firmware.download():
        log('err', 'download falhou')
        core.device.disconnect()
        return 1

    log('info', 'iniciando flash serial (pode levar ~4 min)...')
    core.updater.setup()
    core.updater.start()
    log('ok', 'flash concluído — verificando...')

    core.recover()
    fw = core.readFirmware()
    log('info', f"pós-flash: firmware {core.versionStr(fw['version'])} [{fw['status']}]")
    core.device.disconnect()
    return 0


def cmdSettings(args):
    """Lê (ou grava) settings do device. Sem --set, despeja tudo."""
    if not core.robustSync():
        return 1

    if args.set:
        for pair in args.set:
            if '=' not in pair:
                log('err', f'formato inválido: {pair!r} (use chave=valor)')
                core.device.disconnect()
                return 1

            key, value = pair.split('=', 1)

            if not core.writeSetting(key.strip(), value.strip()):
                core.device.disconnect()
                return 1

        if args.restart:
            core.restart()

        core.device.disconnect()
        return 0

    keys = args.keys or core.SETTING_KEYS
    log('info', '----- SETTINGS -----')

    for key, value in core.readSettings(keys).items():
        log('info', f'{key:16} = {value!r}')

    core.device.disconnect()
    return 0


def cmdTelemetry(args):
    """Configura o modo de telemetria (seta + reinicia + confere)."""
    if not core.robustSync():
        return 1

    if not args.mode:
        current = core.readSetting('telemetry')
        names = {str(v): k for k, v in core.TELEMETRIES.items()}
        log('info', f'telemetry = {current!r} ({names.get(str(current), "desconhecido")})')
        log('info', f'modos: {", ".join(f"{k}={v}" for k, v in core.TELEMETRIES.items())}')
        core.device.disconnect()
        return 0

    ok = core.setTelemetry(args.mode)
    core.device.disconnect()
    return 0 if ok else 1


def cmdBlock(args):
    if not core.robustSync():
        return 1
    ok = core.setBlock(True)
    core.device.disconnect()
    return 0 if ok else 1


def cmdUnblock(args):
    if not core.robustSync():
        return 1
    ok = core.setBlock(False)
    core.device.disconnect()
    return 0 if ok else 1


def cmdServerDevice(args):
    """Consulta o registro do device no servidor."""
    res = get_req(f'/devices/{args.esp_id}')

    if res['status'] == 'error' or not res.get('data'):
        log('err', f'device {args.esp_id} não encontrado no servidor')
        return 1

    log('info', f'----- {args.esp_id} -----')

    for key, value in res['data'].items():
        log('info', f'{key:18} = {value!r}')

    return 0


INSTALL_TELEMETRY = {'mix': '0', 'suntech': '2', 'mix2': '5', 'entrack': '6'}


def cmdInstall(args):
    """Cria a instalação no servidor (Etilometro = aparelho ↔ placa ↔ telemetria). Sem --yes só
    valida e mostra o que seria gravado. Procedimento: procedimentos/cadastro.md §13."""
    import requests
    from utils.api import API, handle_access_token

    esp = args.esp_id.strip()
    plate = args.placa.strip().upper()
    res = get_req(f'/devices/{esp}')
    if res['status'] == 'error' or not res.get('data'):
        log('err', f'device {esp} não existe no servidor — cadastre antes (register)')
        return 1

    companies = get_req('/companies').get('data') or []
    code = INSTALL_TELEMETRY[args.telemetria]
    tel = next((c for c in companies if c.get('type') == 'telemetry' and str(c.get('value')) == code), None)
    if not tel:
        log('err', f'telemetria {args.telemetria} (código {code}) não encontrada em /companies')
        return 1
    if args.telemetria == 'mix':
        log('warn', 'mix = MIX ANTIGO (0). A maior parte da frota MiX é MIX 2.0 → confirme; se for, use mix2')

    rows = get_req('/etilometers').get('data') or []
    same = [e for e in rows if (e.get('vehicle') or '').strip().upper() == plate or e.get('esp_id') == esp]

    payload = {'device': esp, 'vehicle_plate': plate, 'telemetry': tel['id'],
               'vehicle_type': 1 if args.tipo == 'carro' else 0}
    if args.instalador:
        payload['installer'] = args.instalador
    if args.apelido:
        payload['nickname'] = args.apelido

    log('info', f"instalação a criar (PRODUÇÃO): {payload}  [telemetria {tel.get('label')}]")
    for e in same:
        log('warn', f"já existe instalação {e.get('id')}: placa {e.get('vehicle')} ↔ {e.get('esp_id')} "
                    f"({e.get('telemetry_label')}, desde {str(e.get('installation_date'))[:10]})")
    if same and not args.duplicar:
        log('err', 'placa ou aparelho já instalados: é troca/edição? Remova/edite a antiga (Helper patch '
                   'ou server-delete) ou confirme com o usuário e rode com --duplicar')
        return 2
    if not args.yes:
        log('warn', 'nada foi gravado. Confirme os dados com o usuário e rode de novo com --yes')
        return 3

    access, _ = handle_access_token()
    r = requests.post(f'{API}/etilometers/', json=payload, timeout=30,
                      headers={'Authorization': f'Bearer {access}'})
    if not r.ok:
        log('err', f'servidor recusou ({r.status_code}): {r.text[:400]}')
        return 1

    check = [e for e in (get_req('/etilometers').get('data') or [])
             if (e.get('vehicle') or '').strip().upper() == plate and e.get('esp_id') == esp]
    log('ok' if check else 'err', f"instalação {'criada e conferida' if check else 'NÃO encontrada após o POST'}: "
                                  f"{plate} ↔ {esp} ({tel.get('label')})")
    return 0 if check else 1


def cmdServerDelete(args):
    """DELETE de verdade no servidor. `deleted=True` NÃO apaga nada (ver §13)."""
    from utils.api import delete_req

    res = get_req(f'/devices/{args.esp_id}')

    if res['status'] == 'error' or not res.get('data'):
        log('err', f'device {args.esp_id} não encontrado no servidor')
        return 1

    data = res['data']
    log('warn', 'REGISTRO A DELETAR (produção, hard delete, cascata p/ o Suntech vinculado):')

    for key in ('id', 'series_num', 'company', 'sensor_id', 'suntech', 'chip'):
        log('info', f'{key:12} = {data.get(key)!r}')

    if not args.yes:
        log('err', 'confirmação necessária: rode de novo com --yes (e CONFIRME com o usuário antes).')
        return 1

    delete_req(f'/devices/{args.esp_id}')
    check = get_req(f'/devices/{args.esp_id}')
    gone  = (check['status'] == 'error' or not check.get('data'))

    log('ok' if gone else 'err',
        f'{args.esp_id} {"REMOVIDO do servidor (404 na consulta)" if gone else "AINDA EXISTE — falhou"}')
    return 0 if gone else 1


def build():
    p = argparse.ArgumentParser(prog='sighir', description='Sighir Tester AI CLI')
    sub = p.add_subparsers(dest='cmd', required=True)

    pre = sub.add_parser('preflight')
    pre.add_argument('--quick', action='store_true', help='pula checagem se deps OK há < 24h (cache)')
    pre.set_defaults(func=cmdPreflight)

    sub.add_parser('init').set_defaults(func=cmdInit)
    sub.add_parser('status').set_defaults(func=cmdStatus)
    sub.add_parser('firmware').set_defaults(func=cmdFirmware)
    sub.add_parser('recover').set_defaults(func=cmdRecover)

    ers = sub.add_parser('erase')
    ers.add_argument('--force', action='store_true',
                     help='faz o reset de fábrica mesmo com esp_id já nativo (sem isto, só age se o esp_id estiver sobrescrito)')
    ers.set_defaults(func=cmdErase)

    st = sub.add_parser('settings')
    st.add_argument('keys', nargs='*', help='chaves a ler (sem isto, lê todas)')
    st.add_argument('--set', action='append', metavar='CHAVE=VALOR', help='grava uma setting (repetível)')
    st.add_argument('--restart', action='store_true', help='reinicia depois de gravar (necessário p/ telemetry)')
    st.set_defaults(func=cmdSettings)

    tel = sub.add_parser('telemetry')
    tel.add_argument('mode', nargs='?', choices=list(core.TELEMETRIES), help='sem isto, mostra o modo atual')
    tel.set_defaults(func=cmdTelemetry)

    sub.add_parser('block').set_defaults(func=cmdBlock)
    sub.add_parser('unblock').set_defaults(func=cmdUnblock)

    sdev = sub.add_parser('server-device')
    sdev.add_argument('esp_id')
    sdev.set_defaults(func=cmdServerDevice)

    sdel = sub.add_parser('server-delete')
    sdel.add_argument('esp_id')
    sdel.add_argument('--yes', action='store_true', help='confirma o hard delete em produção')
    sdel.set_defaults(func=cmdServerDelete)

    ins = sub.add_parser('install', help='cria a instalação (aparelho ↔ placa ↔ telemetria) no servidor')
    ins.add_argument('esp_id', help='MIC... já cadastrado (register)')
    ins.add_argument('--placa', required=True)
    ins.add_argument('--telemetria', required=True, choices=list(INSTALL_TELEMETRY),
                     help='mix2 = MIX 2.0 (maioria da frota MiX); mix = MIX antigo')
    ins.add_argument('--tipo', choices=['caminhao', 'carro'], default='caminhao')
    ins.add_argument('--instalador', help='nome de quem instalou')
    ins.add_argument('--apelido', help='nickname opcional')
    ins.add_argument('--duplicar', action='store_true', help='cria mesmo havendo instalação com a placa/aparelho')
    ins.add_argument('--yes', action='store_true', help='grava de verdade (depois de confirmar com o usuário)')
    ins.set_defaults(func=cmdInstall)

    reg = sub.add_parser('register')
    reg.add_argument('--company', help='value da empresa (ex: logika). Sem isto, lista as opções.')
    reg.add_argument('--series', default='auto', help='número de série ou "auto"')
    reg.add_argument('--suntech', default='none', help='ID suntech ou "none"')
    reg.add_argument('--chip', default='N/A', help='número do chip suntech ou "N/A"')
    reg.set_defaults(func=cmdRegister)

    tst = sub.add_parser('test')
    tst.add_argument('name', nargs='?', help='nome do teste (alcohol, alcohol-blow, blow, temp, sensor). Sem isto, lista.')
    tst.add_argument('--telemetry', default='mix', choices=['mix', 'suntech'], help='variante de telemetria (default: mix)')
    tst.set_defaults(func=cmdTest)

    sub.add_parser('flash').set_defaults(func=cmdFlash)
    return p


def main():
    args = build().parse_args()
    sys.exit(args.func(args))


if __name__ == '__main__':
    main()
