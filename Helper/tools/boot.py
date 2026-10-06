#!/usr/bin/env python3
"""
boot.py — bootstrap das IAs Sighir. O MESMO arquivo existe em Tester/, Server/ e Helper/
(cada pasta é independente); o que muda entre elas está em tools/ai.json.

    python tools/boot.py start claude|gemini [--dry-run] [--sem-prompt]
        prepara tudo e abre o agente (é o que os .exe e o start.sh chamam)
    python tools/boot.py setup [--forcar]
        só prepara: .venv, dependências, ferramentas do sistema, índice da base docs/
    python tools/boot.py hook claude|gemini
        verificação rápida no início de cada sessão (SessionStart do Claude,
        PreInvocation do AGY) — injeta no contexto o estado do ambiente
    python tools/boot.py status
        mostra o último relatório (.sighir/boot.json)

Só usa a biblioteca padrão: roda antes de qualquer dependência existir.
"""

import os
import re
import sys
import json
import time
import shutil
import signal
import socket
import hashlib
import platform
import tempfile
import argparse
import subprocess

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

TOOLS     = os.path.dirname(os.path.realpath(__file__))
ROOT      = os.path.dirname(TOOLS)
STATE     = os.path.join(ROOT, '.sighir')
BOOT_JSON = os.path.join(STATE, 'boot.json')
LOCK      = os.path.join(STATE, 'boot.lock')
IS_WIN    = os.name == 'nt'
VENV      = os.path.join(ROOT, '.venv')
VENV_BIN  = os.path.join(VENV, 'Scripts' if IS_WIN else 'bin')
VENV_PY   = os.path.join(VENV_BIN, 'python.exe' if IS_WIN else 'python')
FRESH     = 12 * 3600
API_HOST  = ('sighir.com', 8000)

DEFAULTS = {
    'id': os.path.basename(ROOT).lower(),
    'nome': 'Sighir AI',
    'requirements': 'requirements.txt',
    'imports': [],
    'extras': [],
    'claude': {'model': 'claude-sonnet-5', 'effort': 'high'},
    'gemini': {'model': 'auto-pro-high', 'fallback': 'gemini-3.1-pro-high'},
    'prompt_inicial': 'Olá! Inicie a sessão.',
}


