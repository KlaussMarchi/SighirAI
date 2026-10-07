#!/usr/bin/env python3
"""
contrato.py — o "contrato" do servidor de produção: o que a API e o banco oferecem hoje, o que mudou desde a
última vez e o que as três IAs (Tester, Server, Helper) precisam dele. Só leitura.

    python contrato.py diferenca [--salvar]   compara o servidor de agora com docs/servidor_contrato.json e
                                              mostra rotas/campos/tabelas/migrações novas ou sumidas, com os
                                              arquivos do repositório que usam cada coisa que mudou
    python contrato.py verificar              confere, campo a campo, se a API ainda tem tudo o que as IAs
                                              leem e gravam (USO abaixo); código 1 se faltar algo
    python contrato.py capturar               só grava o contrato atual em docs/servidor_contrato.json
    python contrato.py uso                    tabela "rota/campo → quem usa" (para revisar o impacto)

O contrato guarda NOMES (rotas, campos, tipos, obrigatoriedade, colunas, migrações), nunca valores.
Banco: lido do snapshot docs/ServerAnalysis/files/db.sqlite3 (atualize antes com `servidor.py snapshot`).
Procedimento completo quando o servidor muda: docs/migracao_servidor.md.
"""

import os
import re
import ast
import sys
import json
import sqlite3
import argparse
import urllib.error
import urllib.request
from datetime import datetime

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
from servidor import Api, URL, CTX, SNAPSHOT, BRT, say  # noqa: E402

DOCS = os.path.dirname(TOOLS)
ROOT = os.path.dirname(DOCS)
CONTRACT = os.path.join(DOCS, 'servidor_contrato.json')
EXTRA_ROUTES = ['companies/']          # rotas usadas que não aparecem na raiz do router
CODE_DIRS = ['Tester', 'Server', 'Helper', os.path.join('docs', 'tools')]
SKIP_DIRS = {'.venv', '__pycache__', '.git', 'launcher', 'node_modules'}

# O QUE CADA IA USA DO SERVIDOR. Mudou o código de uma IA → atualize aqui (o `verificar` confere contra a API).
# 'le' = campos lidos de cada linha; 'grava' = campos enviados em POST/PATCH.
USO = {
    'devices/': {
        'le': {'Tester register/install/server-device': ['id', 'plate', 'telemetry', 'telemetry_company',
                                                          'installation_data', 'series_num', 'company'],
               'Tester onde/duplicidade': ['id', 'sensor_id', 'telemetry', 'plate', 'series_num', 'company',
                                           'installation_date', 'telemetry_company_label'],
               'Helper veiculo/device': ['id', 'series_num', 'sensor_id', 'software_version', 'need_update',
                                         'telemetry', 'company', 'timestamp', 'default_settings']},
        'grava': {'Tester register': ['id', 'company', 'series_num', 'sensor_id', 'need_update', 'telemetry'],
                  'Tester install': ['plate', 'vehicle_type', 'telemetry_company', 'telemetry', 'is_operating',
                                     'installation_date', 'installer', 'nickname', 'installation_data'],
                  'Tester edit': ['company', 'series_num', 'sensor_id', 'telemetry', 'plate', 'telemetry_company',
                                  'installation_date', 'installer', 'nickname', 'installation_data', 'need_update'],
                  'Tester flash (re-arma)': ['need_update'],
                  'Helper patch': 'WRITABLE:devices'},
    },
    'telemetries/': {
        'le': {'Helper veiculo/device': ['id', 'chip', 'is_connected', 'is_ignition_on', 'is_relay_on',
                                         'has_to_block', 'has_to_unblock', 'ip', 'port'],
               'Tester register/install': ['id', 'chip', 'vehicle']},
        'grava': {'Tester register/install': ['id', 'chip'], 'Helper patch': 'WRITABLE:telemetries'},
    },
    'etilometers/': {
        'le': {'Server scanner': ['vehicle', 'telemetry', 'telemetry_label', 'installation_date', 'sensor_id',
                                  'software_version', 'esp_id', 'company'],
               'Helper veiculo/lista': ['vehicle', 'esp_id', 'sensor_id', 'telemetry', 'telemetry_label', 'company',
                                        'vehicle_type', 'installation_date', 'installer', 'is_operating', 'id'],
               'Tester install (dedup/conferência)': ['vehicle', 'esp_id', 'telemetry_label', 'installation_date'],
               'docs servidor.py': ['vehicle', 'esp_id', 'telemetry_label', 'company', 'software_version']},
    },
    'logs/': {
        'le': {'Server scanner': ['vehicle', 'event', 'timestamp', 'created_at'],
               'Helper veiculo/eventos': ['vehicle', 'event', 'timestamp', 'created_at']},
    },
    'anomalies/': {
        'le': {'Server scanner': ['id', 'vehicle', 'category', 'desc', 'solved', 'deleted'],
               'Helper anomalias': ['vehicle', 'category', 'desc', 'solved']},
        'grava': {'Server scanner': ['vehicle', 'category', 'desc', 'solved']},
    },
    'sensors/': {'le': {'Server scanner / Helper': ['id', 'timestamp', 'solution', 'deleted']}},
    'firmwares/': {'le': {'Server scanner / Helper / servidor.py': ['version', 'release_date', 'deleted']}},
    'companies/': {'le': {'todas': ['id', 'label', 'type', 'value']}},
}


