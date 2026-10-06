"""
Operações robustas do Sighir Tester AI (camada reutilizável).

Envolve as classes de objects/ (Device, Server, Updater) adicionando
reconexão com retry/backoff, validação de formato e a detecção de
"firmware antigo" — sem reimplementar o protocolo. É a base usada pela
CLI (tools/sighir.py) e pode ser importada por qualquer script.

Convenções:
  - Sem type hints (padrão do projeto).
  - camelCase para métodos/variáveis, PascalCase para classes.
"""

import os
import sys
import re
from time import sleep

# garante que a raiz do projeto está no sys.path (tools/ é subpasta)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from objects.Device.index import device
from objects.Server.index import server      # noqa: F401 — reexportado (sighir.py usa core.server)
from objects.Updater.index import updater    # noqa: F401 — reexportado (sighir.py usa core.updater)
from utils.api import post_req

MIN_FIRMWARE = (6, 4, 0)
VERSION_RE   = re.compile(r'v?(\d+)\.(\d+)\.(\d+)')


def log(tag, msg):
    colors = {'ok': '\033[32m', 'err': '\033[31m', 'info': '\033[34m',
              'warn': '\033[38;5;208m', 'reset': '\033[0m'}
    c = colors.get(tag, colors['info'])
    print(f"{c}[sighir:{tag}]{colors['reset']} {msg}")


_everConnected = False


def robustConnect(retries=6, backoff=2.0):
    global _everConnected
    for attempt in range(1, retries + 1):
        # nunca conectou neste processo e não há porta candidata (nenhuma USB): o etilômetro não está
        # plugado — duas olhadas e desiste (~2 s em vez de ~24 s). A insistência longa abaixo é para a
        # porta que some e volta depois de reset/erase/flash, quando já houve conexão.
        if not _everConnected and device.port is None:
            port = device.scan()
            if port is None:
                if attempt >= 2:
                    log('err', 'nenhuma porta USB do etilômetro: confira o cabo (de dados) e o driver')
                    return False
                sleep(1.0)
                continue
            device.port = port

        device.reconnect()
        if device.device and device.device.is_open:
            _everConnected = True
            return True
        # a porta pode ter re-enumerado (ex: pós reset/erase com outro nome):
        # força re-scan na próxima tentativa
        device.port = None
        log('warn', f'falha ao abrir porta, tentativa {attempt}/{retries}')
        sleep(backoff)
    return False


def robustSync(retries=8, backoff=None):
    """Sincroniza com retry+backoff PROGRESSIVO. A 1ª sync após erase/reset/flash
    costuma falhar porque o device ainda está reiniciando — mas quando ele está
    vivo o ACK vem em ~0.3s, então não faz sentido pagar 5s de timeout + 2s de
    espera já na 1ª tentativa. Começa barato e só fica paciente se precisar."""
    if not robustConnect():
        log('err', 'sem porta serial')
        return False

    for attempt in range(1, retries + 1):
        device.reconnect()
        wait = backoff if backoff else min(0.3 * (2 ** (attempt - 1)), 3.0)

        if not (device.device and device.device.is_open):
            sleep(wait)
            continue

        device.clear()

        if device.expect(target='ETKAACK', command='$ETKA!', timeout=1.5 + attempt):
            log('ok', f'sincronizado (tentativa {attempt})')
            return True

        log('warn', f'sem ETKAACK, tentativa {attempt}/{retries}')
        sleep(wait)

    log('err', 'device não sincronizou')
    return False


def parseVersion(text):
    m = VERSION_RE.search(text or '')
    if not m:
        return None
    return tuple(int(g) for g in m.groups())


def readFirmware(retries=4):
    """Lê $firmware! e classifica.

    Retorna dict:
      {'raw': <str>, 'version': (x,y,z)|None, 'status': 'ok'|'below_min'|'old'}

    REGRA: se após N tentativas (com limpeza de buffer) a resposta vier
    vazia ou sem o formato vX.Y.Z, o firmware é ANTIGO (não suporta o
    comando) -> status 'old' -> deve-se pedir atualização ao usuário.
    """
    lastRaw = ''
    for attempt in range(1, retries + 1):
        device.clear()
        raw = device.getResponse('$firmware!')
        lastRaw = raw
        version = parseVersion(raw)
        if version:
            status = 'ok' if version >= MIN_FIRMWARE else 'below_min'
            return {'raw': raw, 'version': version, 'status': status}
        log('warn', f'firmware inválido/sem resposta ({raw!r}), tentativa {attempt}/{retries}')
        sleep(1.0)

    return {'raw': lastRaw, 'version': None, 'status': 'old'}


