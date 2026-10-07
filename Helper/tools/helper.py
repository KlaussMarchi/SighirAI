#!/usr/bin/env python3
"""
Sighir Helper AI — CLI de suporte técnico.

    python tools/helper.py init                      ambiente, servidor e base de conhecimento
    python tools/helper.py veiculo PLACA [--dias 7]  raio-x do veículo: cadastro, sensor, firmware,
                                                     módulo, eventos decodificados, anomalias, chamados
    python tools/helper.py logs PLACA [--dias 3] [--limite 80] [--evento ETEV02]
    python tools/helper.py evento '$ETEV35!'         o que um evento significa (e de onde vem)
    python tools/helper.py device MIC...             hardware + instalação(ões) + módulo
    python tools/helper.py anomalias [PLACA]         alertas abertos do Scanner
    python tools/helper.py lista [--empresa X] [--telemetria mix]
    python tools/helper.py busca termo [termo...]    busca na base docs/ (atalho do kb.py)
    python tools/helper.py chamado --placa X --problema "..." ...   gera o chamado no formato do Notion
    python tools/helper.py patch devices MIC... need_update=true [--sim]   (escrita em produção)

Leitura é livre. Escrita (patch) mostra antes/depois e só executa com --sim, depois de o usuário confirmar.
"""

import os
import re
import sys
import json
import argparse
import subprocess
import unicodedata
from datetime import datetime, timedelta, timezone

TOOLS = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)

import _venv  # noqa: E402
_venv.ensure(ROOT)

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

BRT = timezone(timedelta(hours=-3))

# código → (rótulo do painel, explicação curta). Fonte: docs/firmware_reference.md §2 + PPTC 0001-01.
EVENTS = {
    '$ETEV01': ('Veículo Desbloqueado', 'liberado (teste sem álcool, contrassenha, adiamento, manobrista, remoto ou 5 reinícios)'),
    '$ETEV02': ('Veículo Bloqueado', 'bloqueado (álcool, sem sopro em viagem, fim da manobra, MIX2 70 s, remoto)'),
    '$ETEV03': ('Veículo em Movimento', 'comando do rastreador (MIX 2.0): viagem começou (caminhão)'),
    '$ETEV04': ('Veículo Desligado', 'comando do rastreador: ignição desligada'),
    '$ETEV05': ('Sopro Realizado', 'sopro válido; começou a análise (~23 s) — não é resultado'),
    '$ETEV06': ('Falha de Comunicação', 'teste de telemetria do menu: rastreador não respondeu em 15 s'),
    '$ETEV07': ('Parâmetros Atualizados', 'configuração remota aplicada (Wi-Fi)'),
    '$ETEV08': ('Dispositivo Inicializado', 'boot do aparelho (1 a cada ~3 dias é normal; vários por dia = alimentação)'),
    '$ETEV09': ('Sensor Inicializado', 'sensor encontrado no boot; payload = ID do sensor'),
    '$ETEV10': ('Firmware Atualizado', 'OTA por Wi-Fi concluído'),
    '$ETEV11': ('Sem Sopro', 'não detectou sopro em 25 s'),
    '$ETEV12': ('Teste Randômico', 'teste randômico solicitado em viagem'),
    '$ETEV13': ('Sensor Quase Vencido', 'contador de sopros ≥ 1750 (payload = sopros)'),
    '$ETEV14': ('Sensor Vencido (sopros)', 'contador de sopros > 2500 — trocar sensor'),
    '$ETEV15': ('Teste Adiado', 'motorista adiou; veículo liberado por postpone_time'),
    '$ETEV16': ('Teste Realizado', 'teste de ignição concluído (com ou sem álcool)'),
    '$ETEV17': ('Início do Tempo de Manobra', 'desligou desbloqueado — ou resposta ao keep-alive $ETKA!'),
    '$ETEV18': ('Fim do Tempo de Manobra', 'manobra esgotou; segue bloqueio'),
    '$ETEV20': ('Sensor OK (diagnóstico)', 'autodiagnóstico do sensor de álcool aprovado'),
    '$ETEV22': ('Modo Manobrista Ativado', 'uso administrativo, partida sem teste'),
    '!ETEV23': ('Modo Manobrista Desativado', 'delimitadores invertidos de propósito no firmware'),
    '$ETEV24': ('Sensor Defeituoso', 'sensor de álcool/EEPROM sem resposta no I²C'),
    '$ETEV25': ('Teste Randômico Realizado', 'teste randômico concluído'),
    '$ETEV26': ('Contrassenha Aceita', 'liberação administrativa após positivo'),
    '$ETEV27': ('Temperatura Alta', '≥ 52 °C ou sensor de temperatura mudo'),
    '$ETEV28': ('Temperatura Crítica', '≥ 60 °C'),
    '$ETEV29': ('Leitura Sem Álcool', 'resultado negativo'),
    '$ETEV30': ('Álcool Detectado', 'resultado positivo (payload = mg/L × 1000; 0000 = sensor sem coeficientes)'),
    '$ETEV31': ('Ignição (veículo leve)', 'comando do rastreador (carro)'),
    '$ETEV32': ('Desbloqueio em Modo Manobrista', 'partida sem teste com manobrista ativo'),
    '$ETEV33': ('Teste Randômico Não Realizado', 'randômico sem sopro e recusou repetir'),
    '$ETEV34': ('Teste Randômico Adiado', 'adiou o randômico'),
    '$ETEV35': ('Motorista Não Autorizado', 'reprovou/não soprou COM o veículo em viagem — alarme até desligar'),
    '$ETEV36': ('Sensor Substituído', 'ID do sensor mudou (payload = novo ID)'),
    '$ETEV37': ('Bloqueio Remoto', 'registrado pelo servidor/portal'),
    '$ETEV38': ('Desbloqueio Remoto', 'registrado pelo servidor/portal'),
    '$ETEV40': ('Contrassenha Digitada', 'tentativa de contrassenha (payload = o que foi digitado)'),
    '$ETEV41': ('Umidade Alta', '≥ 95 %'),
}