def options(api, route):
    """metadados do DRF (OPTIONS): campos de escrita com tipo/obrigatório/somente leitura/limites/escolhas."""
    if not api.access:
        api.login()
    req = urllib.request.Request(f'{URL}/{route}', method='OPTIONS',
                                 headers={'Authorization': f'Bearer {api.access}'})
    try:
        with urllib.request.urlopen(req, timeout=60, context=CTX) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as err:
        return {'erro': err.code}
    actions = data.get('actions') or {}
    fields = actions.get('POST') or actions.get('PUT') or {}
    out = {}
    for name, meta in fields.items():
        f = {'tipo': meta.get('type'), 'obrigatorio': bool(meta.get('required')),
             'so_leitura': bool(meta.get('read_only'))}
        if meta.get('max_length'):
            f['max'] = meta['max_length']
        if meta.get('choices'):
            f['escolhas'] = [c.get('value') for c in meta['choices']]
        out[name] = f
    return {'escrita': out, 'metodos': sorted(actions)}


def capture():
    api = Api()
    say('lendo a API (raiz, OPTIONS e 1 linha de cada rota)...')
    root = api.get('') or {}
    routes = sorted({f'{name}/' for name in root} | set(EXTRA_ROUTES))
    api_part = {}
    for route in routes:
        sample = api.get(route, limit=1, page=1)
        rows = sample if isinstance(sample, list) else (sample or {}).get('results', [])
        entry = {'leitura': sorted(rows[0].keys()) if rows else [],
                 'total': None if isinstance(sample, list) else (sample or {}).get('count')}
        entry.update(options(api, route))
        api_part[route] = entry
    db = {}
    if os.path.exists(SNAPSHOT):
        con = sqlite3.connect(f'file:{SNAPSHOT}?mode=ro', uri=True)
        tables = [t for (t,) in con.execute("select name from sqlite_master where type='table' order by name")
                  if not t.startswith(('sqlite_', 'django_', 'auth_'))]
        db['tabelas'] = {t: [r[1] for r in con.execute(f'pragma table_info("{t}")')] for t in tables}
        db['migracoes'] = [f'{a}.{n}' for a, n in con.execute(
            "select app, name from django_migrations where app not in ('admin','auth','contenttypes','sessions') "
            'order by applied')]
        db['snapshot'] = datetime.fromtimestamp(os.path.getmtime(SNAPSHOT), BRT).strftime('%d/%m/%Y %H:%M')
        con.close()
    return {'capturado': datetime.now(BRT).strftime('%d/%m/%Y %H:%M (BRT)'), 'raiz_api': sorted(root),
            'api': api_part, 'banco': db}