def versionStr(version):
    return 'v' + '.'.join(map(str, version)) if version else 'desconhecida'


EVENT_RE = re.compile(r'^ETEV\d+')
TOKEN_RE = re.compile(r'\$([^!$]*)!')


def extractValue(raw):
    """Extrai o payload de uma resposta `$<valor>!`, IGNORANDO eventos.

    Por que: a resposta do device pode vir colada a um evento assíncrono — em
    especial o `$ETEV17!`, que é a 2ª linha da resposta do `$ETKA!` da sync e
    chega ~100ms depois. Pegar "do primeiro $ até o primeiro !" devolveria
    'ETEV17' como se fosse o valor. Um valor de setting NUNCA tem forma de
    `$ETEVxx!`, então dá pra descartar com segurança e ficar com o último token
    válido (o mais recente = a resposta do comando que acabamos de mandar)."""
    if not raw:
        return None

    tokens = [token.strip() for token in TOKEN_RE.findall(raw)]
    tokens = [token for token in tokens if token and not EVENT_RE.match(token)]

    if tokens:
        return tokens[-1]

    # resposta sem $...! (ex: 'v6.4.4', 'ETL...', 'OK'): limpa eventos soltos
    cleaned = TOKEN_RE.sub(' ', raw).strip()
    return cleaned or None


def readEspId(retries=4):
    for attempt in range(1, retries + 1):
        device.clear()
        raw = device.request('ID:esp_id$', timeout=10)
        if raw and 'MIC' in raw:
            return extractValue(raw)
        # pode vir 'admin_sighir' (config sobrescrita) — também é válido como leitura
        if raw and 'admin_sighir' in raw:
            return extractValue(raw)
        log('warn', f'esp_id inválido ({raw!r}), tentativa {attempt}/{retries}')
        sleep(1.0)
    return None


def readSensorId(retries=4):
    for attempt in range(1, retries + 1):
        device.clear()
        raw = device.request('sensor_id', timeout=10)
        if raw and 'ETL' in raw:
            return extractValue(raw)
        log('warn', f'sensor_id inválido ({raw!r}), tentativa {attempt}/{retries}')
        sleep(1.0)
    return None


def isNativeId(espId):
    return bool(espId) and espId.startswith('MIC')


SETTING_KEYS = ['esp_id', 'sensor_id', 'telemetry', 'vehicle_type', 'server', 'wifi',
                'ssid', 'passwd', 'lang', 'brightness', 'volume', 'camera', 'bypass', 'blowProb',
                'enable_random', 'max_postpone', 'postpone_time', 'maneuver_time', 'time_of_travel',
                'number_of_tests', 'rand_ppn_time', 'rand_min_time', 'last_alcohol', 'last_analog',
                'temp_debug', 'press', 'testalc', 'reset']

TELEMETRIES = {'mix': 0, 'suntech': 2, 'mix2': 5, 'entrack': 6}


def readSetting(key, timeout=6.0, retries=3):
    """Lê uma setting do NVS (`ID:<key>$` -> `$<value>!`).

    Usa extractValue() (não `request()`): settings curtas como `$6!` são válidas,
    e a resposta pode vir grudada num `$ETEV17!` remanescente da sync."""
    for attempt in range(1, retries + 1):
        device.clear()
        device.send(f'ID:{key}$')
        value = extractValue(device.get(timeout=timeout))

        if value:
            return value

        log('warn', f'sem resposta para ID:{key}$, tentativa {attempt}/{retries}')
        sleep(0.3)

    return None


def readSettings(keys=None):
    return {key: readSetting(key) for key in (keys or SETTING_KEYS)}