def loadCfg():
    try:
        with open(os.path.join(TOOLS, 'ai.json'), encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = {}
    cfg = dict(DEFAULTS)
    cfg.update(data)
    return cfg


CFG = loadCfg()


# ----------------------------------------------------------------- saída

class Out:
    """No modo interativo imprime com cor; no modo hook fica mudo (o stdout é do agente)."""

    COLORS = {'ok': '32', 'aviso': '33', 'erro': '31', 'info': '36', 'passo': '1;37'}

    def __init__(self, live):
        self.live = live
        if live and IS_WIN:
            os.system('')  # liga as sequências ANSI no console do Windows

    def __call__(self, tag, msg):
        if not self.live:
            return
        label = {'ok': ' OK ', 'aviso': 'AVISO', 'erro': 'ERRO', 'info': ' .. ', 'passo': '>>'}.get(tag, tag)
        color = self.COLORS.get(tag, '0')
        if sys.stdout.isatty():
            print(f'\033[{color}m[{label}]\033[0m {msg}', flush=True)
        else:
            print(f'[{label}] {msg}', flush=True)


def run(cmd, timeout=600, live=False, env=None, cwd=None):
    """(código, saída). live=True deixa o processo usar o console (instaladores)."""
    env = dict(env if env is not None else os.environ)
    env.setdefault('PYTHONIOENCODING', 'utf-8')  # filhos Python falam UTF-8 no pipe (Windows usa cp1252)
    try:
        if live:
            return subprocess.call(cmd, timeout=timeout, env=env, cwd=cwd), ''
        res = subprocess.run(cmd, capture_output=True, timeout=timeout, env=env, cwd=cwd,
                             stdin=subprocess.DEVNULL)
        text = (res.stdout or b'').decode('utf-8', 'replace') + (res.stderr or b'').decode('utf-8', 'replace')
        return res.returncode, text
    except FileNotFoundError:
        return 127, f'não encontrado: {cmd[0]}'
    except subprocess.TimeoutExpired:
        return 124, f'tempo esgotado ({timeout}s): {" ".join(map(str, cmd))[:120]}'
    except OSError as err:
        return 126, str(err)


def which(name):
    return shutil.which(name)


def prependPath(folder):
    if folder and os.path.isdir(folder) and folder not in os.environ.get('PATH', '').split(os.pathsep):
        os.environ['PATH'] = folder + os.pathsep + os.environ.get('PATH', '')


def home(*parts):
    return os.path.join(os.path.expanduser('~'), *parts)


def loadJson(path, default=None):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def saveJson(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


class Lock:
    """evita dois pip install simultâneos no mesmo .venv (duas sessões abrindo juntas)."""

    def __enter__(self):
        os.makedirs(STATE, exist_ok=True)
        deadline = time.time() + 600
        while True:
            try:
                self.fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(self.fd, str(os.getpid()).encode())
                return self
            except FileExistsError:
                try:
                    if time.time() - os.path.getmtime(LOCK) > 900:
                        os.remove(LOCK)
                        continue
                except OSError:
                    continue
                if time.time() > deadline:
                    self.fd = None
                    return self
                time.sleep(1)

    def __exit__(self, *exc):
        if self.fd is not None:
            os.close(self.fd)
            try:
                os.remove(LOCK)
            except OSError:
                pass


# ----------------------------------------------------------------- ambiente

def docsDir():
    candidates = [os.environ.get('SIGHIR_DOCS'), os.path.join(ROOT, '..', 'docs'),
                  os.path.join(ROOT, '..', 'Docs'), os.path.join(ROOT, 'docs')]
    for cand in candidates:
        if cand and os.path.isfile(os.path.join(cand, 'tools', 'kb.py')):
            return os.path.abspath(cand)
    for cand in candidates[1:]:
        if os.path.isdir(cand):
            return os.path.abspath(cand)
    return None


def isAdmin():
    try:
        if IS_WIN:
            import ctypes
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        return os.geteuid() == 0
    except Exception:
        return False


def detect():
    info = {'so': platform.system(), 'release': platform.release(), 'arch': platform.machine(),
            'python': platform.python_version(), 'python_exe': sys.executable, 'admin': isAdmin()}
    if info['so'] == 'Linux':
        try:
            data = dict(re.findall(r'^(\w+)="?([^"\n]*)"?', open('/etc/os-release').read(), re.M))
            info['distro'] = data.get('PRETTY_NAME') or data.get('NAME')
            info['distro_id'] = ' '.join(filter(None, [data.get('ID'), data.get('ID_LIKE')]))
        except OSError:
            pass
    elif IS_WIN:
        info['distro'] = f'Windows {platform.release()} ({platform.version()})'
    elif info['so'] == 'Darwin':
        info['distro'] = f'macOS {platform.mac_ver()[0]}'
    info['gerenciadores'] = [m for m in ('winget', 'choco', 'scoop', 'apt-get', 'dnf', 'yum', 'pacman',
                                         'zypper', 'apk', 'brew') if which(m)]
    return info


def online(host, port, timeout=4):
    start = time.time()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return int((time.time() - start) * 1000)
    except OSError:
        return None


def sudoPrefix():
    if IS_WIN or isAdmin():
        return []
    return ['sudo'] if which('sudo') else None


def systemInstall(packages, out, interactive):
    """instala pacotes do sistema no Linux/macOS (pede senha do sudo no console)."""
    if not interactive:
        return False
    pre = sudoPrefix()
    if pre is None:
        out('aviso', f'sem sudo para instalar {", ".join(packages)}')
        return False
    managers = [('apt-get', ['apt-get', 'install', '-y']), ('dnf', ['dnf', 'install', '-y']),
                ('yum', ['yum', 'install', '-y']), ('pacman', ['pacman', '-S', '--noconfirm']),
                ('zypper', ['zypper', '--non-interactive', 'install']), ('apk', ['apk', 'add'])]
    for name, base in managers:
        if which(name):
            out('info', f'instalando {" ".join(packages)} via {name} (pode pedir a senha do sudo)')
            if name == 'apt-get':
                run(pre + ['apt-get', 'update', '-qq'], timeout=600, live=True)
            code, _ = run(pre + base + packages, timeout=1200, live=True)
            return code == 0
    if which('brew'):
        code, _ = run(['brew', 'install'] + packages, timeout=1200, live=True)
        return code == 0
    out('aviso', f'nenhum gerenciador de pacotes conhecido para instalar {", ".join(packages)}')
    return False


# ----------------------------------------------------------------- python e dependências

def venvOk():
    if not os.path.isfile(VENV_PY):
        return False
    code, _ = run([VENV_PY, '-c', 'import sys'], timeout=60)
    return code == 0


def ensureVenv(out, interactive):
    if venvOk():
        return True
    if os.path.isdir(VENV):
        shutil.rmtree(VENV, ignore_errors=True)
    out('info', f'criando ambiente virtual em {os.path.relpath(VENV, ROOT)}')
    code, text = run([sys.executable, '-m', 'venv', VENV], timeout=600)
    if code == 0 and venvOk():
        return True
    if platform.system() == 'Linux':
        minor = f'{sys.version_info[0]}.{sys.version_info[1]}'
        shutil.rmtree(VENV, ignore_errors=True)
        if systemInstall([f'python{minor}-venv'], out, interactive) or systemInstall(['python3-venv'], out, interactive):
            code, text = run([sys.executable, '-m', 'venv', VENV], timeout=600)
            if code == 0 and venvOk():
                return True
    shutil.rmtree(VENV, ignore_errors=True)
    out('aviso', 'não deu para criar o .venv — usando o Python do sistema '
                 f'({text.strip().splitlines()[-1][:120] if text.strip() else "sem detalhe"})')
    return False


def requirementsPath():
    return os.path.join(ROOT, CFG.get('requirements') or 'requirements.txt')


def depsSignature(py):
    h = hashlib.sha1()
    try:
        h.update(open(requirementsPath(), 'rb').read())
    except OSError:
        pass
    h.update(py.encode())
    h.update(platform.python_version().encode())
    return h.hexdigest()


def importsOk(py):
    names = CFG.get('imports') or []
    if not names:
        return True, ''
    code, text = run([py, '-c', 'import ' + ', '.join(names)], timeout=120)
    return code == 0, text.strip().splitlines()[-1] if text.strip() else ''


def pip(py, args, system, timeout=1200):
    base = [py, '-m', 'pip', 'install', '--disable-pip-version-check', '--no-input', '-q'] + args
    if system and not os.environ.get('CONDA_DEFAULT_ENV'):
        base.append('--user')
    code, text = run(base, timeout=timeout)
    if code != 0 and 'externally-managed' in text:
        code, text = run(base + ['--break-system-packages'], timeout=timeout)
    return code == 0, text


def ensureDeps(out, interactive, force=False):
    """devolve (python_do_projeto, ok, faltando)."""
    useVenv = ensureVenv(out, interactive)
    py = VENV_PY if useVenv else sys.executable
    stamp = os.path.join(STATE, 'deps.json')
    sig = depsSignature(py)
    saved = loadJson(stamp, {}) or {}
    good, detail = importsOk(py)
    if not force and saved.get('sig') == sig and good:
        return py, True, []

    if not os.path.isfile(requirementsPath()):
        return py, good, [] if good else [detail]

    code, _ = run([py, '-m', 'pip', '--version'], timeout=120)
    if code != 0:
        run([py, '-m', 'ensurepip', '--upgrade'], timeout=600)
    out('info', 'instalando dependências Python (requirements.txt)')
    ok, text = pip(py, ['-r', requirementsPath()], system=not useVenv)
    good, detail = importsOk(py)
    if ok and good:
        saveJson(stamp, {'sig': sig, 'quando': time.strftime('%Y-%m-%d %H:%M:%S')})
        out('ok', 'dependências instaladas')
        return py, True, []
    lines = [l for l in text.strip().splitlines() if l.strip()]
    reason = detail or (lines[-1] if lines else 'pip falhou')
    out('erro', f'dependências com problema: {reason[:200]}')
    return py, False, [reason[:200]]


# ----------------------------------------------------------------- ferramentas do sistema

def gitBash():
    candidates = []
    git = which('git')
    if git:
        base = os.path.dirname(os.path.dirname(os.path.realpath(git)))
        candidates += [os.path.join(base, 'bin', 'bash.exe'), os.path.join(base, 'usr', 'bin', 'bash.exe')]
    for env in ('ProgramFiles', 'ProgramFiles(x86)', 'LOCALAPPDATA'):
        base = os.environ.get(env)
        if base:
            candidates += [os.path.join(base, 'Git', 'bin', 'bash.exe'),
                           os.path.join(base, 'Programs', 'Git', 'bin', 'bash.exe')]
    for cand in candidates:
        if os.path.isfile(cand):
            return cand
    return None


def ensureGit(out, interactive):
    """o Claude Code no Windows precisa do Git Bash."""
    if not IS_WIN:
        return True
    bash = gitBash()
    if bash:
        os.environ.setdefault('CLAUDE_CODE_GIT_BASH_PATH', bash)
        return True
    if interactive and which('winget'):
        out('info', 'instalando o Git for Windows (necessário para o Claude Code)')
        run(['winget', 'install', '--id', 'Git.Git', '-e', '--silent', '--accept-package-agreements',
             '--accept-source-agreements'], timeout=1800, live=True)
        for folder in (r'C:\Program Files\Git\cmd', r'C:\Program Files\Git\bin'):
            prependPath(folder)
        bash = gitBash()
        if bash:
            os.environ['CLAUDE_CODE_GIT_BASH_PATH'] = bash
            return True
    out('erro', 'Git for Windows não encontrado — instale em https://git-scm.com/download/win')
    return False


def pdfTool():
    if which('pdftotext'):
        return which('pdftotext')
    bash = gitBash() if IS_WIN else None
    if bash:
        cand = os.path.join(os.path.dirname(os.path.dirname(bash)), 'mingw64', 'bin', 'pdftotext.exe')
        if os.path.isfile(cand):
            return cand
    return None


def ensureExtras(py, out, interactive, report):
    extras = CFG.get('extras') or []
    system = platform.system()
    if 'serial' in extras and system == 'Linux':
        try:
            import grp
            groups = {grp.getgrgid(g).gr_name for g in os.getgroups()}
        except Exception:
            groups = set()
        wanted = 'uucp' if 'arch' in (report.get('ambiente', {}).get('distro_id') or '') else 'dialout'
        if wanted not in groups and not isAdmin():
            msg = (f'usuário fora do grupo {wanted}: a porta serial vai negar acesso. '
                   f'Rode: sudo usermod -aG {wanted} $USER  e faça logout/login')
            out('aviso', msg)
            report['avisos'].append(msg)
    if 'serial' in extras:
        code, text = run([py, '-c', 'import serial.tools.list_ports as l; '
                          'print("\\n".join(p.device + "=" + (p.description or "") for p in l.comports()))'],
                         timeout=60)
        ports = [l.strip() for l in text.splitlines() if '=' in l] if code == 0 else []
        usb = [p for p in ports if 'usb' in p.lower()]
        other = [p.split('=')[0] for p in ports if p not in usb]
        if usb:
            report['portas_serial'] = '; '.join(usb) + (f' (outras, não-USB: {", ".join(other)})' if other else '')
            out('ok', f'porta USB (provável etilômetro): {"; ".join(usb)}')
        else:
            report['portas_serial'] = 'nenhuma USB conectada' + (f' (só {", ".join(other)}, não-USB)' if other else '')
            out('info', 'nenhuma porta serial USB agora (conecte o etilômetro pelo USB quando for usar)'
                + (f' — vistas: {", ".join(other)} (Bluetooth/outras)' if other else ''))
    if not pdfTool():
        if system == 'Linux' and interactive and which('apt-get'):
            systemInstall(['poppler-utils'], out, interactive)
        if not pdfTool():
            report['avisos'].append('pdftotext ausente: PDFs da base são lidos pelo pypdf (mais lento)')


def refreshDocs(py, out):
    docs = docsDir()
    if not docs:
        return {'ok': False, 'motivo': 'pasta docs/ não encontrada ao lado desta pasta'}
    kb = os.path.join(docs, 'tools', 'kb.py')
    if not os.path.isfile(kb):
        return {'ok': False, 'pasta': docs, 'motivo': 'docs/tools/kb.py ausente'}
    code, text = run([py, kb, 'atualizar', '--json'], timeout=900)
    info = {'ok': code == 0, 'pasta': docs}
    try:
        info.update(json.loads(text.strip().splitlines()[-1]))
    except (ValueError, IndexError):
        info['ok'] = False
        info['motivo'] = text.strip().splitlines()[-1][:200] if text.strip() else 'kb.py falhou'
    return info


# ----------------------------------------------------------------- setup

def setup(interactive=True, force=False):
    out = Out(interactive)
    report = {'ai': CFG['id'], 'nome': CFG['nome'], 'quando': time.strftime('%Y-%m-%d %H:%M:%S'),
              'avisos': [], 'erros': []}
    with Lock():
        env = detect()
        report['ambiente'] = env
        out('passo', f"{CFG['nome']} — preparando o ambiente")
        out('info', f"{env.get('distro') or env['so']} | {env['arch']} | Python {env['python']}")
        if sys.version_info < (3, 9):
            report['erros'].append(f'Python {env["python"]} é antigo demais (mínimo 3.9)')
            out('erro', report['erros'][-1])

        py, ok, missing = ensureDeps(out, interactive, force)
        report['python_projeto'] = py
        report['venv'] = py == VENV_PY
        report['deps_ok'] = ok
        if missing:
            report['erros'].append('dependências: ' + '; '.join(missing))
        elif ok:
            out('ok', f"Python do projeto: {os.path.relpath(py, ROOT) if report['venv'] else py}")

        ensureExtras(py, out, interactive, report)

        ms = online(*API_HOST)
        report['servidor'] = {'online': ms is not None, 'ms': ms}
        if ms is None:
            report['avisos'].append('servidor sighir.com:8000 inacessível agora (sem internet ou servidor fora)')
            out('aviso', report['avisos'][-1])
        else:
            out('ok', f'servidor sighir.com:8000 alcançável ({ms} ms)')

        docs = refreshDocs(py, out)
        report['docs'] = docs
        if docs.get('ok'):
            extra = f", {docs['pendentes']} pendente(s) de revisão" if docs.get('pendentes') else ''
            out('ok', f"base de conhecimento: {docs.get('arquivos')} arquivos indexados{extra}")
        else:
            report['avisos'].append('base docs/: ' + docs.get('motivo', 'indisponível'))
            out('aviso', report['avisos'][-1])

        saveJson(BOOT_JSON, report)
    return report


# ----------------------------------------------------------------- agentes

def findClaude():
    found = which('claude')
    if found:
        return found
    for cand in (home('.local', 'bin', 'claude.exe' if IS_WIN else 'claude'),
                 home('.claude', 'local', 'claude.exe' if IS_WIN else 'claude'),
                 os.path.join(os.environ.get('APPDATA', ''), 'npm', 'claude.cmd'),
                 '/usr/local/bin/claude', '/opt/homebrew/bin/claude'):
        if cand and os.path.isfile(cand):
            prependPath(os.path.dirname(cand))
            return cand
    return None


def findAgy():
    found = which('agy')
    if found:
        return found
    for cand in (os.path.join(os.environ.get('LOCALAPPDATA', ''), 'agy', 'bin', 'agy.exe'),
                 home('.local', 'bin', 'agy'), '/usr/local/bin/agy', '/opt/homebrew/bin/agy'):
        if cand and os.path.isfile(cand):
            prependPath(os.path.dirname(cand))
            return cand
    return None


INSTALLERS = {
    'claude': ('https://claude.ai/install.ps1', 'https://claude.ai/install.sh'),
    'gemini': ('https://antigravity.google/cli/install.ps1', 'https://antigravity.google/cli/install.sh'),
}


def ensureAgent(agent, out, interactive):
    finder = findClaude if agent == 'claude' else findAgy
    exe = finder()
    if exe:
        return exe
    if not interactive:
        return None
    label = 'Claude Code' if agent == 'claude' else 'Antigravity CLI (agy)'
    ps1, sh = INSTALLERS[agent]
    out('info', f'{label} não encontrado — instalando pelo instalador oficial')
    if IS_WIN:
        run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command',
             f'[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; irm {ps1} | iex'],
            timeout=1800, live=True)
    else:
        if not which('curl'):
            systemInstall(['curl'], out, interactive)
        run(['bash', '-c', f'curl -fsSL {sh} | bash'], timeout=1800, live=True)
    prependPath(home('.local', 'bin'))
    if IS_WIN and agent == 'gemini':
        prependPath(os.path.join(os.environ.get('LOCALAPPDATA', ''), 'agy', 'bin'))
    exe = finder()
    if exe:
        out('ok', f'{label} instalado: {exe}')
    else:
        out('erro', f'não consegui instalar o {label}. Instale manualmente ({ps1 if IS_WIN else sh}) e abra de novo.')
    return exe