def load():
    try:
        return json.load(open(CONTRACT, encoding='utf-8'))
    except (OSError, ValueError):
        return None


def save(contract):
    with open(CONTRACT, 'w', encoding='utf-8') as f:
        json.dump(contract, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write('\n')
    say(f'contrato salvo em {os.path.relpath(CONTRACT, ROOT)} ({contract["capturado"]})')


def codeFiles():
    for base in CODE_DIRS:
        for root, dirs, names in os.walk(os.path.join(ROOT, base)):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for n in names:
                if n.endswith(('.py', '.md')) and n != 'contrato.py':
                    yield os.path.join(root, n)


def usages(term, route=False):
    """arquivo:linha que citam a rota (`suntechs`) ou o campo entre aspas (`'chip'`)."""
    pat = re.compile(rf'\b{re.escape(term.strip("/"))}\b' if route else rf'[\'"]{re.escape(term)}[\'"]')
    hits = []
    for path in codeFiles():
        try:
            for i, line in enumerate(open(path, encoding='utf-8', errors='replace'), 1):
                if pat.search(line):
                    hits.append(f'{os.path.relpath(path, ROOT)}:{i}')
        except OSError:
            pass
    return hits


def show(hits, limit=8):
    if hits:
        say('      usado em: ' + ', '.join(hits[:limit]) + (f' … (+{len(hits) - limit})' if len(hits) > limit else ''))


def diff(old, new):
    """lista o que mudou; devolve quantas mudanças achou."""
    n = 0
    say(f"\ncontrato salvo: {old['capturado']} | servidor agora: {new['capturado']}")
    o_api, n_api = old.get('api', {}), new.get('api', {})
    for route in sorted(set(n_api) - set(o_api)):
        n += 1
        say(f'+ rota nova: {route}  leitura={n_api[route].get("leitura")}')
    for route in sorted(set(o_api) - set(n_api)):
        n += 1
        say(f'- rota SUMIU: {route}')
        show(usages(route, route=True))
    for route in sorted(set(o_api) & set(n_api)):
        o, c = o_api[route], n_api[route]
        lines = []
        for f in sorted(set(c.get('leitura', [])) - set(o.get('leitura', []))):
            lines.append((f'+ campo de leitura novo: {f}', None))
        for f in sorted(set(o.get('leitura', [])) - set(c.get('leitura', []))):
            lines.append((f'- campo de leitura SUMIU: {f}', f))
        ow, cw = o.get('escrita', {}), c.get('escrita', {})
        for f in sorted(set(cw) - set(ow)):
            lines.append((f'+ campo de escrita novo: {f} {cw[f]}', None))
        for f in sorted(set(ow) - set(cw)):
            lines.append((f'- campo de escrita SUMIU: {f}', f))
        for f in sorted(set(ow) & set(cw)):
            if ow[f] != cw[f]:
                changed = {k: (ow[f].get(k), cw[f].get(k)) for k in set(ow[f]) | set(cw[f]) if ow[f].get(k) != cw[f].get(k)}
                lines.append((f'~ campo de escrita mudou: {f} ' + ', '.join(f'{k}: {a!r} → {b!r}' for k, (a, b) in changed.items()), f))
        if o.get('metodos') != c.get('metodos'):
            lines.append((f"~ métodos: {o.get('metodos')} → {c.get('metodos')}", None))
        if lines:
            say(f'\n{route}')
            for text, field in lines:
                n += 1
                say(f'   {text}')
                if field:
                    show(usages(field))
    o_db, n_db = old.get('banco', {}).get('tabelas', {}), new.get('banco', {}).get('tabelas', {})
    if o_db and n_db:
        for t in sorted(set(n_db) - set(o_db)):
            n += 1
            say(f'+ tabela nova: {t} {n_db[t]}')
        for t in sorted(set(o_db) - set(n_db)):
            n += 1
            say(f'- tabela SUMIU: {t}')
        for t in sorted(set(o_db) & set(n_db)):
            add, rem = sorted(set(n_db[t]) - set(o_db[t])), sorted(set(o_db[t]) - set(n_db[t]))
            if add or rem:
                n += 1
                say(f'~ {t}: ' + ' '.join([f'+{c}' for c in add] + [f'-{c}' for c in rem]))
        migs = [m for m in new['banco'].get('migracoes', []) if m not in old['banco'].get('migracoes', [])]
        for m in migs:
            n += 1
            say(f'+ migração nova: {m}')
    elif n_db and not o_db:
        say('(o contrato salvo não tinha o banco: só a API foi comparada)')
    else:
        say('(sem snapshot do banco: rode `servidor.py snapshot` para comparar tabelas e migrações)')
    say(f'\n{n} mudança(s).' if n else '\nnada mudou desde o contrato salvo.')
    return n


def writable(name):
    """WRITABLE do Helper lido do código-fonte (sem importar: o Helper depende de requests)."""
    src = open(os.path.join(ROOT, 'Helper', 'tools', 'api.py'), encoding='utf-8').read()
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, 'id', '') == 'WRITABLE' for t in node.targets):
            return sorted(ast.literal_eval(node.value).get(name, []))
    return []


