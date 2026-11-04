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
  install <esp_id> ...   instala o aparelho na placa (PATCH /devices: placa, telemetria, módulo; exige --yes)
  server-device <id>     consulta o registro do device no servidor
  onde <valor>           onde um MIC / sensor ETL / módulo / placa / nº de série já está cadastrado
  progresso              estado do flash em andamento (espera até 20 s e mostra a porcentagem)
  edit <esp_id> ...      edita um aparelho já cadastrado (empresa, módulo/chip, sensor, série, desinstalar; exige --yes)
  server-delete <id>     DELETA o device do servidor (hard delete, exige --yes)
  test [nome]            roda um teste do protocol.json (alcohol/blow/temp/sensor)
  flash [--forcar]       re-arma + baixa + flasha firmware via serial (longo; aparelho novo = build genérica; --arquivo BIN grava um .bin local)
  qualidade [etapas]     testes de qualidade (serial, temperatura, sensor, calibracao, pressao, autodiagnostico, sopro, sem-alcool, com-alcool)
  monitor                leituras ao vivo do /get-data (debug dos sensores)
  configurar --company X configuração padrão da empresa no aparelho (+ --set chave=valor; grava com --yes)
  relatorio --tecnico N  reenvia o default_settings (configuração + relatório de ensaio) do aparelho cadastrado

Exemplos:
  python tools/sighir.py init
  python tools/sighir.py settings telemetry vehicle_type
  python tools/sighir.py settings --set vehicle_type=1 --restart
  python tools/sighir.py telemetry entrack
  python tools/sighir.py register --company logika --series auto --modulo 1700023879 --chip N/A
  python tools/sighir.py install MIC123... --placa ABC1D23 --telemetria mix2 --instalador Fulano --yes
  python tools/sighir.py edit MIC123... --company logika --desinstalar --modulo 1700023880 --chip 8955... --yes
  python tools/sighir.py server-delete MIC123... --yes
  python tools/sighir.py flash
