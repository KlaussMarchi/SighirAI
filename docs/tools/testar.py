#!/usr/bin/env python3
"""
testar.py — bateria de testes das três IAs (Tester, Server, Helper) e das ferramentas de docs/.
Procedimento completo (inclusive o roteiro manual de bancada): docs/testes.md.

    python docs/tools/testar.py              rápido: todas as suítes offline (sem rede, sem aparelho), ~1 min
    python docs/tools/testar.py --api        + produção em SÓ LEITURA: contrato, Helper, prévia do install do
                                             Tester, consulta de device (escolhe uma instalação real Suntech)
    python docs/tools/testar.py --completo   + check seco do Scanner (lê 3 meses de log: 3–4 min na 1ª do dia)
    python docs/tools/testar.py --bancada    + aparelho na USB: init/status/firmware/settings/telemetria (leitura)

Nada aqui grava no servidor nem no aparelho. O que grava (register, install --yes, telemetry <modo>, block,
flash…) está no roteiro manual de docs/testes.md §3, sempre com o ok do usuário.
Código de saída: 0 = tudo passou; 1 = alguma etapa falhou.
"""

import os
import sys
import time
import argparse
import subprocess

TOOLS = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.dirname(TOOLS)
ROOT = os.path.dirname(DOCS)
PY = sys.executable
ENV = dict(os.environ, PYTHONIOENCODING='utf-8')
results = []


def run(name, cmd, cwd, expect=(0,), must=(), mustnot=(), timeout=600):
    """roda uma etapa; passa se o código de saída está em `expect` e a saída tem `must` e não tem `mustnot`."""
    t0 = time.time()
    try:
        p = subprocess.run(cmd, cwd=cwd, env=ENV, capture_output=True, text=True, encoding='utf-8',
                           errors='replace', timeout=timeout)
        out, code = p.stdout + p.stderr, p.returncode
    except subprocess.TimeoutExpired:
        out, code = f'tempo esgotado ({timeout} s)', None
    ok = code in expect and all(m in out for m in must) and not any(m in out for m in mustnot)
    dt = time.time() - t0
    results.append((ok, name, dt))
    print(f"{'ok   ' if ok else 'FALHA'} {name}  ({dt:.0f} s)", flush=True)
    if not ok:
        tail = '\n'.join(out.strip().splitlines()[-15:])
        print('      código', code, '| esperado', expect, '| fim da saída:\n      ' + tail.replace('\n', '\n      '))
    return ok, out


def offline():
    print('\n== offline (sem rede, sem aparelho)')
    run('docs: sincronizador do Notion', [PY, 'tools/test_notion_sync.py'], DOCS, must=['todos passaram'])
    run('docs: contrato do servidor', [PY, 'tools/test_contrato.py'], DOCS, must=['todos passaram'])
    run('Server: regras e reconciliação do scanner', [PY, 'test_scan.py'], os.path.join(ROOT, 'Server', 'scanner'),
        must=['todos passaram'])
    run('Helper: comandos, checklists, travas de escrita', [PY, 'tools/test_helper.py'], os.path.join(ROOT, 'Helper'),
        must=['todos passaram'])
    run('Tester: register/install (API falsa)', [PY, 'tools/test_cli.py'], os.path.join(ROOT, 'Tester'),
        must=['todos passaram'])
    for ia in ('Tester', 'Server', 'Helper'):
        run(f'{ia}: ambiente (boot.py status)', [PY, 'tools/boot.py', 'status'], os.path.join(ROOT, ia), expect=(0, 1),
            mustnot=['Traceback'])


def reference():
    """uma instalação real Suntech com módulo, para as consultas de leitura."""
    sys.path.insert(0, TOOLS)
    from servidor import Api
    api = Api()
    for e in api.rows('etilometers/', limit=500, max_rows=500):
        if (e.get('telemetry_label') or '').upper() == 'SUNTECH' and e.get('vehicle') and e.get('esp_id'):
            dev = api.get(f"devices/{e['esp_id']}/") or {}
            if dev.get('telemetry'):
                return e['vehicle'], e['esp_id']
    return None, None