def trustAgy(out):
    """o AGY só carrega regras/hooks do workspace em pastas confiáveis: marca esta pasta."""
    path = home('.gemini', 'antigravity-cli', 'settings.json')
    data = loadJson(path, {}) if os.path.exists(path) else {}
    if not isinstance(data, dict):
        return
    target = os.path.normpath(ROOT)
    current = data.get('trustedWorkspaces') or []
    if any(os.path.normcase(os.path.normpath(p)) == os.path.normcase(target) for p in current):
        return
    try:
        if os.path.exists(path) and not os.path.exists(path + '.sighir-bak'):
            shutil.copy2(path, path + '.sighir-bak')
        data['trustedWorkspaces'] = current + [target]
        saveJson(path, data)
        out('ok', f'AGY: pasta marcada como confiável ({target})')
    except OSError as err:
        out('aviso', f'AGY: não consegui marcar a pasta como confiável ({err})')


def agyModel(agy, out):
    """escolhe o Gemini Pro (High) mais novo que o `agy models` oferecer. Devolve (id, rótulo)."""
    wanted = (CFG.get('gemini') or {}).get('model', 'auto-pro-high')
    fallback = (CFG.get('gemini') or {}).get('fallback', 'gemini-3.1-pro-high')
    if not wanted.startswith('auto'):
        return wanted, None
    cache = os.path.join(STATE, 'agy_models.json')
    saved = loadJson(cache, {}) or {}
    models = saved.get('models') if time.time() - saved.get('ts', 0) < 86400 else None
    if not models:
        code, text = run([agy, 'models'], timeout=120, cwd=tempfile.gettempdir())
        models = re.findall(r'^\s*(gemini-[\w.\-]+)\s+(.+?)\s*$', text, re.M) if code == 0 else []
        if models:
            saveJson(cache, {'ts': time.time(), 'models': models})
    best = None
    for model, label in models or []:
        m = re.match(r'^gemini-(\d+(?:\.\d+)*)-pro-high$', model)
        if m:
            version = tuple(int(x) for x in m.group(1).split('.'))
            if best is None or version > best[0]:
                best = (version, model, label)
    return (best[1], best[2]) if best else (fallback, None)