MIX_BLIND = ('$ETEV29', '$ETEV30', '$ETEV35', '$ETEV24')


def say(msg=''):
    print(msg, flush=True)


def norm(text):
    text = unicodedata.normalize('NFKD', str(text or ''))
    return ''.join(c for c in text if not unicodedata.combining(c)).lower()


def plateKey(plate):
    return re.sub(r'[^A-Z0-9]', '', str(plate or '').upper())


def parseTime(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except ValueError:
        return None


def brt(value, fmt='%d/%m %H:%M:%S'):
    t = parseTime(value)
    if not t:
        return '?'
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return t.astimezone(BRT).strftime(fmt)


def age(value):
    t = parseTime(value)
    if not t:
        return 'nunca'
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - t
    hours = delta.total_seconds() / 3600
    if hours < 1:
        return f'há {int(delta.total_seconds() // 60)} min'
    if hours < 48:
        return f'há {hours:.0f} h'
    return f'há {hours / 24:.0f} dias'


def decode(event):
    """('$ETEV30', 'Álcool Detectado', detalhe)"""
    event = (event or '').strip()
    if event.startswith('!ETEV23'):
        code = '!ETEV23'
    else:
        m = re.match(r'^\$ETEV(\d{2})', event)
        code = f'$ETEV{m.group(1)}' if m else None
    if not code:
        return None, event, 'mensagem fora do formato de evento'
    label, info = EVENTS.get(code, ('(código desconhecido)', ''))
    payload = event.strip('$!')[6:] if code != '!ETEV23' else ''
    detail = ''
    if payload:
        if code == '$ETEV30':
            detail = 'SEM COEFICIENTES (0,000)' if not payload.strip('0') else f'{int(payload) / 1000:.3f} mg/L'
        elif code in ('$ETEV13', '$ETEV14'):
            detail = f'{int(payload)} sopros' if payload.isdigit() else payload
        elif code in ('$ETEV09', '$ETEV36'):
            detail = f'sensor {payload}'
        elif code == '$ETEV40':
            detail = f'digitou {payload}'
        else:
            detail = payload
    return code, label, detail


def api():
    from api import api as client
    return client


# ----------------------------------------------------------------- consultas

_companies = None


def companies():
    global _companies
    if _companies is None:
        _companies = {c['id']: c for c in api().rows('companies/', limit=500)}
    return _companies


def companyName(cnpj):
    c = companies().get(cnpj)
    return c['label'] if c else (cnpj or '?')


def findEtilometers(plate):
    """instalação(ões) pela placa: tenta o filtro exato e cai para a lista inteira (143 linhas)."""
    for candidate in dict.fromkeys([plate, plate.upper(), plate.strip()]):
        rows = api().rows('etilometers/', limit=50, vehicle_plate=candidate)
        if rows and len(rows) < 20:
            return rows
    key = plateKey(plate)
    return [e for e in api().rows('etilometers/', limit=500) if plateKey(e.get('vehicle')) == key]


def latestFirmware():
    try:
        rows = api().rows('firmwares/', limit=100)
    except Exception:
        return None
    best = None
    for f in rows:
        m = re.match(r'v?(\d+)\.(\d+)\.(\d+)', f.get('version') or '')
        if m and not f.get('deleted'):
            v = tuple(int(x) for x in m.groups())
            if not best or v > best[0]:
                best = (v, f.get('version'), f.get('release_date'))
    return best


def fetchLogs(plate, days=7, limit=2000, event=None):
    start = (datetime.now(timezone.utc) - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
    params = {'vehicle': plate, 'start': start, 'limit': min(limit, 2000)}
    if event:
        params['event'] = event
    data = api().get('logs/', **params)
    if not data:
        return []
    rows = data.get('results', []) if isinstance(data, dict) else data
    rows.sort(key=lambda r: r.get('timestamp') or '', reverse=True)
    return rows[:limit]


def lastEver(plate):
    data = api().get('logs/', vehicle=plate, limit=1)
    rows = (data or {}).get('results', []) if isinstance(data, dict) else (data or [])
    return rows[0] if rows else None


def notionCases(plate):
    docs = os.environ.get('SIGHIR_DOCS') or os.path.join(ROOT, '..', 'docs')
    path = os.path.join(docs, 'casos_notion.md')
    try:
        text = open(path, encoding='utf-8').read()
    except OSError:
        return []
    key = plateKey(plate)
    out = []
    for block in text.split('\n## ')[1:]:
        title = block.splitlines()[0]
        if key and key in plateKey(block[:400]):
            solution = re.search(r'\*\*Solução:\*\* (.*)', block)
            out.append((title, solution.group(1)[:200] if solution else ''))
    return out


# ----------------------------------------------------------------- comandos

def cmdInit(args):
    import boot
    report = boot.loadJson(boot.BOOT_JSON, None)
    if report:
        report['docs'] = boot.refreshDocs(sys.executable, boot.Out(False))
        boot.saveJson(boot.BOOT_JSON, report)
        say(boot.summary(report))
    else:
        say('ambiente ainda não preparado — rodando python tools/boot.py setup')
        boot.setup(interactive=True)
    try:
        client = api()
        client.check()  # reaproveita o token guardado (login custa ~1,3 s)
        n = client.get('etilometers/', limit=1) or {}
        a = client.get('anomalies/', solved='false', limit=1) or {}
        say(f"servidor: login OK | {n.get('count', '?')} etilômetros | {a.get('count', '?')} anomalias abertas")
    except Exception as err:
        say(f'servidor: FALHOU ({err}) — consultas ao servidor indisponíveis agora')
    return 0


def printTimeline(rows):
    """horário de chegada no servidor em BRT. O relógio de origem (created_at) só aparece quando o
    atraso não é o fuso de 3 h nem ~0 — ou seja, entrega em lote (típico da MiX) ou relógio errado."""
    say(f'{"servidor (BRT)":<16} {"evento":<16} significado')
    for r in rows:
        code, label, detail = decode(r.get('event'))
        when = brt(r.get('timestamp'))
        origin = parseTime(r.get('created_at'))
        server = parseTime(r.get('timestamp'))
        extra = ''
        if origin and server:
            if origin.tzinfo is None:
                origin = origin.replace(tzinfo=timezone.utc)
            diff = (server - origin).total_seconds()
            if min(abs(diff), abs(diff - 3 * 3600)) > 600:
                extra = f'  (origem {origin.strftime("%d/%m %H:%M")}*)'
        text = label + (f' — {detail}' if detail else '')
        say(f'{when:<16} {r.get("event", "")[:16]:<16} {text}{extra}')


def parallel(tasks):
    """roda consultas independentes ao mesmo tempo ({nome: função}); erro vira None."""
    from concurrent.futures import ThreadPoolExecutor
    api().check()  # autentica uma vez antes de abrir as threads
    with ThreadPoolExecutor(max_workers=min(8, len(tasks) or 1)) as pool:
        futures = {name: pool.submit(fn) for name, fn in tasks.items()}
    out = {}
    for name, fut in futures.items():
        try:
            out[name] = fut.result()
        except Exception:
            out[name] = None
    return out


# rótulo da telemetria no cadastro → comando equivalente no Tester (docs/telemetrias.md §1)
TESTER_TELEMETRY = {'MIX TELEMATICS': 'mix (MIX antigo, 0)', 'MIX TELEMATICS (NOVO)': 'mix2 (MIX 2.0, 5)',
                    'SUNTECH': 'suntech (2)', 'ENTRACK': 'entrack (6)'}


# seção do diagnostico.md → checklist oficial da equipe (Notion → Troubleshooting → docs/troubleshooting.md)
CHECKLISTS = {'S1': 'Problemas de Requisição de Teste', 'S2': 'Problemas de Bloqueio',
              'S3': 'Problemas de Bloqueio', 'S4': 'Problemas de Bloqueio', 'S6': 'Reiniciamentos Inesperados',
              'S9': 'Problemas de Sopro', 'S10': 'Problemas de Alcool', 'S13': 'Problemas de Comunicação',
              'S14': 'Problemas de Atualização', 'S16': 'Problemas de Conexão Aplicativo-Etilômetro'}


def checklists(clues, tel):
    """checklists da equipe que valem para as pistas (com a telemetria, quando a seção se divide por ela)."""
    kind = next((k for k in ('Suntech', 'Entrack', 'MIX') if k.upper() in (tel or '').upper()), None)
    names = []
    for code in re.findall(r'\b(S\d+)\b', ' '.join(clues)):
        name = CHECKLISTS.get(code)
        if name and name not in names:
            names.append(name)
    return [f'{n} › {kind}' if kind and n in ('Problemas de Requisição de Teste', 'Problemas de Bloqueio',
                                            'Problemas de Comunicação') else n for n in names]


def hints(tel, logs, last, counts, cal_days, version, anomalies):
    """pistas automáticas: número do servidor → seção do docs/diagnostico.md."""
    def c(*codes):
        return sum(counts.get(x, 0) for x in codes)
    out = []
    mix = 'MIX' in (tel or '').upper()
    if (tel or '').upper() not in TESTER_TELEMETRY:
        out.append(f'telemetria do cadastro "{tel}" não é um rastreador → cadastro inconsistente (S19)')
    if not last:
        out.append('nunca enviou log: instalação pendente, telemetria que não repassa ou placa diferente (S13)')
    else:
        seen = parseTime(last.get('timestamp'))
        idle = (datetime.now(timezone.utc) - seen).total_seconds() / 86400 if seen else 0
        if idle >= 7:
            out.append(f'sem comunicação há {idle:.0f} dias (S13; MiX de empresa que não repassa logs pode ser normal)')
    if c('$ETEV08') >= 3:
        out.append(f"{c('$ETEV08')} reinícios na janela → alimentação/bateria/fusível (S6)")
    if c('$ETEV24'):
        out.append(f"{c('$ETEV24')} × sensor defeituoso → I²C/encaixe do sensor (S7)")
    if c('$ETEV35'):
        out.append(f"{c('$ETEV35')} × motorista não autorizado → conduta depois de adiar (S11)")
    zeros = sum(1 for r in logs if (r.get('event') or '').startswith('$ETEV300000'))
    if zeros:
        out.append(f'{zeros} × álcool 0,000 mg/L → sensor sem coeficientes (S10)')
    if c('$ETEV11') >= 5 and c('$ETEV11') > 3 * max(c('$ETEV05'), 1):
        out.append(f"{c('$ETEV11')} sem sopro × {c('$ETEV05')} sopros válidos → sensor de pressão/bocal ou conduta (S9)")
    if c('$ETEV01') >= 5 and not c('$ETEV16', '$ETEV25', '$ETEV15', '$ETEV26', '$ETEV32', '$ETEV38'):
        out.append(f"{c('$ETEV01')} desbloqueios sem teste/adiamento na janela → liberação por outro caminho "
                   '(remoto, reinícios, manobrista) ou entrega parcial da telemetria (S1 hip. 1, S3)')
    if mix and c('$ETEV16', '$ETEV25') and not c('$ETEV29', '$ETEV30'):
        out.append('testes sem resultado: normal na MiX (não repassa $ETEV29/30) — o resultado só na tela/app')
    if cal_days is not None and cal_days > 365:
        out.append(f'calibração vencida há {cal_days - 365} dias (S18)')
    if version in (None, '', '1.0.0'):
        out.append('versão desconhecida no servidor: confirme na tela ID (S14)')
    if anomalies:
        out.append('há anomalia aberta: mapa categoria → seção no fim de diagnostico.md')
    return out


def cmdVeiculo(args):
    plate = args.placa
    rows = findEtilometers(plate)
    if not rows:
        say(f'nenhuma instalação (etilometers/) com a placa {plate!r}.')
        last = lastEver(plate)
        if last:
            say(f'mas há logs com essa placa: último {last.get("event")} {age(last.get("timestamp"))}')
        return 1
    if len(rows) > 1:
        say(f'⚠ {len(rows)} instalações com a placa {plate} (placa duplicada no cadastro):')

    tasks = {'fw': latestFirmware, 'companies': companies}
    for i, e in enumerate(rows):
        esp, sid, veh = e.get('esp_id'), e.get('sensor_id'), e.get('vehicle')
        tasks[f'dev{i}'] = (lambda esp=esp: api().get(f'devices/{esp}/') if esp else None)
        tasks[f'sensor{i}'] = (lambda sid=sid: api().get(f'sensors/{sid}/') if sid else None)
        tasks[f'sun{i}'] = (lambda esp=esp: moduleOf(esp))
        tasks[f'logs{i}'] = (lambda veh=veh: fetchLogs(veh, days=args.dias))
        tasks[f'last{i}'] = (lambda veh=veh: lastEver(veh))
        tasks[f'anom{i}'] = (lambda veh=veh: api().rows('anomalies/', limit=50, vehicle=veh, solved='false'))
    got = parallel(tasks)
    fw = got.get('fw')

    for i, e in enumerate(rows):
        say(f"\n=== {e.get('vehicle')} — {companyName(e.get('company'))} ===")
        tel = e.get('telemetry_label') or companyName(e.get('telemetry'))
        vt = {0: 'Caminhão', 1: 'Carro'}.get(e.get('vehicle_type'), e.get('vehicle_type'))
        tester = TESTER_TELEMETRY.get((tel or '').upper())
        say(f"instalação {e.get('id')} | {vt} | telemetria {tel}"
            f"{' (no Tester: telemetry ' + tester + ')' if tester else ''}"
            f" | instalado em {brt(e.get('installation_date'), '%d/%m/%Y')} por {e.get('installer') or '?'}"
            f" | operando={e.get('is_operating')}"
            f"{' | câmera ' + e['camera_service'] if e.get('camera_service') not in (None, '', 'None') else ''}")
        esp = e.get('esp_id')
        dev = got.get(f'dev{i}')
        version = (dev or {}).get('software_version') or e.get('software_version')
        vnote = ''
        if version in (None, '', '1.0.0'):
            vnote = ' (1.0.0 = nunca reportou pelo Wi-Fi; veja a tela ID)'
        elif fw:
            m = re.match(r'v?(\d+)\.(\d+)\.(\d+)', version)
            if m and tuple(int(x) for x in m.groups()) < fw[0]:
                vnote = f' (catálogo: {fw[1]} de {fw[2]}; pode estar defasado)'
        say(f"aparelho {esp} | série {(dev or {}).get('series_num', '?')} | firmware {version}{vnote}"
            f" | need_update={(dev or {}).get('need_update', e.get('device_need_update'))}"
            f" | chip {(dev or {}).get('chip') or next((s.get('chip') for s in got.get(f'sun{i}') or [] if s.get('chip')), '-')}")
        sid = e.get('sensor_id') or (dev or {}).get('sensor_id')
        sensor = got.get(f'sensor{i}') if e.get('sensor_id') else (api().get(f'sensors/{sid}/') if sid else None)
        cal_days = None
        if sid:
            if sensor and sensor.get('timestamp'):
                cal = parseTime(sensor['timestamp'])
                cal_days = (datetime.now(timezone.utc) - cal).days if cal else None
                status = 'VENCIDA (> 1 ano)' if cal_days and cal_days > 365 else 'válida'
                say(f"sensor {sid} | calibração {brt(sensor['timestamp'], '%d/%m/%Y')} ({cal_days} dias, {status})"
                    f" | solução {sensor.get('solution') or '?'}")
            else:
                say(f'sensor {sid} | sem calibração registrada no servidor')
        for s in got.get(f'sun{i}') or []:
            say(f"módulo {s.get('id')} | conectado={s.get('is_connected')} ignição={s.get('is_ignition_on')}"
                f" relé={s.get('is_relay_on')} | pendente bloquear={s.get('has_to_block')} "
                f"desbloquear={s.get('has_to_unblock')} | {s.get('ip')}:{s.get('port')} "
                '(flags podem estar defasadas: confira pelos logs)')

        logs = got.get(f'logs{i}') or []
        last = logs[0] if logs else got.get(f'last{i}')
        if not last:
            say('comunicação: NENHUM log desta placa no servidor')
        else:
            code, label, _ = decode(last.get('event'))
            say(f"último evento: {last.get('event')} {label} — {brt(last.get('timestamp'), '%d/%m/%Y %H:%M')}"
                f" ({age(last.get('timestamp'))})")
        counts = {}
        for r in logs:
            code, _, _ = decode(r.get('event'))
            counts[code] = counts.get(code, 0) + 1
        if logs:
            def c(*codes):
                return sum(counts.get(x, 0) for x in codes)
            say(f"últimos {args.dias} dias ({len(logs)} logs): testes {c('$ETEV16', '$ETEV25')} | sem álcool {c('$ETEV29')}"
                f" | álcool {c('$ETEV30')} | desbloq {c('$ETEV01')} | bloq {c('$ETEV02')} | boots {c('$ETEV08')}"
                f" | sem sopro {c('$ETEV11')} | adiados {c('$ETEV15', '$ETEV34')} | não autorizado {c('$ETEV35')}"
                f" | sensor defeituoso {c('$ETEV24')} | randômicos {c('$ETEV12')}")
            state = next((r for r in logs if (r.get('event') or '').startswith(('$ETEV01', '$ETEV02'))), None)
            if state:
                say(f"último estado informado: {'DESBLOQUEADO' if state['event'].startswith('$ETEV01') else 'BLOQUEADO'}"
                    f" em {brt(state.get('timestamp'))}")
        if 'MIX' in (tel or '').upper():
            say('nota MiX: resultado ($ETEV29/30), $ETEV35 e $ETEV24 não chegam pela MiX; eventos chegam em lote.')

        anomalies = got.get(f'anom{i}') or []
        clues = hints(tel, logs, last, counts, cal_days, version, anomalies)
        if clues:
            say('\npistas (docs/diagnostico.md):')
            for clue in clues:
                say(f'  - {clue}')
            steps = checklists(clues, tel)
            if steps:
                say('  checklist da equipe (docs/troubleshooting.md): ' + ' | '.join(steps))
        if logs and args.eventos:
            say(f'\nlinha do tempo (últimos {min(args.eventos, len(logs))}):')
            printTimeline(logs[:args.eventos])
        if anomalies:
            say('\nanomalias abertas:')
            for a in anomalies:
                say(f"  [{a.get('category')}] {(a.get('desc') or '').splitlines()[0][:220]}")
        cases = notionCases(e.get('vehicle'))
        if cases:
            say('\nchamados anteriores no Notion (casos_notion.md):')
            for title, sol in cases:
                say(f'  - {title}' + (f' → {sol}' if sol else ''))
    return 0


def cmdLogs(args):
    rows = fetchLogs(args.placa, days=args.dias, limit=args.limite, event=args.evento)
    if not rows:
        say(f'nenhum log de {args.placa} nos últimos {args.dias} dias'
            + (f' com evento {args.evento}' if args.evento else ''))
        last = lastEver(args.placa)
        if last:
            say(f'último log da placa: {last.get("event")} em {brt(last.get("timestamp"))} ({age(last.get("timestamp"))})')
        return 1
    say(f'{len(rows)} log(s) de {args.placa} (mais recente primeiro; horário do servidor em BRT, * = relógio de origem difere):')
    printTimeline(rows)
    return 0


def cmdEvento(args):
    code, label, detail = decode(args.codigo if args.codigo.startswith(('$', '!')) else '$' + args.codigo.strip('$!') + '!')
    if not code:
        say(f'{args.codigo}: não é um evento $ETEVnn! (pode ser mensagem de controle — veja comandos_config.md §6)')
        return 1
    info = EVENTS.get(code, ('?', ''))[1]
    say(f'{code}! — {label}' + (f' ({detail})' if detail else ''))
    say(f'  {info}')
    if code in MIX_BLIND:
        say('  não chega ao servidor por veículos MiX (medido na base inteira)')
    say('  detalhes: docs/firmware_reference.md §2 (linha do firmware, fluxos) e Notion/main.pdf §2.3')
    return 0


def moduleOf(esp, dev=None):
    """módulo rastreador do aparelho: devices/<MIC>/.telemetry → telemetries/<id>/ (era suntechs/?device=,
    404 desde a migração de 24/09/2026). MiX não tem módulo vinculado."""
    if not esp:
        return []
    dev = dev or api().get(f'devices/{esp}/') or {}
    tid = dev.get('telemetry')
    mod = api().get(f'telemetries/{tid}/') if tid else None
    return [mod] if mod else []


def cmdDevice(args):
    dev = api().get(f'devices/{args.esp_id}/')
    if not dev:
        say(f'device {args.esp_id} não existe no servidor')
        return 1
    say(f"device {dev['id']} | série {dev.get('series_num')} | empresa {companyName(dev.get('company'))}"
        f" | sensor {dev.get('sensor_id')} | firmware {dev.get('software_version')} | need_update={dev.get('need_update')}"
        f" | módulo {dev.get('telemetry') or '-'} | cadastrado {brt(dev.get('timestamp'), '%d/%m/%Y')}")
    if dev.get('default_settings'):
        say(f"default_settings: {json.dumps(dev['default_settings'], ensure_ascii=False)[:300]}")
    inst = [e for e in api().rows('etilometers/', limit=500) if e.get('esp_id') == args.esp_id]
    for e in inst:
        say(f"instalado na placa {e.get('vehicle')} ({e.get('telemetry_label')}) desde {brt(e.get('installation_date'), '%d/%m/%Y')}")
    if not inst:
        say('sem instalação (etilometers/) — em estoque ou instalação não cadastrada')
    for s in moduleOf(args.esp_id, dev):
        say(f"módulo {s.get('id')} chip {s.get('chip') or '-'} conectado={s.get('is_connected')}"
            f" ignição={s.get('is_ignition_on')} relé={s.get('is_relay_on')}")
    return 0


def cmdAnomalias(args):
    params = {'solved': 'false'}
    if args.placa:
        params['vehicle'] = args.placa
    rows = api().rows('anomalies/', limit=500, **params)
    if not rows:
        say('nenhuma anomalia aberta' + (f' para {args.placa}' if args.placa else ''))
        return 0
    by = {}
    for a in rows:
        by.setdefault(a.get('category'), []).append(a)
    say(f'{len(rows)} anomalia(s) aberta(s):')
    for cat, items in sorted(by.items(), key=lambda kv: -len(kv[1])):
        say(f'\n[{cat}] {len(items)}')
        for a in items[: (50 if args.placa else args.max)]:
            say(f"  {a.get('vehicle'):<14} {(a.get('desc') or '').splitlines()[0][:160]}")
        if len(items) > (50 if args.placa else args.max):
            say(f'  … +{len(items) - args.max}')
    return 0


def cmdLista(args):
    rows = parallel({'rows': lambda: api().rows('etilometers/', limit=500), 'companies': companies}).get('rows') or []
    out = []
    for e in rows:
        comp = companyName(e.get('company'))
        tel = e.get('telemetry_label') or ''
        if args.empresa and norm(args.empresa) not in norm(comp):
            continue
        if args.telemetria and norm(args.telemetria) not in norm(tel):
            continue
        out.append((comp, e.get('vehicle') or '', tel, e.get('esp_id') or '', e.get('software_version') or '',
                    brt(e.get('installation_date'), '%d/%m/%Y'), e.get('is_operating')))
    out.sort()
    say(f'{len(out)} instalação(ões):')
    for comp, plate, tel, esp, ver, inst, op in out:
        say(f'{comp[:24]:<24} {plate:<14} {tel[:22]:<22} {esp:<20} fw {ver:<8} {inst} {"" if op else "(não operando)"}')
    return 0


def cmdBusca(args):
    docs = os.environ.get('SIGHIR_DOCS') or os.path.join(ROOT, '..', 'docs')
    kb = os.path.join(docs, 'tools', 'kb.py')
    if not os.path.isfile(kb):
        say('base docs/ não encontrada ao lado desta pasta')
        return 1
    cmd = [sys.executable, kb, 'busca'] + args.termos + ['-n', str(args.n)]
    if args.codigo:
        cmd.append('--codigo')
    return subprocess.call(cmd)


def cmdChamado(args):
    now = datetime.now(BRT)
    lines = [f'# {args.problema}', '',
             f'Status: {args.status}', f'Data: {now:%d/%m/%Y %H:%M} (BRT)']
    if args.tipo:
        lines.append(f'Tipo de problema: {args.tipo}')
    if args.empresa:
        lines.append(f'Empresa: {args.empresa}')
    lines.append(f'Placa do Veículo: {args.placa}')
    if args.responsavel:
        lines.append(f'Responsável: {args.responsavel}')
    lines += ['', '## Informações (Tela “Info” do Etilometro)', '',
              f'- Telemetria: {args.telemetria or ""}', f'- Tempo ligado: {args.tempo_ligado or ""}',
              f'- Status de viagem: {args.status_viagem or ""}', f'- SSID do roteador: {args.ssid or ""}',
              f'- Versão de firmware (Tela ID): {args.firmware or ""}', '',
              '## Descrição da tarefa', '', args.descricao or '', '', '## Observações', '']
    for obs in args.obs or []:
        lines.append(f'- [ ] {obs}')
    lines += ['', '## Solução', '', args.solucao or '', '']
    if args.evidencias:
        lines += ['## Evidências (Sighir Helper AI)', '', args.evidencias, '']
    text = '\n'.join(lines)
    folder = os.path.join(ROOT, 'chamados')
    os.makedirs(folder, exist_ok=True)
    slug = re.sub(r'[^a-z0-9]+', '-', norm(args.problema))[:40].strip('-')
    path = os.path.join(folder, f'{now:%Y-%m-%d}_{plateKey(args.placa) or "sem-placa"}_{slug}.md')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)
    say(text)
    say(f'\n(salvo em {os.path.relpath(path, ROOT)} — cole no Notion em "Resolução de Problemas")')
    return 0


def parseValue(raw):
    low = raw.lower()
    if low in ('true', 'false'):
        return low == 'true'
    if low in ('null', 'none'):
        return None
    if re.fullmatch(r'-?\d+', raw):
        return int(raw)
    return raw


def cmdPatch(args):
    from api import WRITABLE
    data = {}
    for pair in args.campos:
        if '=' not in pair:
            say(f'formato inválido: {pair!r} (use campo=valor)')
            return 2
        key, value = pair.split('=', 1)
        data[key.strip()] = parseValue(value.strip())
    allowed = WRITABLE.get(args.recurso, set())
    bad = set(data) - allowed
    if bad:
        say(f'campos não permitidos em {args.recurso}: {", ".join(sorted(bad))} (permitidos: {", ".join(sorted(allowed))})')
        return 2
    current = api().get(f'{args.recurso}/{args.id}/')
    if current is None:
        say(f'{args.recurso}/{args.id} não existe')
        return 1
    say(f'PRODUÇÃO — {args.recurso}/{args.id}:')
    for key, value in data.items():
        say(f'  {key}: {current.get(key)!r} → {value!r}')
    if not args.sim:
        say('\nnada foi alterado. Confirme com o usuário e rode de novo com --sim.')
        return 3
    api().patch(args.recurso, args.id, data)
    after = api().get(f'{args.recurso}/{args.id}/') or {}
    ok = all(after.get(k) == v for k, v in data.items())
    say(('OK — conferido: ' if ok else 'ATENÇÃO — valor lido depois difere: ') +
        ', '.join(f'{k}={after.get(k)!r}' for k in data))
    return 0 if ok else 1


def build():
    p = argparse.ArgumentParser(prog='helper', description='Sighir Helper AI — suporte técnico')
    sub = p.add_subparsers(dest='cmd', required=True)
    sub.add_parser('init', help='ambiente, servidor e base').set_defaults(func=cmdInit)

    v = sub.add_parser('veiculo', help='raio-x completo de uma placa')
    v.add_argument('placa')
    v.add_argument('--dias', type=int, default=7, help='janela de logs (padrão 7)')
    v.add_argument('--eventos', type=int, default=25, help='quantos eventos mostrar na linha do tempo (0 = nenhum)')
    v.set_defaults(func=cmdVeiculo)

    l = sub.add_parser('logs', help='linha do tempo decodificada')
    l.add_argument('placa')
    l.add_argument('--dias', type=int, default=3)
    l.add_argument('--limite', type=int, default=80)
    l.add_argument('--evento', help='filtra (ex.: ETEV02 ou $ETEV30,$ETEV29)')
    l.set_defaults(func=cmdLogs)

    e = sub.add_parser('evento', help='explica um evento $ETEVnn!')
    e.add_argument('codigo')
    e.set_defaults(func=cmdEvento)

    d = sub.add_parser('device', help='hardware MIC… e onde está instalado')
    d.add_argument('esp_id')
    d.set_defaults(func=cmdDevice)

    a = sub.add_parser('anomalias', help='alertas abertos do Scanner')
    a.add_argument('placa', nargs='?')
    a.add_argument('--max', type=int, default=8, help='itens por categoria (sem placa)')
    a.set_defaults(func=cmdAnomalias)

    s = sub.add_parser('lista', help='instalações (filtros por empresa/telemetria)')
    s.add_argument('--empresa')
    s.add_argument('--telemetria')
    s.set_defaults(func=cmdLista)

    b = sub.add_parser('busca', help='busca na base docs/')
    b.add_argument('termos', nargs='+')
    b.add_argument('-n', type=int, default=6)
    b.add_argument('--codigo', action='store_true')
    b.set_defaults(func=cmdBusca)

    c = sub.add_parser('chamado', help='gera o chamado no formato do Notion (Resolução de Problemas)')
    c.add_argument('--placa', required=True)
    c.add_argument('--problema', required=True, help='título')
    c.add_argument('--status', default='Pendente')
    c.add_argument('--tipo', help='Comunicação, Elétrico, Funcionamento, Não identificado, RETIRADO')
    c.add_argument('--empresa')
    c.add_argument('--responsavel')
    c.add_argument('--telemetria')
    c.add_argument('--tempo-ligado')
    c.add_argument('--status-viagem')
    c.add_argument('--ssid')
    c.add_argument('--firmware')
    c.add_argument('--descricao')
    c.add_argument('--obs', action='append', help='observação (repetível)')
    c.add_argument('--solucao')
    c.add_argument('--evidencias', help='resumo do que o servidor mostrou')
    c.set_defaults(func=cmdChamado)

    w = sub.add_parser('patch', help='altera campos em produção (devices/telemetries) — exige --sim')
    w.add_argument('recurso', choices=['devices', 'telemetries'])
    w.add_argument('id', help='MIC… (devices: aparelho e instalação) ou ID do módulo (telemetries)')
    w.add_argument('campos', nargs='+', help='campo=valor')
    w.add_argument('--sim', action='store_true', help='executa de verdade (depois de o usuário confirmar)')
    w.set_defaults(func=cmdPatch)
    return p


def main():
    args = build().parse_args()
    try:
        return args.func(args)
    except KeyboardInterrupt:
        return 130
    except Exception as err:
        say(f'ERRO: {err}')
        return 1


if __name__ == '__main__':
    sys.exit(main())
