"""
Preflight de ambiente do Sighir Tester AI.

Detecta SO/Python/ambiente (conda, venv, sistema), verifica as dependências
e instala automaticamente o que faltar — funcionando em Linux e Windows,
com ou sem virtualenv. Projetado para ser idempotente e seguro para rodar
no início de toda sessão (Claude Code ou Agy/Gemini).

Uso direto:
    python tools/preflight.py
Ou via CLI:
    python tools/sighir.py preflight
"""

import os
import sys
import time
import platform
import subprocess
import importlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAMP = os.path.join(ROOT, '.preflight_ok')
STAMP_TTL = 24 * 3600  # segundos

# (import_name, pip_name, required)
DEPENDENCIES = [
    ('serial',         'pyserial',       True),
    ('requests',       'requests',       True),
    ('prompt_toolkit', 'prompt_toolkit', True),
]


def log(tag, msg):
    colors = {'ok': '\033[32m', 'err': '\033[31m', 'info': '\033[34m',
              'warn': '\033[38;5;208m', 'reset': '\033[0m'}
    c = colors.get(tag, colors['info'])
    print(f"{c}[preflight:{tag}]{colors['reset']} {msg}")


def detectEnvironment():
    osName = platform.system()
    inVenv = (hasattr(sys, 'real_prefix') or
              (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix))
    inConda = os.environ.get('CONDA_DEFAULT_ENV') is not None
    isolated = inVenv or inConda

    log('info', f'SO: {osName} ({platform.machine()}) | Python {platform.python_version()}')
    log('info', f'Executável: {sys.executable}')

    if inConda:
        log('ok', f"Ambiente conda ativo: {os.environ.get('CONDA_DEFAULT_ENV')}")
    elif inVenv:
        log('ok', f'Virtualenv ativo: {sys.prefix}')
    else:
        log('warn', 'Sem virtualenv/conda — instalando no Python do sistema')

    return {'os': osName, 'isolated': isolated}


def isInstalled(importName):
    try:
        importlib.import_module(importName)
        return True
    except Exception:
        return False


def pipInstall(pipNames, isolated):
    """Instala pacotes lidando com PEP 668 (externally-managed) no Linux."""
    base = [sys.executable, '-m', 'pip', 'install', '-q', *pipNames]

    result = subprocess.run(base, capture_output=True, text=True)
    if result.returncode == 0:
        return True, ''

    stderr = (result.stderr or '') + (result.stdout or '')

    # Ambiente Linux gerenciado externamente (PEP 668) e sem venv/conda
    if not isolated and 'externally-managed' in stderr:
        log('warn', 'ambiente gerenciado externamente — usando --break-system-packages')
        retry = base + ['--break-system-packages']
        result = subprocess.run(retry, capture_output=True, text=True)
        if result.returncode == 0:
            return True, ''
        stderr = (result.stderr or '') + (result.stdout or '')

    return False, stderr.strip()


def stampFresh():
    """True se o preflight passou há < TTL e as obrigatórias ainda importam."""
    try:
        age = time.time() - os.path.getmtime(STAMP)
    except OSError:
        return False
    if age >= STAMP_TTL:
        return False
    return all(isInstalled(i) for i, _, req in DEPENDENCIES if req)


def run(quick=False):
    if quick and stampFresh():
        log('ok', 'preflight em cache (deps OK < 24h) — pulando checagem completa.')
        return True

    log('info', '--- Sighir Tester AI — Preflight ---')
    env = detectEnvironment()

    missingRequired = []
    missingOptional = []

    for importName, pipName, required in DEPENDENCIES:
        if isInstalled(importName):
            log('ok', f'{importName}')
        elif required:
            missingRequired.append((importName, pipName))
            log('err', f'FALTANDO (obrigatório): {importName} -> pip {pipName}')
        else:
            missingOptional.append((importName, pipName))
            log('warn', f'faltando (opcional): {importName}')

    allGood = True

    if missingRequired:
        names = [p for _, p in missingRequired]
        log('info', f'instalando obrigatórias: {", ".join(names)}')
        ok, err = pipInstall(names, env['isolated'])
        if ok:
            still = [i for i, _ in missingRequired if not isInstalled(i)]
            if still:
                log('err', f'ainda faltando após instalação: {", ".join(still)}')
                allGood = False
            else:
                log('ok', 'dependências obrigatórias satisfeitas')
        else:
            log('err', f'pip falhou: {err}')
            allGood = False

    if missingOptional:
        names = [p for _, p in missingOptional]
        log('info', f'tentando opcionais (best-effort): {", ".join(names)}')
        ok, _ = pipInstall(names, env['isolated'])
        if not ok:
            log('warn', 'opcionais não instaladas (ok em headless; core não depende delas)')

    if allGood:
        log('ok', 'AMBIENTE PRONTO — Sighir Tester AI operacional.')
        try:
            with open(STAMP, 'w') as f:
                f.write(str(int(time.time())))
        except OSError:
            pass
    else:
        log('err', 'AMBIENTE COM PROBLEMAS — resolva as dependências acima.')

    return allGood


if __name__ == '__main__':
    sys.exit(0 if run() else 1)