def agyDefaultModel(label, out):
    """o --model do AGY falha se o login estiver vencido na hora de abrir (resolve antes de autenticar)
    e ele cai no modelo padrão. Então, se não houver padrão, gravo o Pro High como padrão."""
    if not label:
        return
    path = home('.gemini', 'antigravity-cli', 'settings.json')
    data = loadJson(path, {}) if os.path.exists(path) else {}
    if not isinstance(data, dict) or data.get('model'):
        return
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if os.path.exists(path) and not os.path.exists(path + '.sighir-bak'):
            shutil.copy2(path, path + '.sighir-bak')
        data['model'] = label
        saveJson(path, data)
        out('ok', f'AGY: modelo padrão definido como {label}')
    except OSError as err:
        out('aviso', f'AGY: não consegui definir o modelo padrão ({err})')


def start(agent, dry=False, noprompt=False):
    report = setup(interactive=True)
    out = Out(True)
    if agent == 'claude':
        ensureGit(out, True)
    exe = ensureAgent(agent, out, True)
    if not exe:
        return 3

    docs = docsDir()
    env = dict(os.environ)
    # aberto de dentro de outra sessão (terminal do Claude Code/VS Code/AGY): sem isto o agente novo se
    # comporta como sessão filha (não salva transcrição, herda esforço, etc.)
    for key in list(env):
        if key in ('CLAUDECODE', 'CLAUDE_PID', 'CLAUDE_EFFORT', 'ANTIGRAVITY_CONVERSATION_ID') or \
           (key.startswith('CLAUDE_CODE_') and key not in ('CLAUDE_CODE_GIT_BASH_PATH', 'CLAUDE_CODE_USE_BEDROCK',
                                                            'CLAUDE_CODE_USE_VERTEX', 'CLAUDE_CODE_MAX_OUTPUT_TOKENS')):
            env.pop(key, None)
    if report.get('venv'):
        env['PATH'] = VENV_BIN + os.pathsep + env.get('PATH', '')
        env['VIRTUAL_ENV'] = VENV
    env['SIGHIR_AI'] = CFG['id']
    env['SIGHIR_DOCS'] = docs or ''
    env['PYTHONIOENCODING'] = 'utf-8'
    prompt = None if noprompt else CFG.get('prompt_inicial')

    if agent == 'claude':
        c = CFG.get('claude') or {}
        cmd = [exe]
        if docs:
            # --add-dir do Claude é variádico: tem que vir antes de outra opção, senão engole o prompt
            cmd += ['--add-dir', docs]
        cmd += ['--model', c.get('model', 'claude-sonnet-5'), '--effort', c.get('effort', 'high'),
                '--permission-mode', 'bypassPermissions']
        if prompt:
            cmd.append(prompt)
    else:
        trustAgy(out)
        model, label = agyModel(exe, out)
        agyDefaultModel(label, out)
        cmd = [exe, '--model', model, '--dangerously-skip-permissions']
        if docs:
            cmd += ['--add-dir', docs]
        if prompt:
            cmd += ['-i', prompt]

    out('passo', 'abrindo: ' + ' '.join(f'"{c}"' if ' ' in c else c for c in cmd))
    if dry:
        return 0
    try:
        if not IS_WIN:
            # no Linux/macOS o processo VIRA o agente: Ctrl+C e o terminal ficam todos com ele
            os.chdir(ROOT)
            os.execvpe(cmd[0], cmd, env)
        os.system(f'title {CFG["nome"]} ({"Claude" if agent == "claude" else "Gemini"})')
        # no Windows o Ctrl+C vai para todos do console: este processo só espera o agente
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        return subprocess.call(cmd, cwd=ROOT, env=env)
    except OSError as err:
        out('erro', f'falha ao abrir o agente: {err}')
        return 4


