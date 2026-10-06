#!/usr/bin/env python3
"""
servidor.py — traz do servidor de produção Sighir o que a base de conhecimento precisa (só leitura).

    python servidor.py resumo      gera docs/servidor_resumo.md: frota por telemetria e empresa, firmware
                                   em campo × catálogo, última comunicação, calibração, anomalias abertas
    python servidor.py snapshot    baixa o banco (db.sqlite3) por scp para docs/ServerAnalysis/files/
                                   (precisa da chave .pem; sem ela, pula)
    python servidor.py tudo        os dois

Só a biblioteca padrão. Nunca `limit=all` (derruba a produção): paginação de 500 e poucas threads.
Credenciais: SIGHIR_API_USER / SIGHIR_API_PASS (padrão: a conta de serviço das IAs).
"""

import os
import re
import sys
import ssl
import json
import time
import shutil
import argparse
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

TOOLS    = os.path.dirname(os.path.abspath(__file__))
DOCS     = os.path.dirname(TOOLS)
OUT_MD   = os.path.join(DOCS, 'servidor_resumo.md')
SNAPSHOT = os.path.join(DOCS, 'ServerAnalysis', 'files', 'db.sqlite3')
URL      = os.environ.get('SIGHIR_API_URL', 'https://sighir.com:8000/api/v2')
USER     = os.environ.get('SIGHIR_API_USER', 'sighir@gmail.com')
PASS     = os.environ.get('SIGHIR_API_PASS', 'sighir12345')
HOST     = os.environ.get('SIGHIR_SSH_HOST', 'ubuntu@52.91.100.216')
REMOTE_DB = '/home/ubuntu/v2/api/db.sqlite3'
BRT      = timezone(timedelta(hours=-3))
CTX      = ssl._create_unverified_context()


def say(msg=''):
    print(msg, flush=True)


class Api:
    def __init__(self):
        self.access, self.exp = None, 0

    def login(self):
        body = json.dumps({'username': USER, 'password': PASS}).encode()
        req = urllib.request.Request(f'{URL}/token/', data=body, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=40, context=CTX) as r:
            self.access = json.loads(r.read())['access']
        self.exp = time.time() + 240

    def get(self, endpoint, **params):
        if str(params.get('limit', '')).lower() in ('all', '0'):
            raise ValueError('limit=all derruba a produção')
        for attempt in range(4):
            if not self.access or time.time() > self.exp:
                self.login()
            url = f'{URL}/{endpoint.lstrip("/")}' + ('?' + urllib.parse.urlencode(params) if params else '')
            req = urllib.request.Request(url, headers={'Authorization': f'Bearer {self.access}'})
            try:
                with urllib.request.urlopen(req, timeout=90, context=CTX) as r:
                    return json.loads(r.read())
            except urllib.error.HTTPError as err:
                if err.code == 404:
                    return None
                if err.code == 401:
                    self.access = None
                    continue
                if err.code >= 500 and attempt < 3:
                    time.sleep(2 * (attempt + 1))
                    continue
                raise
            except (urllib.error.URLError, TimeoutError) as err:
                if attempt >= 1:
                    raise RuntimeError(f'servidor inacessível: {err}')
                time.sleep(2)
        raise RuntimeError(f'GET {endpoint} falhou')

    def rows(self, endpoint, limit=500, max_rows=20000, **params):
        out, page = [], 1
        while True:
            data = self.get(endpoint, limit=limit, page=page, **params)
            if data is None:
                return out
            if isinstance(data, list):
                return data
            out += data.get('results', [])
            if not data.get('next') or len(out) >= max_rows:
                return out
            page += 1


def parseTime(value):
    try:
        dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def version(v):
    m = re.match(r'v?(\d+)\.(\d+)\.(\d+)', v or '')
    return tuple(int(x) for x in m.groups()) if m else None


def bucket(days):
    if days is None:
        return 'nunca'
    if days < 1:
        return '< 1 dia'
    if days < 7:
        return '1–7 dias'
    if days < 30:
        return '7–30 dias'
    return '> 30 dias'


def table(header, rows):
    out = ['| ' + ' | '.join(header) + ' |', '|' + '---|' * len(header)]
    out += ['| ' + ' | '.join(str(c) for c in r) + ' |' for r in rows]
    return out