"""

import os
import re
import sys
import json
import time
import random
import argparse
import threading
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# roda no .venv preparado pelo tools/boot.py (mesmo se o agente foi aberto sem o launcher)
from tools import _venv
_venv.ensure(ROOT)

# SEM O LANÇADOR (PYTHONIOENCODING) O CONSOLE DO WINDOWS É cp1252 E UM "→" DERRUBARIA A CLI NO MEIO DO CADASTRO
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from tools import core
from tools.core import log
from utils.api import get_req, post_req
from tools.session import record
from tools.report import Report


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

    core.device.disconnect()
    dev = serverDevice(espId)

    log('info', '----- STATUS -----')
    log('info', f"firmware  : {core.versionStr(fw['version'])} (raw={fw['raw']!r}) [{fw['status']}]")
    log('info', f"esp_id    : {espId}")
    log('info', f"sensor_id : {sensorId}" + (' (DEBUG: build com bypass do sensor, não cadastre)' if sensorId in core.DEBUG_SENSORS else ''))
    log('info', f"servidor  : {deviceSummary(dev, get_req('/companies').get('data') or []) + ' → já cadastrado: edit' if dev else 'não cadastrado → register'}")

    if fw['status'] == 'old':
        log('warn', 'FIRMWARE ANTIGO: $firmware! não respondeu formato válido. '
                    'Peça atualização (fluxo de versão antiga / WiFi).')
    elif fw['status'] == 'below_min':
        log('warn', f'firmware abaixo do mínimo ({core.versionStr(core.MIN_FIRMWARE)}): qualidade e cadastro '
                    'bloqueados até atualizar (flash).')
    else:
        log('ok', 'firmware OK — pronto para operar.')

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


def serverDevice(esp):
    if not esp:
        return None

    res = get_req(f'/devices/{esp}/')
    return res.get('data') if res['status'] != 'error' else None


def nextSeries():
    res = get_req('/devices')
    devices = res['data'] or []
    nums = [int(d['series_num']) for d in devices if str(d.get('series_num', '')).isdigit()]
    return str((max(nums) if nums else 0) + 1).zfill(5)


PLATE = re.compile(r'^[A-Z]{3}\d[A-Z0-9]\d{2}$')
NO_VALUE = ('', 'NONE', 'N/A', 'NA')


def normPlate(value):
    """placa (antiga ou Mercosul) em maiúsculas; nome livre ('Portaria Predileto', 'MALETA_SIGHIR') fica como veio."""
    v = value.strip()
    return v.upper() if PLATE.match(v.upper()) else v


def optional(value):
    """'none'/'N/A'/vazio = sem valor (MiX não tem módulo nem chip)."""
    v = (value or '').strip()
    return None if v.upper() in NO_VALUE else v


def mixModule(esp):
    """MiX não tem rastreador com ID: desde a migração de 07/10/2026 cada aparelho MiX aponta para um módulo
    próprio `MIX-<esp_id>` em /telemetries, só para guardar a marca (MIX ou MIX 2.0)."""
    return f'MIX-{esp}'


def ensureModule(mod, chip=None, plate=None, brand=None, mine=False):
    """garante o módulo em /telemetries — era /suntechs, 404 desde a migração de 24/09/2026. Cria se não
    existe e grava o chip (mora no módulo desde 24/09/2026) e a marca (`brand` = CNPJ da telemetria, mora no
    módulo desde 07/10/2026; antes era `telemetry_company` no device). Recusa módulo já ligado ao aparelho de
    outra placa (Device.telemetry é único; `mine` = o módulo já é deste aparelho, não barra) e rastreador de
    outra marca. Devolve o registro ou None."""
    if mod.upper().startswith(('MIC', 'ETL')):
        log('err', f'{mod!r} é ID de aparelho/sensor, não de módulo (Suntech 1700…, Entrack 69…): confira com o usuário')
        return None
    res = get_req(f'/telemetries/{mod}/')
    cur = res.get('data') if res['status'] != 'error' else None
    if not cur:
        payload = {'id': mod, **({'chip': chip} if chip else {}), **({'brand': brand} if brand else {})}
        log('info', f'POST /telemetries: {payload}')
        res = post_req('/telemetries', payload)
        if res['status'] == 'error':
            log('err', f"falha ao cadastrar o módulo: {res.get('data')}")
            return None
        log('ok', f'módulo {mod} cadastrado')
        return res.get('data') or payload
    if cur.get('vehicle') and cur['vehicle'] != plate and not mine:
        log('err', f"módulo {mod} já está no aparelho da placa {cur['vehicle']} (o servidor aceita 1 aparelho por "
                   'módulo): desvincule lá antes ou confira o ID com o usuário')
        return None
    # rastreador de verdade não muda de marca: marca diferente = ID ou telemetria digitados errado.
    # O módulo MIX-<esp> pode (MIX antigo ↔ MIX 2.0 é só a marca)
    if brand and cur.get('brand') and cur['brand'] != brand and not mod.startswith('MIX-'):
        log('err', f"módulo {mod} é {cur.get('brand_label') or cur['brand']}, não da telemetria pedida: "
                   'confira o ID do módulo e a telemetria com o usuário')
        return None
    change = {**({'chip': chip} if chip and cur.get('chip') != chip else {}),
              **({'brand': brand} if brand and cur.get('brand') != brand else {})}
    if change:
        log('info', f"PATCH /telemetries/{mod}: " + ', '.join(f'{k} {cur.get(k)!r} → {v!r}' for k, v in change.items()))
        res = post_req(f'/telemetries/{mod}', change, type='PATCH')
        if res['status'] == 'error':
            log('err', f"falha ao gravar o módulo: {res.get('data')}")
            return None
    log('ok', f"módulo {mod} já cadastrado (chip {chip or cur.get('chip') or '-'})")
    return cur


def moduleKind(mod):
    m = str(mod or '')
    return ('Suntech' if m.startswith('17') else 'Entrack' if m.startswith('69') else
            'MiX' if m.startswith('MIX-') else 'módulo')


def deviceSummary(dev, companies):
    plate = dev.get('plate')
    where = f"placa {plate} ({dev.get('telemetry_brand_label') or 'sem telemetria'}, instalado " \
            f"{str(dev.get('installation_date') or '-')[:10]})" if plate else 'sem placa (estoque)'
    mod = dev.get('telemetry')
    kind = moduleKind(mod)
    return (f"{dev.get('id')} — empresa {companyLabel(dev.get('company'), companies)}, série {dev.get('series_num')}, "
            f"sensor {dev.get('sensor_id')}, {where}, módulo {(mod + ('' if kind == 'módulo' else f' ({kind})')) if mod else '-'}")


def findRegistered(esp=None, sensor=None, module=None, plate=None, series=None, devices=None):
    """onde cada identificador já está no servidor → lista de (tipo, valor, device)."""
    devices = devices if devices is not None else (get_req('/devices').get('data') or [])
    hits = []
    for d in devices:
        if esp and d.get('id') == esp:
            hits.append(('aparelho', esp, d))
        if sensor and d.get('sensor_id') == sensor and d.get('id') != esp:
            hits.append(('sensor', sensor, d))
        if module and d.get('telemetry') == module and d.get('id') != esp:
            hits.append(('módulo', module, d))
        if plate and (d.get('plate') or '').upper() == plate.upper() and d.get('id') != esp:
            hits.append(('placa', plate, d))
        if series and d.get('series_num') == series and d.get('id') != esp:
            hits.append(('série', series, d))
    return hits


def optionsFor(kind, value, dev, args, esp=None):
    """texto das opções para o usuário escolher (o agente apresenta e pergunta)."""
    other = dev.get('id')
    company = f" --company {args.company}" if getattr(args, 'company', None) else ''
    module = optional(getattr(args, 'modulo', None))
    chip = optional(getattr(args, 'chip', None))
    modArgs = (f' --modulo {module}' if module else '') + (f' --chip {chip}' if chip else '')
    if kind == 'aparelho':
        return [f"editar o cadastro existente (muda só o necessário, mantém histórico): "
                f"tools/sighir.py edit {other}{company}{' --desinstalar' if dev.get('plate') else ''}{modArgs}"
                f"{' --sensor usb' if getattr(args, 'sensor_lido', None) and args.sensor_lido != dev.get('sensor_id') else ''}",
                'deixar como está (o cadastro já está certo) — nada a fazer',
                f'apagar e cadastrar de novo (perde o histórico; só se o cadastro estiver errado): '
                f'tools/sighir.py server-delete {other} --yes e depois o register']
    if kind == 'módulo':
        return [f"mover o {moduleKind(value)} {value} para este aparelho: tools/sighir.py edit {other} --modulo none "
                f"--yes (tira do aparelho antigo) e depois repetir este comando",
                f'usar outro módulo (confira o ID na etiqueta do {moduleKind(value)})',
                'cadastrar agora sem módulo (--modulo none) e vincular depois com edit --modulo']
    if kind == 'sensor':
        return [f'o sensor foi trocado de aparelho: corrija o antigo (tools/sighir.py edit {other} --sensor <ETL do antigo>) '
                'e repita',
                'conferir o sensor lido (ETL2608402025435219/ETL3550904305917103 são de build de debug: não cadastrar)',
                'seguir mesmo assim (--forcar)']
    if kind == 'placa':
        return [f"trocar o aparelho dessa placa: tools/sighir.py edit {other} --desinstalar --yes e depois este install",
                'conferir a placa digitada',
                'gravar mesmo assim nos dois aparelhos (--forcar) — não recomendado']
    if kind == 'série':
        return ['usar o próximo número livre (--series auto)', f'corrigir a série do aparelho {other} com edit --series']
    return []


def reportConflicts(hits, companies, args, esp=None):
    """mostra ao usuário onde cada coisa já está e as opções; devolve True se houver conflito."""
    if not hits:
        return False
    labels = {'aparelho': 'Este etilômetro', 'sensor': 'O sensor', 'módulo': 'O módulo', 'placa': 'A placa',
              'série': 'O número de série'}
    for kind, value, dev in hits:
        what = f"{labels[kind]} {value}" if kind != 'módulo' else f"O {moduleKind(value)} {value}"
        where = 'JÁ ESTÁ CADASTRADO' if kind == 'aparelho' else f"já pertence ao aparelho {dev.get('id')}"
        log('warn', f"{what} {where}: {deviceSummary(dev, companies)}")
        for i, opt in enumerate(optionsFor(kind, value, dev, args, esp), 1):
            log('info', f'   opção {i}: {opt}')
    log('err', 'nada foi gravado — pergunte ao usuário qual opção ele quer')
    return True


def cmdOnde(args):
    """onde um identificador já está cadastrado (MIC, sensor ETL, módulo, placa ou nº de série)."""
    value = args.valor.strip()
    companies = get_req('/companies').get('data') or []
    devices = get_req('/devices').get('data') or []
    up = value.upper()
    hits = findRegistered(esp=value, sensor=value, module=value, plate=value,
                          series=value.zfill(5) if value.isdigit() else None, devices=devices)
    seen = set()
    for kind, _, dev in hits:
        if (kind, dev.get('id')) in seen:
            continue
        seen.add((kind, dev.get('id')))
        log('ok', f"{kind}: {deviceSummary(dev, companies)}")
    mod = get_req(f'/telemetries/{value}/') if not up.startswith(('MIC', 'ETL')) else {'status': 'error'}
    row = mod.get('data') if mod.get('status') != 'error' else None
    if row and not any(k == 'módulo' for k, _, _ in hits):
        log('ok', f"módulo {value}: cadastrado em /telemetries, chip {row.get('chip') or '-'}, "
                  f"sem aparelho vinculado (livre)")
    if not hits and not row:
        log('info', f'{value!r} não está cadastrado em lugar nenhum (aparelho, sensor, módulo, placa, série)')
        return 1
    return 0


# A BANCADA NÃO TESTA A TELEMETRIA: O FECHAMENTO DO CADASTRO (register / relatorio) LEMBRA O QUE FICA COM A INSTALAÇÃO
FIELD_NOTE = ('cadastro conferido no servidor. Os testes da bancada validam o etilômetro e a comunicação serial; o '
              'funcionamento com a telemetria é com a instalação: ligar no módulo, pedir um teste pela telemetria, '
              'bloquear e desbloquear pelo módulo e conferir se o relé comuta (corta e devolve a ignição)')


def cmdRegister(args):
    if not args.company:
        _, companies = resolveCompany('')
        log('info', 'empresas disponíveis (use --company <value>):')
        for c in companies:
            print(f"  {c.get('value')!r:14} -> {c.get('label')}")
        return 1

    if not args.tecnico:
        log('err', 'informe --tecnico "<nome>": quem fez o ensaio, vai no relatório do default_settings')
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
    sensor = optional(getattr(args, 'sensor', None))
    if sensor:
        sensorId = f"ETL{random.randint(10**15, 10**16 - 1)}" if sensor.lower() == 'random' else sensor.upper()
        if not sensorId.startswith('ETL'):
            log('err', f'sensor inválido: {sensorId!r} (esperado ETL…)')
            core.device.disconnect()
            return 1
    else:
        sensorId = core.readSensorId()
        if not sensorId:
            log('err', 'não foi possível ler sensor_id')
            core.device.disconnect()
            return 1

    series = nextSeries() if (not args.series or args.series == 'auto') else args.series.zfill(5)

    module = optional(args.modulo)
    chip = optional(args.chip)
    config = core.readConfig()
    build = config.get('company')

    core.device.disconnect()

    # já existe? (aparelho, sensor em outro aparelho, módulo em outro aparelho, série) → opções, não grava
    args.sensor_lido = sensorId
    companies = get_req('/companies').get('data') or []
    hits = findRegistered(esp=espId, sensor=sensorId, module=module,
                          series=None if (not args.series or args.series == 'auto') else series)
    if args.forcar:
        hits = [h for h in hits if h[0] not in ('sensor',)]
    if reportConflicts(hits, companies, args, espId):
        return 4
    if module:
        res = get_req(f'/telemetries/{module}/')
        if res['status'] != 'error' and res.get('data'):
            log('info', f'{moduleKind(module)} {module} já existe em /telemetries, livre: será vinculado a este aparelho')

    # módulo primeiro: o device aponta para ele (Device.telemetry -> /telemetries)
    if module and not ensureModule(module, chip):
        return 1
    if chip and not module:
        log('warn', f'chip {chip} ignorado: sem módulo não há onde gravar (o chip mora em /telemetries)')

    payload = {
        'company': companyId,
        'series_num': series,
        'id': espId,
        'sensor_id': sensorId,
        'need_update': True,
    }
    if module:
        payload['telemetry'] = module

    report = Report(espId, args.tecnico, args.obs).update()
    log('info', f'POST /devices: {payload}')
    payload['default_settings'] = defaultSettings(config, report)
    res = post_req('/devices', payload)
    if res['status'] == 'error':
        log('err', f"erro ao registrar: {res.get('data')}")
        return 1

    log('ok', f"DEVICE {espId} REGISTRADO (série {series}, empresa {args.company}"
              f"{', módulo ' + module if module else ''}).")
    record(espId, 'cadastro', ok=True, detalhe=f"Cadastrado: empresa {args.company}, série {series}"
                                               f"{', módulo ' + module if module else ', sem módulo'}{', chip ' + chip if chip else ''}")
    log('warn', f'lembrete: cole a etiqueta {series} no aparelho.')
    log('warn', FIELD_NOTE)

    if build != args.company:
        log('warn', f"o aparelho roda a build {build!r}, não a da {args.company}: rode flash agora para gravar a build "
                    'da empresa (logo e parâmetros dela; need_update já está ligado)')

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


FLASH_STATE = os.path.join(ROOT, '.sighir', 'flash.json')
PROGRESS_EVERY = 20


def flashState(state, percent=None, started=None, **extra):
    data = {'estado': state, 'porcentagem': None if percent is None else round(percent, 1),
            'inicio': started, 'atualizado': time.time(), **extra}
    try:
        os.makedirs(os.path.dirname(FLASH_STATE), exist_ok=True)
        with open(FLASH_STATE, 'w', encoding='utf-8') as f:
            json.dump(data, f)
    except OSError:
        pass
    return data


def elapsed(seconds):
    seconds = int(seconds)
    return f'{seconds // 60} min {seconds % 60:02d} s' if seconds >= 60 else f'{seconds} s'


def progressLoop(stop, started):
    """a cada 20 s: linha PROGRESSO no log (flash.log) + estado em .sighir/flash.json para o agente mostrar."""
    while not stop.wait(PROGRESS_EVERY):
        pct = max(core.updater.percentage, 0)
        state = 'gravando' if core.updater.percentage >= 0 else 'sincronizando'
        flashState(state, pct, started)
        log('info', f'PROGRESSO DO FLASH: {pct:.0f}% ({state}, {elapsed(time.time() - started)})')
        sys.stdout.flush()


def cmdProgresso(args):
    """estado do flash em andamento: espera até --espera s por uma atualização nova e mostra a porcentagem."""
    def read():
        try:
            return json.load(open(FLASH_STATE, encoding='utf-8'))
        except (OSError, ValueError):
            return None
    first = read()
    if not first:
        log('info', 'nenhum flash registrado neste computador')
        return 1
    if first['estado'] not in ('concluído', 'erro'):
        deadline = time.time() + args.espera
        while time.time() < deadline:
            time.sleep(1)
            now = read()
            if now and now.get('atualizado') != first.get('atualizado'):
                first = now
                break
    st = first
    took = elapsed((st.get('atualizado') or time.time()) - (st.get('inicio') or time.time()))
    pct = st.get('porcentagem')
    stale = time.time() - (st.get('atualizado') or 0) > 3 * PROGRESS_EVERY and st['estado'] not in ('concluído', 'erro')
    log('err' if st['estado'] == 'erro' or stale else 'ok' if st['estado'] == 'concluído' else 'info',
        f"flash {st['estado']}: {'' if pct is None else f'{pct:.0f}% '}({took})"
        + (f" — {st.get('detalhe')}" if st.get('detalhe') else '')
        + (' — SEM ATUALIZAÇÃO há mais de 1 min: confira o flash.log e o cabo' if stale else ''))
    return 0 if not stale and st['estado'] != 'erro' else 2


GENERIC_BUILD = 'admin_sighir'    # O /update SERVE A BUILD DA SIGHIR SEM PROCURAR O APARELHO NEM MEXER NO need_update
BUILD_RE      = re.compile(rb'v(\d+)\.(\d+)\.(\d+)\x00')


def buildVersion(data):
    versions = [tuple(int(g) for g in m.groups()) for m in BUILD_RE.finditer(data or b'')]
    return max(versions, default=None)    # A BUILD TAMBÉM TRAZ A VERSÃO DO ESP-IDF (v5.x.x), SEMPRE MENOR


def companyValue(dev):
    companies = get_req('/companies').get('data') or []
    return next((c.get('value') for c in companies if c.get('id') == dev.get('company')), None)


# A BUILD LOCAL (--arquivo, SEM SERVIDOR) OU A DO SERVIDOR: A DA EMPRESA DO APARELHO CADASTRADO OU A GENÉRICA; None = SEM FIRMWARE
def fetchBuild(args, espId):
    if args.arquivo:
        try:
            with open(args.arquivo, 'rb') as f:
                core.server.firmware.file = {'bytes': f.read(), 'filename': os.path.basename(args.arquivo)}
        except OSError as error:
            log('err', f'não foi possível ler {args.arquivo}: {error}')
            return None
        return f'arquivo {os.path.basename(args.arquivo)}'

    dev     = serverDevice(espId)
    company = companyValue(dev) if dev else 'sighir'

    # /update é one-shot — re-arma para garantir que o servidor sirva o firmware
    if dev and not core.rearmUpdate(espId):
        return None

    if not dev:
        log('info', f'{espId} ainda não está no servidor: build genérica da Sighir. Depois do register, flash de novo '
                    'grava a build da empresa (logo e parâmetros)')

    log('info', f'baixando firmware da {company} (one-shot)...')
    if not core.server.firmware.download(espId if dev else GENERIC_BUILD):
        log('err', 'download falhou')
        return None

    return company


def cmdFlash(args):
    started = time.time()
    flashState('preparando', None, started)
    if not core.robustSync():
        flashState('erro', None, started, detalhe='sem conexão com o aparelho')
        return 1

    espId = core.readEspId()
    if not espId:
        log('err', 'não foi possível ler esp_id')
        core.device.disconnect()
        flashState('erro', None, started, detalhe='esp_id não lido')
        return 1

    fw      = core.readFirmware()
    current = core.readSetting('company')
    company = fetchBuild(args, espId)

    if company is None:
        core.device.disconnect()
        flashState('erro', None, started, detalhe='firmware não obtido (arquivo ou servidor)')
        return 1

    build = buildVersion(core.server.firmware.file['bytes'])
    log('info', f"build {company}: {core.versionStr(build)} | aparelho: {core.versionStr(fw['version'])}, build {current!r}")

    if build and build < core.MIN_FIRMWARE and not args.forcar:
        log('err', f'a build da {company} no servidor é {core.versionStr(build)}, abaixo do mínimo '
                   f'{core.versionStr(core.MIN_FIRMWARE)}: o flash não libera o tester. Publique a build nova '
                   '(Etilometro/auxiliary/FirmwareBuilder) ou use --forcar para gravar mesmo assim')
        core.device.disconnect()
        flashState('erro', None, started, detalhe=f'build do servidor {core.versionStr(build)} abaixo do mínimo')
        record(espId, 'flash', ok=False, antes=core.versionStr(fw['version']), build=core.versionStr(build), empresa=company,
               detalhe='não gravado: build do servidor abaixo do mínimo')
        return 2

    if build == fw['version'] and current == company and not args.forcar and not args.arquivo:
        log('ok', f'já atualizado: {core.versionStr(build)} com a build da {company} — nada a gravar (--forcar grava de novo)')
        core.device.disconnect()
        flashState('concluído', 100, started, detalhe=f'já atualizado em {core.versionStr(build)}')
        record(espId, 'flash', ok=True, antes=core.versionStr(fw['version']), build=core.versionStr(build), empresa=company,
               detalhe='já estava atualizado: nada gravado')
        return 0

    log('info', f'iniciando flash serial (~1 min no firmware novo, ~5 min no antigo; progresso a cada {PROGRESS_EVERY} s)...')
    core.updater.percentage = -1
    stop = threading.Event()
    flashState('sincronizando', 0, started)
    reporter = threading.Thread(target=progressLoop, args=(stop, started), daemon=True)
    reporter.start()
    try:
        core.updater.setup()
        written = core.updater.start()
    except Exception as err:
        stop.set()
        flashState('erro', max(core.updater.percentage, 0), started, detalhe=str(err)[:200])
        raise
    stop.set()

    if written is False:
        log('err', 'o aparelho recusou ou interrompeu a gravação: segue na versão anterior (recover e flash de novo)')
        flashState('erro', max(core.updater.percentage, 0), started, detalhe='gravação recusada ou interrompida')
        record(espId, 'flash', ok=False, antes=core.versionStr(fw['version']), build=core.versionStr(build), empresa=company,
               detalhe='gravação recusada ou interrompida')
        core.device.disconnect()
        return 1

    flashState('verificando', 100, started)
    log('info', f'PROGRESSO DO FLASH: 100% (gravado em {elapsed(time.time() - started)})')
    log('ok', 'flash concluído — verificando...')

    before = core.versionStr(fw['version'])

    if not core.robustSync(retries=10):    # O APARELHO REINICIA SOZINHO NA VERSÃO NOVA (A v6.5 LEVA ~45 S): $ETRS! E RTS SÓ SE NÃO VOLTAR
        core.recover()

    fw     = core.readFirmware()
    landed = build is None or fw['version'] == build
    ok     = fw['status'] == 'ok' and landed
    missed = '' if landed else f' — a build gravada é {core.versionStr(build)}: o aparelho não ficou nela'
    log('ok' if ok else 'err', f"pós-flash: firmware {core.versionStr(fw['version'])} [{fw['status']}]{missed}")
    record(espId, 'flash', ok=ok, antes=before, depois=core.versionStr(fw['version']),
           build=core.versionStr(build), empresa=company, detalhe=f"gravado e conferido no aparelho [{fw['status']}]")
    flashState('concluído' if ok else 'erro', 100, started, detalhe=f"firmware {core.versionStr(fw['version'])} [{fw['status']}]")
    core.device.disconnect()
    return 0 if ok else 2


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
MODULE_TELEMETRY = ('suntech', 'entrack')     # MiX não tem módulo/chip


def cmdInstall(args):
    """Instala o aparelho numa placa. Desde a migração do servidor de 24/09/2026 a instalação é o próprio
    Device: PATCH /devices/<esp> com `plate` (o servidor cria/associa o Vehicle), `vehicle_type` e
    `telemetry` (módulo). Desde 07/10/2026 a telemetria é a marca do módulo (`telemetries/<id>.brand` = CNPJ;
    o device só mostra `telemetry_brand`): Suntech/Entrack = o rastreador; MiX = o módulo `MIX-<esp>`.
    Sem --yes só valida e mostra o que seria gravado. Procedimento: procedimentos/cadastro.md §13."""
    esp = args.esp_id.strip()
    plate = normPlate(args.placa)
    res = get_req(f'/devices/{esp}/')
    dev = res.get('data') if res['status'] != 'error' else None
    if not dev:
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

    module = optional(args.modulo)
    chip = optional(args.chip)
    if module and not args.forcar:
        inUse = [h for h in findRegistered(module=module) if h[2].get('id') != esp]
        if reportConflicts(inUse, companies, args, esp):
            return 2
    if module and args.telemetria not in MODULE_TELEMETRY:
        log('err', f'--modulo só vale para Suntech/Entrack; {args.telemetria} não tem módulo')
        return 1
    linked = dev.get('telemetry')
    if args.telemetria in MODULE_TELEMETRY:
        moduleId = module or (linked if linked and not linked.startswith('MIX-') else None)
        if not moduleId and linked:
            log('err', f'o aparelho hoje está na MiX ({linked}): para {args.telemetria} informe o ID do módulo '
                       '(--modulo) — sem ele a telemetria continuaria MiX no servidor')
            return 1
        if not moduleId:
            log('warn', f'{args.telemetria} sem módulo vinculado: pergunte o ID do módulo (--modulo) — sem ele o '
                        'servidor não associa os logs do rastreador a este aparelho nem guarda a telemetria')
    else:
        moduleId = mixModule(esp)

    # placa já em outro aparelho? (Vehicle.plate é único; 1 aparelho por placa)
    rows = get_req('/etilometers').get('data') or []
    others = [e for e in rows if (e.get('vehicle') or '').strip().upper() == plate.upper() and e.get('esp_id') != esp]
    current = (dev.get('plate') or '').strip()

    data = dict(dev['installation_data']) if isinstance(dev.get('installation_data'), dict) else {}
    if args.observacao:
        data['observation'] = args.observacao
    if args.maleta:
        data['suitcase'] = 1
    payload = {'plate': plate, 'vehicle_type': 1 if args.tipo == 'carro' else 0, 'is_operating': True}
    if current.upper() != plate.upper():        # reinstalar na mesma placa mantém a data original
        payload['installation_date'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
    if moduleId and moduleId != linked:
        payload['telemetry'] = moduleId
    if args.instalador:
        payload['installer'] = args.instalador
    if args.apelido:
        payload['nickname'] = args.apelido
    if data:
        payload['installation_data'] = data

    log('info', f"instalação (PRODUÇÃO) PATCH /devices/{esp}: {payload}  [telemetria {tel.get('label')} = marca "
                f"do módulo {moduleId or '-'}{', chip ' + chip if chip else ''}]")
    if moduleId:
        res = get_req(f'/telemetries/{moduleId}/')
        modRow = res.get('data') if res['status'] != 'error' else None
        if not modRow:
            log('info', f"módulo {moduleId}: será criado em /telemetries com a marca {tel.get('label')}")
        elif modRow.get('brand') != tel['id']:
            log('info', f"módulo {moduleId}: marca {modRow.get('brand_label') or modRow.get('brand') or '-'} → "
                        f"{tel.get('label')}")
    blocked = False
    for e in others:
        other = (get_req(f"/devices/{e.get('esp_id')}/").get('data') or {'id': e.get('esp_id'), 'plate': plate})
        reportConflicts([('placa', plate, other)], companies, args, esp)
        blocked = True
    if current and current.upper() != plate.upper():
        log('warn', f'Este aparelho já está instalado: {deviceSummary(dev, companies)}')
        log('info', f'   opção 1: mudou de veículo no mesmo cliente → repetir com --forcar (move para {plate})')
        log('info', f'   opção 2: mudou de cliente → tools/sighir.py edit {esp} --company <nova> --desinstalar --yes '
                    'e depois este install')
        log('info', '   opção 3: conferir o MIC digitado')
        blocked = True
    elif current:
        log('info', f'o aparelho já está na placa {current}: os campos acima serão atualizados')
    if blocked and not args.forcar:
        log('err', 'nada foi gravado — pergunte ao usuário qual opção ele quer')
        return 2
    if not args.yes:
        log('warn', 'nada foi gravado. Confirme os dados com o usuário e rode de novo com --yes')
        return 3

    # o módulo que já é deste aparelho pode estar na placa antiga (troca com --forcar): não barra por placa
    if moduleId and not ensureModule(moduleId, chip if module else None, plate, brand=tel['id'],
                                     mine=moduleId == linked):
        return 1
    res = post_req(f'/devices/{esp}', payload, type='PATCH')
    if res['status'] == 'error':
        log('err', f"servidor recusou: {res.get('data')}")
        return 1

    after = get_req(f'/devices/{esp}/').get('data') or {}
    checks = {'placa': (after.get('plate') or '').upper() == plate.upper()}
    if moduleId:
        checks['módulo'] = after.get('telemetry') == moduleId
        checks['telemetria'] = after.get('telemetry_brand') == tel['id']
    inst = [e for e in (get_req('/etilometers').get('data') or [])
            if e.get('esp_id') == esp and (e.get('vehicle') or '').upper() == plate.upper()]
    checks['etilometers/'] = bool(inst)
    bad = [k for k, ok in checks.items() if not ok]
    log('ok' if not bad else 'err', f"instalação {plate} ↔ {esp} ({tel.get('label')}): "
        + ('gravada e conferida' if not bad else f"NÃO conferiu {', '.join(bad)} — devolveu {after}"))
    return 0 if not bad else 1


# a telemetria (marca) fica no módulo desde 07/10/2026: tirar da placa não mexe nela; o install seguinte
# troca de módulo/marca se o cliente novo usar outra telemetria
UNINSTALL = {'plate': None, 'installation_date': None, 'installer': '', 'nickname': '', 'installation_data': {}}


def companyLabel(cid, companies):
    return next((c.get('label') for c in companies if c.get('id') == cid), cid) if cid else None


def cmdEdit(args):
    """Edita um aparelho JÁ cadastrado, mudando só o que foi pedido (ex.: voltou da Predileto, vai para a
    Logika com outro módulo). Mostra antes → depois; só grava com --yes e confere. Para pôr numa placa nova
    depois, use `install`."""
    esp = args.esp_id.strip()
    res = get_req(f'/devices/{esp}/')
    dev = res.get('data') if res['status'] != 'error' else None
    if not dev:
        log('err', f'device {esp} não existe no servidor — para aparelho novo use register')
        return 1
    companies = get_req('/companies').get('data') or []
    mod = dev.get('telemetry')
    modRow = (get_req(f'/telemetries/{mod}/').get('data') or {}) if mod else {}
    log('info', f"----- {esp} hoje -----")
    log('info', f"empresa {companyLabel(dev.get('company'), companies)} | série {dev.get('series_num')} | "
                f"sensor {dev.get('sensor_id')} | módulo {mod or '-'} (chip {modRow.get('chip') or '-'})")
    log('info', f"placa {dev.get('plate') or '-'} | telemetria {dev.get('telemetry_brand_label') or '-'} | "
                f"instalado {str(dev.get('installation_date') or '-')[:10]} por {dev.get('installer') or '-'}")

    change = {}
    if args.company:
        cid, options = resolveCompany(args.company)
        if not cid:
            log('err', f'empresa {args.company!r} não encontrada. Valores: ' +
                ', '.join(repr(c.get('value')) for c in options))
            return 1
        if cid != dev.get('company'):
            change['company'] = cid
    if args.series:
        series = args.series.zfill(5)
        if series != dev.get('series_num'):
            dup = [d['id'] for d in (get_req('/devices').get('data') or [])
                   if d.get('series_num') == series and d.get('id') != esp]
            if dup:
                log('err', f'a série {series} já é do aparelho {dup[0]}')
                return 1
            change['series_num'] = series
    if args.sensor:
        sensor = args.sensor.strip()
        if sensor.lower() == 'usb':
            if not core.robustSync():
                return 1
            live, sensor = core.readEspId(), core.readSensorId()
            core.device.disconnect()
            if live != esp:
                log('err', f'o aparelho na USB é {live}, não {esp}: conecte o aparelho certo')
                return 1
        if not sensor or not sensor.upper().startswith('ETL'):
            log('err', f'sensor inválido: {sensor!r} (esperado ETL…)')
            return 1
        if sensor != dev.get('sensor_id'):
            change['sensor_id'] = sensor
    newModule, chip = None, optional(args.chip)
    if args.modulo is not None:
        newModule = optional(args.modulo)
        if newModule != mod:
            change['telemetry'] = newModule          # None = desvincula o módulo
    if args.desinstalar:
        if not dev.get('plate'):
            log('warn', 'o aparelho não está em placa nenhuma: --desinstalar não muda nada')
        else:
            change.update({k: v for k, v in UNINSTALL.items() if dev.get(k) != v})
    if args.rearmar and not dev.get('need_update'):
        change['need_update'] = True
    chipModule = change.get('telemetry', mod)
    chipChange = bool(chip and chipModule and (chipModule != mod or chip != modRow.get('chip')))
    if chip and not chipModule:
        log('err', 'chip sem módulo: informe --modulo (o chip mora no módulo, em /telemetries)')
        return 1

    if 'company' in change and dev.get('plate') and not args.desinstalar:
        log('err', f"o aparelho ainda está na placa {dev['plate']} da empresa antiga: use --desinstalar "
                   '(ou --forcar se a placa também mudou de dono)')
        if not args.forcar:
            return 2

    if not change and not chipChange:
        log('ok', 'nada a mudar: o cadastro já está assim')
        return 0
    log('info', f'----- alterações (PRODUÇÃO, PATCH /devices/{esp}) -----')
    for k, v in change.items():
        before = dev.get(k)
        if k == 'company':
            before, v = companyLabel(before, companies), companyLabel(v, companies)
        log('info', f'{k:18} {before!r} → {v!r}')
    if chipChange:
        log('info', f"{'chip do módulo':18} {modRow.get('chip') if chipModule == mod else None!r} → {chip!r}  "
                    f'(/telemetries/{chipModule})')
    if args.desinstalar and dev.get('plate'):
        log('warn', f"sai da placa {dev['plate']}: abra o Helper (anomalias {dev['plate']}) se houver alerta aberto dela")
    if not args.yes:
        log('warn', 'nada foi gravado. Confirme com o usuário e rode de novo com --yes')
        return 3

    if chipModule and (chipModule != mod or chipChange):
        if not ensureModule(chipModule, chip, None if args.desinstalar else dev.get('plate'), mine=chipModule == mod):
            return 1
    if change:
        res = post_req(f'/devices/{esp}', change, type='PATCH')
        if res['status'] == 'error':
            log('err', f"servidor recusou: {res.get('data')}")
            return 1
    after = get_req(f'/devices/{esp}/').get('data') or {}
    bad = [k for k, v in change.items() if (after.get(k) or None) != (v or None)]
    if chipChange:
        got = (get_req(f'/telemetries/{chipModule}/').get('data') or {}).get('chip')
        if got != chip:
            bad.append('chip')
    log('ok' if not bad else 'err', f'{esp}: ' + ('alterado e conferido' if not bad else
                                                   f"NÃO conferiu {', '.join(bad)} — devolveu {after}"))
    if not bad and args.desinstalar:
        log('info', 'para instalar na placa nova: tools/sighir.py install <esp> --placa ... --telemetria ...')
    return 0 if not bad else 1


def cmdServerDelete(args):
    """DELETE de verdade no servidor. `deleted=True` NÃO apaga nada (ver §13)."""
    from utils.api import delete_req

    res = get_req(f'/devices/{args.esp_id}')

    if res['status'] == 'error' or not res.get('data'):
        log('err', f'device {args.esp_id} não encontrado no servidor')
        return 1

    data = res['data']
    log('warn', 'REGISTRO A DELETAR (produção, hard delete). O módulo (/telemetries) e a placa (Vehicle) ficam; '
                'os logs apontam para o aparelho (log.device) e podem ir junto — confirme com o usuário:')

    for key in ('id', 'series_num', 'company', 'sensor_id', 'plate', 'telemetry', 'telemetry_brand_label'):
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


AUTO_STEPS    = ['serial', 'temperatura', 'sensor', 'calibracao', 'pressao']
MANUAL_STEPS  = ['autodiagnostico', 'sopro', 'sem-alcool', 'com-alcool']    # O OPERADOR NA TELA, SOPRANDO
DIAG_STEPS    = ('autodiagnostico', 'sopro')                               # LEEM AS LINHAS JSON DO DIAGNÓSTICO (core.DIAG_FIRMWARE)


def cmdQuality(args):
    from tools.quality import Quality

    names = args.etapas or AUTO_STEPS
    wrong = [name for name in names if name not in AUTO_STEPS + MANUAL_STEPS]
    if wrong:
        log('err', f"etapa desconhecida: {', '.join(wrong)} (use {', '.join(AUTO_STEPS + MANUAL_STEPS)})")
        return 1

    if not core.robustSync():
        return 1

    fw = core.readFirmware()
    if fw['status'] != 'ok':
        log('err', f"qualidade BLOQUEADA: firmware {core.versionStr(fw['version'])} [{fw['status']}], mínimo "
                   f"{core.versionStr(core.MIN_FIRMWARE)}. Atualize (flash) antes.")
        core.device.disconnect()
        return 2

    if any(name in DIAG_STEPS for name in names) and fw['version'] < core.DIAG_FIRMWARE:
        log('err', f"{'/'.join(DIAG_STEPS)} exigem o firmware {core.versionStr(core.DIAG_FIRMWARE)} (protocolo de sopro na tela); "
                   f"este está na {core.versionStr(fw['version'])}: atualize (flash) antes; se o flash disser 'já atualizado', "
                   f"a {core.versionStr(core.DIAG_FIRMWARE)} ainda não foi publicada no servidor (Etilometro/auxiliary/FirmwareBuilder)")
        core.device.disconnect()
        return 2

    quality = Quality(fw, core.readEspId(), core.readSensorId())

    if not core.isNativeId(quality.espId):
        log('err', f'esp_id {quality.espId!r} não é nativo (MIC…): rode erase antes dos testes — o relatório do cadastro é guardado pelo MIC')
        core.device.disconnect()
        return 2

    mode    = {str(code): name for name, code in core.TELEMETRIES.items()}.get(str(core.readSetting('telemetry')))
    record(quality.espId, 'aparelho', firmware=core.versionStr(fw['version']), status=fw['status'], minimo=core.versionStr(core.MIN_FIRMWARE),
           sensor_id=quality.sensorId, debug=quality.debug(), telemetria=f'{mode} (configurada no aparelho)' if mode else None)
    steps   = {
        'serial': quality.serial,
        'temperatura': quality.temperature,
        'sensor': quality.sensor,
        'calibracao': quality.calibration,
        'pressao': quality.pressure,
        'autodiagnostico': quality.selfDiagnostic,
        'sopro': lambda: quality.blows(args.blowprob),
        'sem-alcool': lambda: quality.alcohol(False, args.vezes or 1),
        'com-alcool': lambda: quality.alcohol(True, args.vezes or 1)
    }

    for name in names:
        steps[name]()

    quality.print()
    core.device.disconnect()
    return 1 if quality.failed() else 0


# default_settings DO DEVICE = CONFIGURAÇÃO ATUAL DO APARELHO + RELATÓRIO DE ENSAIO; O SERVIDOR GERA O PDF COM ISSO
def defaultSettings(config, report):
    verdict = report['veredito']
    log('ok' if verdict['codigo'] == 'apto' else 'warn',
        f"default_settings: {len(config)} configurações + relatório {report['numero']} — {verdict['titulo']} "
        f"({verdict['aprovados']}/{verdict['total']} ensaios) — {verdict['texto']}")
    return json.dumps({'settings': config, 'report': report}, ensure_ascii=False)


def cmdReport(args):
    if not core.robustSync():
        return 1

    esp, config = core.readEspId(), core.readConfig()
    core.device.disconnect()

    if not serverDevice(esp):
        log('err', f'{esp} não está cadastrado: o relatório vai junto no register --tecnico')
        return 1

    payload = {'default_settings': defaultSettings(config, Report(esp, args.tecnico, args.obs).update())}

    if not args.yes:
        log('warn', f'nada foi gravado. Confirme com o usuário e rode de novo com --yes (PATCH /devices/{esp} default_settings)')
        return 3

    res = post_req(f'/devices/{esp}', payload, type='PATCH')
    if res['status'] == 'error':
        log('err', f"servidor recusou: {res.get('data')}")
        return 1

    saved = (serverDevice(esp) or {}).get('default_settings')
    ok    = saved == payload['default_settings']
    log('ok' if ok else 'err', f'{esp}: default_settings ' + ('gravado e conferido' if ok else f'NÃO conferiu — devolveu {str(saved)[:200]}'))

    if ok:
        log('warn', FIELD_NOTE)

    return 0 if ok else 1


LEGACY_SETTINGS = ('comm_type', 'operation_mode', 'maleta')    # CHAVES ANTIGAS NO CADASTRO DA EMPRESA QUE O FIRMWARE NÃO USA (FirmwareBuilder)
REMOTE_MAX      = 240                                          # O FIRMWARE DESCARTA COMANDO SERIAL ACIMA DE 256 CARACTERES


def companySettings(value):
    company = next((c for c in get_req('/companies').get('data') or [] if c.get('value') == value and c.get('type') == 'transportation'), None)

    if company is None:
        return None

    data = company.get('data') or {}
    data = json.loads(data) if isinstance(data, str) else data
    return {key: v for key, v in (data.get('settings') or {}).items() if key in core.DEVICE_SETTINGS and key not in LEGACY_SETTINGS}


def settingText(value):
    return ('true' if value else 'false') if isinstance(value, bool) else str(value)


# CONFIGURAÇÃO DA EMPRESA NO APARELHO: PADRÃO DO CADASTRO DA EMPRESA + O QUE O TÉCNICO PEDIR; AS MUDANÇAS DELE VÃO TAMBÉM NO
# "remote", QUE O FIRMWARE REAPLICA POR CIMA DOS PARÂMETROS DA EMPRESA QUANDO A BUILD DELA ENTRA DEPOIS DO CADASTRO
def cmdConfigure(args):
    standard = companySettings(args.company)

    if standard is None:
        log('err', f'empresa {args.company!r} não encontrada em /companies (use o value, ex.: logika)')
        return 1

    extra = {}

    for pair in args.set or []:
        if '=' not in pair:
            log('err', f'formato inválido: {pair!r} (use chave=valor)')
            return 1

        key, value = (part.strip() for part in pair.split('=', 1))
        extra[key] = value if key in core.TEXT_SETTINGS else core.typedValue(value)

    unknown = [key for key in extra if key not in core.DEVICE_SETTINGS]

    if unknown:
        log('err', f"fora da configuração do aparelho: {', '.join(unknown)} (aceitas: {', '.join(core.DEVICE_SETTINGS)}; o resto é settings --set)")
        return 1

    if not core.robustSync():
        return 1

    esp, current = core.readEspId(), core.readConfig()
    target       = {**standard, **extra}
    change       = {key: value for key, value in target.items() if current.get(key) != value}
    overrides    = {key: value for key, value in extra.items() if standard.get(key) != value}

    log('info', f'----- configuração {args.company}: aparelho → padrão da empresa{" + pedido" if extra else ""} -----')

    for key in core.DEVICE_SETTINGS:
        if key in target:
            mark = '*' if key in change else ' '
            log('info', f"{mark} {key:16} {current.get(key)!r:>14} → {target[key]!r:<14}" + (' (pedido)' if key in overrides else ''))

    if not change:
        log('ok', 'o aparelho já está na configuração da empresa')
        record(esp, 'configuracao', empresa=args.company, alteradas={}, configuracao=current)
        core.device.disconnect()
        return 0

    if not args.yes:
        log('warn', f'{len(change)} mudança(s) marcadas com *: nada foi gravado. Pergunte ao usuário se quer mudar mais alguma e rode com --yes')
        core.device.disconnect()
        return 3

    remote = json.dumps(overrides, separators=(',', ':'))
    writes = [*change.items(), *([('remote', remote)] if overrides and len(remote) <= REMOTE_MAX else [])]

    if overrides and len(remote) > REMOTE_MAX:
        log('warn', 'pedidos demais para o "remote": um flash da build da empresa depois do cadastro pode voltar esses valores ao padrão')

    if not all(core.writeSetting(key, settingText(value)) for key, value in writes):
        core.device.disconnect()
        return 1

    core.restart()    # TELEMETRIA, CÂMERA, ADIAMENTOS E blowProb SÓ SÃO LIDOS NO BOOT
    after = core.readConfig()
    core.device.disconnect()
    bad   = [key for key, value in target.items() if after.get(key) != value]
    record(esp, 'configuracao', empresa=args.company, alteradas={key: {'antes': current.get(key), 'depois': after.get(key)} for key in change},
           configuracao=after)
    log('ok' if not bad else 'err', f'{esp}: configuração da {args.company} ' + ('gravada e conferida' if not bad else f"NÃO conferiu {', '.join(bad)}"))
    return 0 if not bad else 1


def cmdMonitor(args):
    from tools.quality import readSeries

    if not core.robustSync():
        return 1

    rows = readSeries(args.segundos, args.intervalo)
    core.device.disconnect()

    if not rows:
        log('err', '/get-data sem resposta (o comando existe a partir da v6.5)')
        return 1

    keys = [key for key in rows[0] if key != 'filtered_analog']
    print('  '.join(f'{key:>11}' for key in keys))

    for row in rows:
        print('  '.join(f'{row.get(key, "-"):>11}' for key in keys))

    log('info', '----- RESUMO (mín / média / máx) -----')

    for key in keys[1:]:
        values = [row[key] for row in rows if isinstance(row.get(key), (int, float))]
        log('info', f'{key:16} {min(values):>11} {sum(values)/len(values):>11.3f} {max(values):>11}' if values else f'{key:16} -')

    return 0


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

    edt = sub.add_parser('edit', help='edita aparelho já cadastrado (só o que mudar) — exige --yes')
    edt.add_argument('esp_id', help='MIC... já cadastrado')
    edt.add_argument('--company', help='value da nova empresa (ex: logika)')
    edt.add_argument('--modulo', '--suntech', dest='modulo', help='novo ID do módulo Suntech/Entrack, ou "none" para desvincular')
    edt.add_argument('--chip', help='chip do módulo (grava em /telemetries)')
    edt.add_argument('--sensor', help='novo sensor ETL… ou "usb" (lê do aparelho conectado)')
    edt.add_argument('--series', help='novo número de série')
    edt.add_argument('--desinstalar', action='store_true', help='tira da placa (volta para o estoque)')
    edt.add_argument('--rearmar', action='store_true', help='need_update=true (próxima atualização)')
    edt.add_argument('--forcar', action='store_true', help='troca a empresa mantendo a placa')
    edt.add_argument('--yes', action='store_true', help='grava de verdade (depois de confirmar com o usuário)')
    edt.set_defaults(func=cmdEdit)

    ond = sub.add_parser('onde', help='onde um MIC/ETL/módulo/placa/série já está cadastrado')
    ond.add_argument('valor')
    ond.set_defaults(func=cmdOnde)

    prg = sub.add_parser('progresso', help='porcentagem do flash em andamento (espera até 20 s)')
    prg.add_argument('--espera', type=int, default=PROGRESS_EVERY)
    prg.set_defaults(func=cmdProgresso)

    sdel = sub.add_parser('server-delete')
    sdel.add_argument('esp_id')
    sdel.add_argument('--yes', action='store_true', help='confirma o hard delete em produção')
    sdel.set_defaults(func=cmdServerDelete)

    ins = sub.add_parser('install', help='instala o aparelho numa placa (PATCH /devices) — exige --yes')
    ins.add_argument('esp_id', help='MIC... já cadastrado (register)')
    ins.add_argument('--placa', required=True, help='placa do veículo (o servidor cria/associa o Vehicle)')
    ins.add_argument('--telemetria', required=True, choices=list(INSTALL_TELEMETRY),
                     help='mix2 = MIX 2.0 (maioria da frota MiX); mix = MIX antigo')
    ins.add_argument('--modulo', help='ID do módulo Suntech/Entrack (se ainda não vinculado no register)')
    ins.add_argument('--chip', help='chip do módulo (grava em /telemetries)')
    ins.add_argument('--tipo', choices=['caminhao', 'carro'], default='caminhao')
    ins.add_argument('--maleta', action='store_true', help='maleta de demonstração (installation_data.suitcase=1)')
    ins.add_argument('--observacao', help='observação da instalação (installation_data.observation)')
    ins.add_argument('--instalador', help='nome de quem instalou')
    ins.add_argument('--apelido', help='nickname opcional')
    ins.add_argument('--forcar', '--duplicar', dest='forcar', action='store_true',
                     help='grava mesmo com a placa em outro aparelho ou o aparelho em outra placa (troca)')
    ins.add_argument('--yes', action='store_true', help='grava de verdade (depois de confirmar com o usuário)')
    ins.set_defaults(func=cmdInstall)

    reg = sub.add_parser('register')
    reg.add_argument('--company', help='value da empresa (ex: logika). Sem isto, lista as opções.')
    reg.add_argument('--series', default='auto', help='número de série ou "auto"')
    reg.add_argument('--modulo', '--suntech', dest='modulo', default='none',
                     help='ID do módulo Suntech/Entrack (/telemetries) ou "none" (MiX)')
    reg.add_argument('--chip', default='N/A', help='chip do módulo (grava em /telemetries) ou "N/A"')
    reg.add_argument('--sensor', help='ID do sensor ETL… manual ou "random" (default: lê da USB)')
    reg.add_argument('--forcar', action='store_true', help='cadastra mesmo com o sensor já em outro aparelho')
    reg.add_argument('--tecnico', help='nome de quem fez o ensaio (vai no relatório do default_settings)')
    reg.add_argument('--obs', help='observações do técnico para o relatório')
    reg.set_defaults(func=cmdRegister)

    tst = sub.add_parser('test')
    tst.add_argument('name', nargs='?', help='nome do teste (alcohol, alcohol-blow, blow, temp, sensor). Sem isto, lista.')
    tst.add_argument('--telemetry', default='mix', choices=['mix', 'suntech'], help='variante de telemetria (default: mix)')
    tst.set_defaults(func=cmdTest)

    qua = sub.add_parser('qualidade', help='testes de qualidade (sem etapas: serial, temperatura, sensor, pressao)')
    qua.add_argument('etapas', nargs='*', help=f"{', '.join(AUTO_STEPS)} (automáticas) e {', '.join(MANUAL_STEPS)} (operador soprando)")
    qua.add_argument('--vezes', type=int, help='repetições de sem-alcool/com-alcool (padrão 1)')
    qua.add_argument('--blowprob', type=float, help='sopro: tolerância do protocolo (0.3 a 1.5 s), gravada antes pelo CF:blowProb$X!')

    rel = sub.add_parser('relatorio', help='reenvia o default_settings (configuração + relatório de ensaio) de aparelho cadastrado')
    rel.add_argument('--tecnico', required=True, help='nome de quem fez o ensaio')
    rel.add_argument('--obs', help='observações do técnico')
    rel.add_argument('--yes', action='store_true', help='grava de verdade (PATCH /devices default_settings)')
    rel.set_defaults(func=cmdReport)

    cfg = sub.add_parser('configurar', help='aplica a configuração padrão da empresa (+ --set) no aparelho; sem --yes só mostra')
    cfg.add_argument('--company', required=True, help='value da empresa (ex: logika)')
    cfg.add_argument('--set', action='append', metavar='CHAVE=VALOR', help='mudança pedida pelo técnico (repetível)')
    cfg.add_argument('--yes', action='store_true', help='grava, reinicia e confere')
    cfg.set_defaults(func=cmdConfigure)
    qua.set_defaults(func=cmdQuality)

    mon = sub.add_parser('monitor', help='leituras ao vivo do /get-data (temperatura, umidade, analog, pressão, chave)')
    mon.add_argument('--segundos', type=float, default=10)
    mon.add_argument('--intervalo', type=float, default=0.5)
    mon.set_defaults(func=cmdMonitor)

    fl = sub.add_parser('flash', help='re-arma + baixa + flasha (aparelho novo: build genérica da Sighir)')
    fl.add_argument('--forcar', action='store_true', help='grava mesmo já atualizado ou com a build do servidor abaixo do mínimo')
    fl.add_argument('--arquivo', help='grava este .bin local (ex.: a build do Config/index.py compile) sem tocar no servidor')
    fl.set_defaults(func=cmdFlash)
    return p


def main():
    args = build().parse_args()
    sys.exit(args.func(args))


if __name__ == '__main__':
    main()