# ----------------------------------------------------------------- hook de sessão

def summary(report):
    parts = []
    env = report.get('ambiente', {})
    py = report.get('python_projeto') or sys.executable
    pyShown = os.path.relpath(py, ROOT) if report.get('venv') else py
    parts.append(f"{env.get('distro') or env.get('so', '?')} | Python {env.get('python', '?')} "
                 f"({'.venv' if report.get('venv') else 'sistema'})")
    parts.append('dependências OK' if report.get('deps_ok') else 'DEPENDÊNCIAS COM PROBLEMA')
    srv = report.get('servidor') or {}
    parts.append('servidor sighir.com:8000 ' + ('online' if srv.get('online') else 'INACESSÍVEL'))
    docs = report.get('docs') or {}
    if docs.get('ok'):
        d = f"base docs: {docs.get('arquivos')} arquivos"
        if docs.get('firmware'):
            d += f", firmware {docs['firmware']}"
        if docs.get('pendentes'):
            d += f", {docs['pendentes']} documento(s) novos/alterados sem revisão (kb.py novidades)"
        if docs.get('notion'):
            d += f", {docs['notion']}"
        parts.append(d)
    else:
        parts.append('base docs: ' + docs.get('motivo', 'indisponível'))
    if report.get('portas_serial') is not None:
        parts.append('portas seriais: ' + (report.get('portas_serial') or 'nenhuma agora'))
    text = (f"[{CFG['nome']} — ambiente verificado em {report.get('quando')}] " + ' | '.join(parts) + '.')
    problems = (report.get('erros') or []) + (report.get('avisos') or [])
    if problems:
        text += ' Atenção: ' + ' ; '.join(problems[:5]) + '. Resolva (ou explique ao usuário) antes de operar;' \
                ' `python tools/boot.py setup` refaz a preparação.'
    docsPath = docs.get('pasta')
    text += (f" Python do projeto: {pyShown} (as CLIs em tools/ já se re-executam nele)."
             f" Base de conhecimento: {docsPath or '../docs'} (comece por INDEX.md)."
             ' Siga o início de sessão do AGENTS.md.')
    return text