def resumo():
    api = Api()
    started = time.time()
    now = datetime.now(timezone.utc)
    comps = {c['id']: c for c in api.rows('companies/')}
    inst = api.rows('etilometers/')
    firmwares = api.rows('firmwares/', limit=100)
    anomalies = api.rows('anomalies/', solved='false')

    def lastLog(plate):
        data = api.get('logs/', vehicle=plate, limit=1) if plate else None
        rows = (data or {}).get('results', []) if isinstance(data, dict) else (data or [])
        return parseTime(rows[0].get('timestamp')) if rows else None

    def sensorDate(sid):
        data = api.get(f'sensors/{sid}/') if sid else None
        return parseTime((data or {}).get('timestamp'))

    with ThreadPoolExecutor(4) as pool:          # poucas threads: a produção é um SQLite num t2.large
        lasts = list(pool.map(lambda e: lastLog(e.get('vehicle')), inst))
        cals = list(pool.map(lambda e: sensorDate(e.get('sensor_id')), inst))

    name = lambda cid: (comps.get(cid) or {}).get('label') or (cid or '?')  # noqa: E731
    latest = max(((version(f.get('version')), f) for f in firmwares
                  if version(f.get('version')) and not f.get('deleted')), default=(None, {}), key=lambda t: t[0])[1]
    fleet = []
    for e, last, cal in zip(inst, lasts, cals):
        idle = (now - last).total_seconds() / 86400 if last else None
        calDays = (now - cal).days if cal else None
        fleet.append({'placa': e.get('vehicle') or '?', 'empresa': name(e.get('company')),
                      'telemetria': e.get('telemetry_label') or name(e.get('telemetry')),
                      'firmware': e.get('software_version') or '?', 'operando': e.get('is_operating'),
                      'tipo': {0: 'caminhão', 1: 'carro', 2: 'maleta'}.get(e.get('vehicle_type'), e.get('vehicle_type')),
                      'ultimo': last, 'parado': idle, 'cal': calDays, 'esp': e.get('esp_id') or '?'})

    def count(key):
        out = {}
        for f in fleet:
            out[f[key]] = out.get(f[key], 0) + 1
        return sorted(out.items(), key=lambda kv: -kv[1])

    L = ['# Servidor de produção — resumo da frota (gerado)', '',
         f'> Gerado por `tools/servidor.py resumo` em {datetime.now(BRT):%d/%m/%Y %H:%M} (BRT), só leitura da API '
         f'(`{URL}`). Não edite: "sincronizar os documentos" refaz. Números mudam todo dia — para uma placa '
         'específica use o Helper (`helper.py veiculo PLACA`).', '',
         f'**{len(fleet)} instalações** em {len({f["empresa"] for f in fleet})} empresas · '
         f"{sum(1 for f in fleet if f['operando'])} operando · anomalias abertas: {len(anomalies)} · "
         f"firmware mais novo no catálogo: **{latest.get('version', '?')}** "
         f"({(latest.get('release_date') or '')[:10]})", '']

    L += ['## Por telemetria', ''] + table(['telemetria', 'instalações'], count('telemetria')) + ['']
    comm = {}
    for f in fleet:
        comm[bucket(f['parado'])] = comm.get(bucket(f['parado']), 0) + 1
    order = ['< 1 dia', '1–7 dias', '7–30 dias', '> 30 dias', 'nunca']
    L += ['## Última comunicação (último log recebido)', '',
          'Na MiX de empresa que não repassa logs, "sem comunicação" pode ser normal (`telemetrias.md`).', '']
    L += table(['há quanto tempo', 'instalações'], [(k, comm.get(k, 0)) for k in order]) + ['']
    calBuckets = {'vencida (> 365 dias)': 0, 'vence em ≤ 30 dias': 0, 'em dia': 0, 'sem dado': 0}
    for f in fleet:
        d = f['cal']
        key = 'sem dado' if d is None else 'vencida (> 365 dias)' if d > 365 else \
            'vence em ≤ 30 dias' if d > 335 else 'em dia'
        calBuckets[key] += 1
    L += ['## Calibração do sensor (data da calibração corrente, regra de 1 ano)', ''] + \
        table(['situação', 'instalações'], calBuckets.items()) + ['']
    fw = count('firmware')
    L += ['## Firmware reportado × catálogo', '',
          '`software_version` só muda no check-update via Wi-Fi; `1.0.0` = nunca reportou (`portal_app.md` §4).', '']
    L += table(['versão reportada', 'instalações'], fw) + ['']
    L += ['Catálogo (`firmwares/`, mais novas primeiro):', '']
    cat = sorted((f for f in firmwares if version(f.get('version'))), key=lambda f: version(f['version']), reverse=True)
    L += table(['versão', 'data', 'descrição'],
               [(f.get('version'), (f.get('release_date') or '')[:10],
                 re.sub(r'\s+', ' ', f.get('desc') or '')[:90].replace('|', '/')) for f in cat[:8]]) + ['']
    cats = {}
    for a in anomalies:
        cats[a.get('category') or '(sem categoria)'] = cats.get(a.get('category') or '(sem categoria)', 0) + 1
    L += ['## Anomalias abertas (Scanner)', ''] + \
        table(['categoria', 'abertas'], sorted(cats.items(), key=lambda kv: -kv[1])) + ['']
    per = {}
    for f in fleet:
        p = per.setdefault(f['empresa'], {'n': 0, 'tel': set(), 'mudo': 0, 'venc': 0})
        p['n'] += 1
        p['tel'].add(f['telemetria'])
        p['mudo'] += 1 if (f['parado'] is None or f['parado'] >= 7) else 0
        p['venc'] += 1 if (f['cal'] or 0) > 365 else 0
    L += ['## Por empresa', ''] + table(
        ['empresa', 'instalações', 'telemetrias', 'sem log ≥ 7 dias', 'calibração vencida'],
        [(k, v['n'], ', '.join(sorted(v['tel'])), v['mudo'], v['venc'])
         for k, v in sorted(per.items(), key=lambda kv: -kv[1]['n'])]) + ['']
    tels = [c for c in comps.values() if c.get('type') == 'telemetry']
    L += ['## Telemetrias cadastradas (`companies/`, type=telemetry)', '',
          'O `value` é o modo de telemetria gravado no aparelho (`telemetrias.md`).', '']
    L += table(['telemetria', 'value', 'id'], [(c.get('label'), c.get('value'), c.get('id'))
                                               for c in sorted(tels, key=lambda c: str(c.get('value')))]) + ['']
    L += ['## Instalações', '']
    L += table(['placa', 'empresa', 'telemetria', 'tipo', 'aparelho', 'firmware', 'último log', 'calibração (dias)',
                'operando'],
               [(f['placa'], f['empresa'], f['telemetria'], f['tipo'], f['esp'], f['firmware'],
                 f['ultimo'].astimezone(BRT).strftime('%d/%m/%Y') if f['ultimo'] else 'nunca',
                 f['cal'] if f['cal'] is not None else '?', 'sim' if f['operando'] else 'não')
                for f in sorted(fleet, key=lambda f: (f['empresa'], f['placa']))]) + ['']
    text = '\n'.join(L)
    try:
        old = open(OUT_MD, encoding='utf-8').read()
    except OSError:
        old = ''
    strip = lambda t: re.sub(r'em \d{2}/\d{2}/\d{4} \d{2}:\d{2} \(BRT\)', '', t)  # noqa: E731
    if strip(old) != strip(text):
        with open(OUT_MD, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
    say(f'servidor: {len(fleet)} instalações, {len(anomalies)} anomalias abertas, firmware mais novo '
        f"{latest.get('version', '?')} → docs/servidor_resumo.md ({time.time() - started:.0f}s)")
    return 0


def findKey():
    cands = [os.environ.get('SIGHIR_PEM'),
             os.path.join(DOCS, '..', '..', 'Etilometro', 'pwdsighir.pem'),
             os.path.join(DOCS, '..', '..', 'Suntech Monitor', 'pwdsighir.pem'),
             os.path.join(os.path.expanduser('~'), '.ssh', 'pwdsighir.pem')]
    return next((os.path.abspath(c) for c in cands if c and os.path.isfile(c)), None)


def snapshot():
    key = findKey()
    scp = shutil.which('scp')
    if not key or not scp:
        say('snapshot: pulado (' + ('chave pwdsighir.pem não encontrada — defina SIGHIR_PEM' if not key
                                    else 'scp não encontrado') + '). O Scanner funciona sem ele.')
        return 0
    os.makedirs(os.path.dirname(SNAPSHOT), exist_ok=True)
    tmp = SNAPSHOT + '.baixando'
    started = time.time()
    cmd = [scp, '-q', '-i', key, '-o', 'StrictHostKeyChecking=accept-new', '-o', 'BatchMode=yes',
           '-o', 'ConnectTimeout=20', f'{HOST}:{REMOTE_DB}', tmp]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    except subprocess.TimeoutExpired:
        say('snapshot: tempo esgotado (15 min) — mantido o anterior')
        return 1
    if res.returncode != 0 or not os.path.exists(tmp) or os.path.getsize(tmp) < 1_000_000:
        say(f'snapshot: falhou ({(res.stderr or "").strip()[:200]}) — mantido o anterior')
        if os.path.exists(tmp):
            os.remove(tmp)
        return 1
    os.replace(tmp, SNAPSHOT)
    say(f'snapshot: {os.path.getsize(SNAPSHOT) // 1048576} MB → docs/ServerAnalysis/files/db.sqlite3 '
        f'({time.time() - started:.0f}s)')
    return 0


def main():
    p = argparse.ArgumentParser(prog='servidor', description='Servidor Sighir → docs/ (só leitura)')
    p.add_argument('cmd', choices=['resumo', 'snapshot', 'tudo'])
    args = p.parse_args()
    code = 0
    try:
        if args.cmd in ('resumo', 'tudo'):
            code |= resumo()
    except Exception as err:
        say(f'servidor: resumo falhou — {err}')
        code = 1
    if args.cmd in ('snapshot', 'tudo'):
        code |= snapshot()
    return code


if __name__ == '__main__':
    sys.exit(main())
