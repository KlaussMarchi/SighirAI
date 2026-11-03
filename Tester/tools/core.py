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
from time import sleep, monotonic

# garante que a raiz do projeto está no sys.path (tools/ é subpasta)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import serial
import serial.tools.list_ports
from objects.Device.index import device
from objects.Server.index import server      # noqa: F401 — reexportado (sighir.py usa core.server)
from objects.Updater.index import updater    # noqa: F401 — reexportado (sighir.py usa core.updater)
from utils.api import post_req

MIN_FIRMWARE  = (6, 5, 3)
VERSION_RE    = re.compile(r'v?(\d+)\.(\d+)\.(\d+)')
DEBUG_SENSORS = ('ETL2608402025435219', 'ETL3550904305917103')   # sensor_id FALSO DA BUILD DE DEBUG
BOOT_TIME     = 30.0    # s, A v6.5 LEVA ~45 S PARA SINCRONIZAR DEPOIS DO RESET (O robustSync COBRE O RESTO)


def log(tag, msg):
    colors = {'ok': '\033[32m', 'err': '\033[31m', 'info': '\033[34m',
              'warn': '\033[38;5;208m', 'reset': '\033[0m'}
    c = colors.get(tag, colors['info'])
    print(f"{c}[sighir:{tag}]{colors['reset']} {msg}")


_everConnected = False
BRIDGES    = ('10c4', '1a86', '0403')    # CONVERSORES USB-SERIAL DO ETILÔMETRO: CP210x (WT32-SC01) PRIMEIRO, CH340, FTDI
PROBE_TIME = 1.5                         # s POR PORTA: O APARELHO VIVO RESPONDE O $ETKA! EM ~0,4 S


def candidates():
    ports = [p for p in serial.tools.list_ports.comports() if p.vid and 'bluetooth' not in (p.description or '').lower()]
    return sorted(ports, key=lambda p: BRIDGES.index(f'{p.vid:04x}') if f'{p.vid:04x}' in BRIDGES else len(BRIDGES))


def probe(port):
    try:
        link = serial.Serial()
        link.port, link.baudrate, link.timeout = port, 115200, 0.2
        link.dtr = link.rts = False    # SOLTOS: NÃO REINICIA O ESP32 PELO CIRCUITO DE AUTO-RESET
        link.open()
    except serial.SerialException:
        return False

    answer, startTime = b'', monotonic()

    while monotonic() - startTime < PROBE_TIME and b'ETKAACK' not in answer:
        link.write(b'$ETKA!\r\n')
        sleep(0.4)
        answer += link.read(link.in_waiting or 1)

    link.close()
    return b'ETKAACK' in answer


# COM MAIS DE UMA PLACA USB-SERIAL NA BANCADA, FICA COM A QUE RESPONDE $ETKAACK! (O ETILÔMETRO)
def findPort():
    ports = candidates()

    if len(ports) <= 1:
        return ports[0].device if ports else device.scan()

    answering = next((p.device for p in ports if probe(p.device)), None)

    if answering is None:
        log('warn', f"nenhuma das portas USB respondeu ao $ETKA! ({', '.join(p.device for p in ports)}): tentando "
                    f"{ports[0].device} — confira qual é o etilômetro")

    return answering or ports[0].device


def robustConnect(retries=6, backoff=2.0):
    global _everConnected
    for attempt in range(1, retries + 1):
        # nunca conectou neste processo e não há porta candidata (nenhuma USB): o etilômetro não está
        # plugado — duas olhadas e desiste (~2 s em vez de ~24 s). A insistência longa abaixo é para a
        # porta que some e volta depois de reset/erase/flash, quando já houve conexão.
        if not _everConnected and device.port is None:
            port = findPort()
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
        device.port = findPort()
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


# CONFIGURAÇÃO DE OPERAÇÃO DO APARELHO (VAI PARA O default_settings.settings NO CADASTRO); O RESTO É IDENTIDADE OU DIAGNÓSTICO
DEVICE_SETTINGS = ['company', 'telemetry', 'vehicle_type', 'maneuver_time', 'postpone_time', 'max_postpone',
                   'time_of_travel', 'number_of_tests', 'rand_ppn_time', 'rand_min_time', 'enable_random', 'camera',
                   'bypass', 'blowProb', 'valet', 'suitcase', 'blockinv', 'lang', 'brightness', 'volume', 'wifi',
                   'ssid', 'passwd', 'server']

TEXT_SETTINGS = ('company', 'lang', 'ssid', 'passwd', 'server')    # TEXTO MESMO QUANDO SÓ TEM DÍGITOS (SENHA 12345678)

SETTING_KEYS = ['esp_id', 'sensor_id', *DEVICE_SETTINGS, 'last_alcohol', 'last_analog', 'temp_debug', 'presstream',
                'press', 'testalc', 'reset']

TELEMETRIES = {'mix': 0, 'suntech': 2, 'mix2': 5, 'entrack': 6}


def readSetting(key, timeout=6.0, retries=3):
    """Lê uma setting do NVS (`ID:<key>$` -> `$<value>!`).

    Só vale o formato `$valor!` (fora os `$ETEVxx!`): linha de debug do firmware que chegue antes ("heater OFF")
    não é a resposta — segue lendo até o fim do timeout. A resposta pode vir grudada num `$ETEV17!` da sync."""
    for attempt in range(1, retries + 1):
        device.clear()
        device.send(f'ID:{key}$')
        deadline = monotonic() + timeout

        while monotonic() < deadline:
            raw    = device.get(timeout=deadline - monotonic()) or ''
            tokens = [token.strip() for token in TOKEN_RE.findall(raw) if token.strip() and not EVENT_RE.match(token.strip())]

            if tokens:
                return tokens[-1]

            if 'ERROR' in raw:
                return 'ERROR'

        log('warn', f'sem resposta para ID:{key}$, tentativa {attempt}/{retries}')
        sleep(0.3)

    return None


def readSettings(keys=None):
    return {key: readSetting(key) for key in (keys or SETTING_KEYS)}


# AS SETTINGS VOLTAM COMO TEXTO DO NVS ('5', '0.1', 'false', 'null' = CHAVE AUSENTE): NO JSON VIRAM NÚMERO, BOOLEANO OU None
def typedValue(text):
    if text in (None, 'null', 'ERROR'):
        return None

    if text in ('true', 'false'):
        return text == 'true'

    for kind in (int, float):
        try:
            return kind(text)
        except ValueError:
            continue

    return text


def readConfig():
    values = readSettings(DEVICE_SETTINGS)
    return {key: value if key in TEXT_SETTINGS and value not in (None, 'null', 'ERROR') else typedValue(value) for key, value in values.items()}


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
    if not (device.device and device.device.is_open):
        robustConnect(retries=2)
    if device.device and device.device.is_open:
        device.clear()
        device.send('$ETRS!')
    device.disconnect()
    sleep(6.0)

    if robustSync(retries=3):
        return True

    log('warn', 'o $ETRS! não foi lido (tela que não lê a serial, ex.: contrassenha): reset pelo pino RTS')
    return hardReset() and robustSync()


# EN DO ESP32 PELO RTS DO CONVERSOR USB, COM O DTR SOLTO (BOOT NORMAL), COMO O "Hard resetting via RTS pin" DO ESPTOOL
def hardReset():
    if not robustConnect(retries=2):
        return False

    device.device.dtr = False
    device.device.rts = True
    sleep(0.2)
    device.device.rts = False
    device.disconnect()
    sleep(BOOT_TIME)
    return True


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