def hook(agent):
    raw = ''
    try:
        if not sys.stdin.isatty():
            raw = sys.stdin.read()
    except Exception:
        raw = ''
    payload = {}
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except ValueError:
        payload = {}

    if agent == 'gemini':
        conv = str(payload.get('conversationId') or payload.get('conversation_id') or '')
        marker = os.path.join(STATE, 'sessoes', re.sub(r'[^\w\-]', '_', conv) or 'sem-id')
        if conv and os.path.exists(marker):
            print('{}')
            return 0
        os.makedirs(os.path.dirname(marker), exist_ok=True)
        with open(marker, 'w') as f:
            f.write(time.strftime('%Y-%m-%d %H:%M:%S'))
        cleanupMarkers()

    report = loadJson(BOOT_JSON, None)
    stale = (not report or time.time() - os.path.getmtime(BOOT_JSON) > FRESH or
             not report.get('deps_ok') or
             (report.get('venv') and not os.path.isfile(VENV_PY)) or
             (loadJson(os.path.join(STATE, 'deps.json'), {}) or {}).get('sig') !=
             depsSignature(report.get('python_projeto') or VENV_PY))
    try:
        if stale:
            report = setup(interactive=False)
        else:
            report['docs'] = refreshDocs(report.get('python_projeto') or sys.executable, Out(False))
            saveJson(BOOT_JSON, report)
    except Exception as err:
        report = report or {'erros': []}
        report.setdefault('erros', []).append(f'boot.py falhou: {err}')

    text = summary(report)
    if agent == 'gemini':
        print(json.dumps({'injectSteps': [{'ephemeralMessage': text}]}, ensure_ascii=False))
    else:
        print(text)
    return 0