def writeSetting(key, value, timeout=8.0):
    """Grava uma setting (`CF:<key>$<value>!` -> `OK`)."""
    device.clear()
    ok = device.expect(target='OK', command=f'CF:{key}${value}!', timeout=timeout)

    if not ok:
        log('err', f'device não confirmou CF:{key}${value}!')
        return False

    log('ok', f'{key} = {value}')
    return True


def restart(wait=3.0):
    """Reinicia o device e ressincroniza."""
    log('info', 'reiniciando ($ETRS!)')
    device.send('$ETRS!')
    device.disconnect()
    sleep(wait)
    return robustSync(retries=10)


def setTelemetry(mode):
    """Configura o modo de telemetria e REINICIA — o firmware só lê a setting
    `telemetry` no boot (Telemetry::setup())."""
    if mode not in TELEMETRIES:
        log('err', f'modo inválido: {mode!r} (use {", ".join(TELEMETRIES)})')
        return False

    value = TELEMETRIES[mode]
    if mode == 'mix':
        log('warn', 'mix = MIX ANTIGO (0). A maior parte da frota MiX é MIX 2.0 (mix2 = 5): confira no '
                    'cadastro (telemetry_label "MIX TELEMATICS (NOVO)" → mix2) antes de seguir')

    if not writeSetting('telemetry', value):
        return False

    if not restart():
        return False

    current = readSetting('telemetry')
    ok = (str(current) == str(value))
    log('ok' if ok else 'err', f'telemetry = {current!r} ({mode}) — esperado {value}')
    return ok


def setBlock(blocked):
    """Bloqueia/desbloqueia o veículo. O ACK ($ETKAACK!) NÃO vem: o firmware
    sobrescreve a response ao emitir os eventos. A confirmação real é o
    $ETEV02! (bloqueado) / $ETEV01! (desbloqueado)."""
    command = '$ETBL02!' if blocked else '$ETBL01!'
    target  = '$ETEV02!' if blocked else '$ETEV01!'
    label   = 'bloqueado' if blocked else 'desbloqueado'

    device.clear()
    log('info', f'>> {command}')

    if not device.expect(target=target, command=command, timeout=15):
        log('err', f'device não confirmou ({target} não veio)')
        return False

    log('ok', f'veículo {label} ({target})')
    return True


def erase():
    """Reset DE FÁBRICA: regenera o esp_id e volta TODAS as settings ao default
    (telemetry->2/Suntech, wifi->false...). Reinicia sozinho
    (Protocol::check chama settings.erase() + device.reset())."""
    log('info', 'enviando $erase! (reset de fábrica — o device reinicia sozinho)')
    device.clear()
    device.send('$erase!')
    sleep(2.0)
    device.send('$ETRS!')
    device.disconnect()
    sleep(3.0)
    return robustSync(retries=10)


def ensureNativeEspId():
    """Garante esp_id nativo (MIC...). Se estiver sobrescrito, faz erase
    e regenera. Retorna o esp_id final (MIC...) ou None."""
    espId = readEspId()
    if isNativeId(espId):
        log('ok', f'esp_id nativo: {espId}')
        return espId

    log('warn', f'esp_id não-nativo ({espId!r}) — executando erase para regenerar')
    if not erase():
        log('err', 'erase falhou (device não voltou)')
        return None

    espId = readEspId()
    if isNativeId(espId):
        log('ok', f'esp_id regenerado: {espId}')
        return espId

    log('err', f'esp_id ainda não-nativo após erase: {espId!r}')
    return None


def recover():
    """Tira o device de estados travados (ex: modo update interrompido):
    reinicia e ressincroniza com retry."""
    log('info', 'recuperando device ($ETRS! + resync)')
    if device.device and device.device.is_open:
        device.clear()
    device.send('$ETRS!')
    device.disconnect()
    sleep(6.0)
    return robustSync()


def rearmUpdate(espId):
    """Re-arma need_update=True no servidor (PATCH). Necessário porque
    /update é one-shot: o servidor zera need_update ao servir o firmware."""
    log('info', f'rearmando need_update=True para {espId}')
    res = post_req(f'/devices/{espId}', {'need_update': True}, type='PATCH')
    if res['status'] == 'error':
        log('err', f'rearm falhou: {res.get("data")}')
        return False
    log('ok', f"need_update = {(res.get('data') or {}).get('need_update')}")
    return True
