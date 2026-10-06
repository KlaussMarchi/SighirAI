"""
Garante que as CLIs desta pasta rodem no .venv preparado pelo tools/boot.py.

Assim `python tools/helper.py ...` funciona igual no Claude, no AGY, no Windows e no Linux,
mesmo quando o agente foi aberto direto (sem o .exe/start.sh) e o `python` do PATH é o do sistema.
"""

import os
import sys
import subprocess


def ensure(root):
    if os.environ.get('SIGHIR_NO_VENV'):
        return
    venv = os.path.join(root, '.venv')
    py = os.path.join(venv, 'Scripts', 'python.exe') if os.name == 'nt' else os.path.join(venv, 'bin', 'python')
    if not os.path.isfile(py):
        return
    if os.path.normcase(os.path.realpath(sys.prefix)) == os.path.normcase(os.path.realpath(venv)):
        return
    os.environ['SIGHIR_NO_VENV'] = '1'
    sys.stdout.flush()
    sys.stderr.flush()
    if os.name == 'nt':
        sys.exit(subprocess.call([py] + sys.argv))
    os.execv(py, [py] + sys.argv)