def cleanupMarkers():
    folder = os.path.join(STATE, 'sessoes')
    try:
        for name in os.listdir(folder):
            path = os.path.join(folder, name)
            if time.time() - os.path.getmtime(path) > 30 * 86400:
                os.remove(path)
    except OSError:
        pass


def status():
    report = loadJson(BOOT_JSON, None)
    if not report:
        print('ainda não preparado: rode  python tools/boot.py setup')
        return 1
    print(summary(report))
    return 0


def main():
    p = argparse.ArgumentParser(prog='boot', description=f"bootstrap — {CFG['nome']}")
    sub = p.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('start', help='prepara e abre o agente')
    s.add_argument('agente', choices=['claude', 'gemini', 'agy'])
    s.add_argument('--dry-run', action='store_true', help='prepara e mostra o comando, sem abrir')
    s.add_argument('--sem-prompt', action='store_true', help='abre sem a mensagem inicial automática')
    u = sub.add_parser('setup', help='só prepara o ambiente')
    u.add_argument('--forcar', action='store_true', help='reinstala as dependências')
    h = sub.add_parser('hook', help='verificação rápida de início de sessão')
    h.add_argument('agente', choices=['claude', 'gemini', 'agy'])
    sub.add_parser('status', help='último relatório')
    args = p.parse_args()

    agent = getattr(args, 'agente', None)
    agent = 'gemini' if agent == 'agy' else agent
    if args.cmd == 'start':
        try:
            code = start(agent, args.dry_run, args.sem_prompt)
        except KeyboardInterrupt:
            code = 130
        except Exception:
            import traceback
            traceback.print_exc()
            code = 9
        if code in (3, 4, 9, 130) and os.environ.get('SIGHIR_LAUNCHER') == 'exe':
            # aberto pelo .exe com duplo clique: sem isto a janela fecha antes de dar para ler o erro
            try:
                input('\n  Pressione ENTER para fechar...')
            except (EOFError, KeyboardInterrupt):
                pass
        return code
    if args.cmd == 'setup':
        report = setup(interactive=True, force=args.forcar)
        return 0 if not report.get('erros') else 2
    if args.cmd == 'hook':
        try:
            return hook(agent)
        except Exception as err:  # o hook nunca pode travar a sessão
            text = f"[{CFG['nome']}] verificação de ambiente falhou: {err}. Rode python tools/boot.py setup."
            print(json.dumps({'injectSteps': [{'ephemeralMessage': text}]}) if agent == 'gemini' else text)
            return 0
    if args.cmd == 'status':
        return status()
    return 1


if __name__ == '__main__':
    sys.exit(main())