def verify(contract):
    missing = 0
    say(f"\nverificando o que as IAs usam contra o servidor de {contract['capturado']}:")
    for route, use in USO.items():
        entry = contract['api'].get(route)
        if not entry:
            missing += 1
            say(f'  FALTA a rota {route} (usada por: {", ".join(use.get("le", {}) | use.get("grava", {}))})')
            continue
        read, write = set(entry.get('leitura', [])), entry.get('escrita', {})
        for who, fields in use.get('le', {}).items():
            gone = [f for f in fields if f not in read]
            if gone and read:
                missing += 1
                say(f'  FALTA em {route} (leitura) para {who}: {", ".join(gone)}')
        for who, fields in use.get('grava', {}).items():
            if isinstance(fields, str):
                fields = writable(fields.split(':', 1)[1])
            gone = [f for f in fields if f not in write or write[f].get('so_leitura')]
            if gone:
                missing += 1
                say(f'  FALTA em {route} (escrita) para {who}: {", ".join(gone)}')
    say('  tudo o que as IAs usam existe na API.' if not missing else f'  {missing} problema(s) — ver docs/migracao_servidor.md')
    return missing


def usageTable():
    say('| rota | campo | leitura | escrita |\n|---|---|---|---|')
    for route, use in USO.items():
        fields = {}
        for kind in ('le', 'grava'):
            for who, names in use.get(kind, {}).items():
                if isinstance(names, str):
                    names = writable(names.split(':', 1)[1])
                for f in names:
                    fields.setdefault(f, {'le': [], 'grava': []})[kind].append(who)
        for f, w in sorted(fields.items()):
            say(f"| `{route}` | `{f}` | {'; '.join(w['le'])} | {'; '.join(w['grava'])} |")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd')
    d = sub.add_parser('diferenca')
    d.add_argument('--salvar', action='store_true', help='depois de comparar, grava o atual como referência')
    sub.add_parser('verificar')
    sub.add_parser('capturar')
    sub.add_parser('uso')
    args = p.parse_args()
    cmd = args.cmd or 'diferenca'
    if cmd == 'uso':
        usageTable()
        return 0
    live = capture()
    if cmd == 'capturar':
        save(live)
        return 0
    if cmd == 'verificar':
        return 1 if verify(live) else 0
    old = load()
    if not old:
        say('não há contrato salvo: gravando o atual como referência')
        save(live)
        return 0
    changes = diff(old, live)
    problems = verify(live)
    if getattr(args, 'salvar', False):
        save(live)
    elif changes:
        say('quando terminar a migração: `python docs/tools/contrato.py capturar` grava este como referência')
    return 1 if (changes or problems) else 0


if __name__ == '__main__':
    sys.exit(main())