def telemetryHealth():
    """logs por telemetria: zero nas últimas 24 h numa telemetria que tinha >= 3 veículos ativos na semana =
    serviço de integração parado (MiX em 24/09/2026). Frota pequena ou parada só gera aviso."""
    from datetime import datetime, timedelta, timezone
    sys.path.insert(0, TOOLS)
    from servidor import Api
    api = Api()
    fleet = {e['vehicle']: (e.get('telemetry_label') or '').upper() for e in api.rows('etilometers/', limit=500)}
    now = datetime.now(timezone.utc)
    day = (now - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
    rows = api.rows('logs/', limit=2000, max_rows=80000,
                    start=(now - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S'), end=now.strftime('%Y-%m-%d %H:%M:%S'))
    last24, week = {}, {}
    for r in rows:
        label = fleet.get(r.get('vehicle'), '')
        group = 'MIX' if 'MIX' in label else 'SUNTECH' if 'SUNTECH' in label else 'ENTRACK' if 'ENTRACK' in label else None
        if not group:
            continue
        week.setdefault(group, set()).add(r.get('vehicle'))
        if (r.get('timestamp') or '').replace('T', ' ')[:19] >= day:
            last24[group] = last24.get(group, 0) + 1
    for group in ('MIX', 'SUNTECH', 'ENTRACK'):
        n, active = last24.get(group, 0), len(week.get(group, ()))
        bad = n == 0 and active >= 3
        results.append((not bad, f'telemetria {group}: logs chegando', 0))
        note = '' if n else (' — serviço de integração parado? (docs/migracao_servidor.md, serviços satélites)' if bad
                             else f' (aviso: frota {group} sem atividade — {active} veículo(s) ativos na semana)')
        print(f"{'FALHA' if bad else 'ok   '} telemetria {group}: {n} logs nas últimas 24 h, {active} veículos na semana{note}")


def serverServices():
    """sessões screen e processos dos serviços satélites no servidor (SSH só leitura; precisa da chave .pem)."""
    sys.path.insert(0, TOOLS)
    from servidor import findKey, HOST
    key = findKey()
    if not key:
        print('      (sem a chave .pem: serviços do servidor não conferidos)')
        return
    cmd = ('screen -ls; for d in mix telemetry-panel; do pgrep -f "python3 main.py" | while read p; do '
           'readlink /proc/$p/cwd; done; break; done; pgrep -fc gunicorn')
    try:
        p = subprocess.run(['ssh', '-i', key, '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=20', HOST, cmd],
                           capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
        out = p.stdout
    except (OSError, subprocess.TimeoutExpired) as err:
        results.append((False, 'servidor: serviços satélites (SSH)', 0))
        print(f'FALHA servidor: SSH indisponível ({err})')
        return
    checks = {'api (gunicorn)': out.strip().splitlines()[-1].strip() not in ('', '0') if out.strip() else False,
              'mix (integração MiX)': '/telemetries/mix' in out,
              'suntech (telemetry-panel)': '/telemetries/telemetry-panel' in out}
    for name, ok in checks.items():
        results.append((ok, f'servidor: serviço {name} rodando', 0))
        print(f"{'ok   ' if ok else 'FALHA'} servidor: serviço {name} rodando"
              + ('' if ok else ' — religue na sessão screen correspondente (docs/migracao_servidor.md)'))


def online(full):
    print('\n== produção, só leitura')
    run('contrato: o que as IAs usam existe na API', [PY, 'tools/contrato.py', 'verificar'], DOCS,
        must=['tudo o que as IAs usam existe na API'])
    ok, out = run('contrato: diferença desde a referência', [PY, 'tools/contrato.py', 'diferenca'], DOCS,
                  expect=(0, 1), mustnot=['Traceback'])
    if 'nada mudou' not in out:
        print('      ⚠ o servidor mudou desde o contrato salvo: siga docs/migracao_servidor.md')
    telemetryHealth()
    serverServices()
    plate, esp = reference()
    if not plate:
        results.append((False, 'referência: nenhuma instalação Suntech com módulo achada', 0))
        print('FALHA referência: nenhuma instalação Suntech com módulo')
        return
    print(f'      referência: {plate} ↔ {esp}')
    helper = os.path.join(ROOT, 'Helper')
    tester = os.path.join(ROOT, 'Tester')
    run(f'Helper: veiculo {plate}', [PY, 'tools/helper.py', 'veiculo', plate], helper,
        must=['instalação', 'módulo '], mustnot=['Traceback'])
    run(f'Helper: device {esp}', [PY, 'tools/helper.py', 'device', esp], helper,
        must=[f'instalado na placa {plate}', 'módulo '], mustnot=['Traceback'])
    run('Helper: patch sem --sim só mostra', [PY, 'tools/helper.py', 'patch', 'devices', esp, 'nickname=teste'],
        helper, expect=(3,), must=['nada foi alterado'])
    run(f'Tester: server-device {esp}', [PY, 'tools/sighir.py', 'server-device', esp], tester,
        must=['plate', plate], mustnot=['Traceback'])
    run('Tester: prévia do install (mesma placa, não grava)',
        [PY, 'tools/sighir.py', 'install', esp, '--placa', plate, '--telemetria', 'suntech'], tester,
        expect=(3,), must=['já está na placa', 'nada foi gravado'], mustnot=['Traceback'])
    run('Tester: prévia do edit (troca de empresa, não grava)',
        [PY, 'tools/sighir.py', 'edit', esp, '--company', 'logika', '--desinstalar', '--modulo', '1700099999'], tester,
        expect=(3,), must=['alterações', 'plate', 'nada foi gravado'], mustnot=['Traceback'])
    run(f'Tester: onde {esp} (onde está cadastrado)', [PY, 'tools/sighir.py', 'onde', esp], tester,
        must=['aparelho:', plate], mustnot=['Traceback'])
    run('Tester: install recusa aparelho inexistente (não grava)',
        [PY, 'tools/sighir.py', 'install', 'MIC0000000000000000', '--placa', plate, '--telemetria', 'mix2'], tester,
        expect=(1,), must=['não existe no servidor'])
    run('docs: resumo da frota (servidor.py)', [PY, 'tools/servidor.py', 'resumo'], DOCS, mustnot=['Traceback'])
    if full:
        run('Server: check seco do scanner (não escreve)', [PY, 'scan.py'], os.path.join(ROOT, 'Server', 'scanner'),
            must=['MODO SECO'], mustnot=['Traceback', 'recusado'], timeout=1200)


def bench():
    print('\n== bancada (aparelho na USB, só leitura)')
    tester = os.path.join(ROOT, 'Tester')
    ok, _ = run('Tester: init (preflight + status)', [PY, 'tools/sighir.py', 'init'], tester, mustnot=['Traceback'])
    if not ok:
        print('      sem aparelho/serial: confira o cabo e o driver (Tester/procedimentos/ambiente_arquitetura.md §2.1)')
        return
    run('Tester: firmware', [PY, 'tools/sighir.py', 'firmware'], tester, mustnot=['Traceback'])
    run('Tester: settings', [PY, 'tools/sighir.py', 'settings'], tester, mustnot=['Traceback'])
    run('Tester: telemetria (só mostra)', [PY, 'tools/sighir.py', 'telemetry'], tester, mustnot=['Traceback'])
    run('Tester: lista de testes do protocol.json', [PY, 'tools/sighir.py', 'test'], tester, mustnot=['Traceback'])
    print('      próximo passo: roteiro de gravação de docs/testes.md §3 (com o usuário)')


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--api', action='store_true', help='inclui produção em só leitura')
    p.add_argument('--completo', action='store_true', help='--api + check seco do scanner')
    p.add_argument('--bancada', action='store_true', help='inclui o aparelho na USB (leitura)')
    args = p.parse_args()
    offline()
    if args.api or args.completo:
        online(args.completo)
    if args.bancada:
        bench()
    bad = [name for ok, name, _ in results if not ok]
    print(f"\n{len(results) - len(bad)}/{len(results)} etapas passaram" + (f" — falharam: {'; '.join(bad)}" if bad else ''))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
