import os, json
from datetime import datetime, timedelta

ROOT     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SESSIONS = os.path.join(ROOT, '.sighir', 'bancada')    # .sighir/sessoes É DO boot.py
SESSION_HOURS = 24    # O ENSAIO DE BANCADA VALE NO DIA: RESULTADO MAIS VELHO NÃO ENTRA NO RELATÓRIO DE UM CADASTRO NOVO


def sessionPath(esp):
    return os.path.join(SESSIONS, f'{esp}.json')


def load(esp):
    try:
        events = json.load(open(sessionPath(esp), encoding='utf-8'))
    except (OSError, ValueError):
        return []

    since = (datetime.now() - timedelta(hours=SESSION_HOURS)).isoformat(timespec='seconds')
    return [e for e in events if e.get('quando', '') >= since]


# CADA COMANDO QUE MEXE NO APARELHO ANOTA O QUE FEZ; O RELATÓRIO JUNTA TUDO E ARQUIVA A SESSÃO
def record(esp, kind, **data):
    if not esp:
        return

    events = load(esp) + [{'tipo': kind, 'quando': datetime.now().isoformat(timespec='seconds'), **data}]

    try:
        os.makedirs(SESSIONS, exist_ok=True)
        with open(sessionPath(esp), 'w', encoding='utf-8') as f:
            json.dump(events, f, ensure_ascii=False, indent=2)
    except OSError:
        pass
