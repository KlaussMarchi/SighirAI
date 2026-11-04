from objects.Device.index import device
from utils.functions import sendEvent
from time import time
import base64, zlib, hashlib, re
from objects.Server.index import server

try:
    from termios import error as PortError    # NO LINUX O tcflush/tcsetattr DA PORTA QUE SUMIU NÃO VIRA OSError
except ImportError:
    PortError = OSError


# ATUALIZAÇÃO DE FIRMWARE PELO SERIAL: BLOCOS EM BASE64 COM OFFSET E CRC, REENVIADOS ATÉ O "written"; O FIRMWARE NOVO RECEBE A SESSÃO A 921600
class SerialUpdater:
    BAUD       = 115200
    FAST_BAUD  = 921600    # SÓ DURANTE A SESSÃO E SE O FIRMWARE ACEITAR: FORA DELA A SERIAL CONTINUA EM 115200
    CHUNK_SIZE = 2048      # O FIRMWARE ANTIGO RECEBE NO MÁXIMO 2048 BYTES POR BLOCO
    FAST_CHUNK = 4096      # UM SETOR DA FLASH: O FIRMWARE NOVO RECEBE ATÉ 4096
    MAX_TRIES  = 5
    SYNC_TRIES = 12        # 60 s: O cmdFlash JÁ SINCRONIZOU ANTES, SEM RESPOSTA AQUI O APARELHO SAIU DA USB
    SESSIONS   = 2         # A SESSÃO QUE CAI NO MEIO NÃO ATIVA NADA: A SEGUNDA RECOMEÇA EM 115200
    PROBE_WAIT = 2.5       # s PELO "written" DO PRIMEIRO BLOCO NA VELOCIDADE NOVA (APAGAR 64 KB DA FLASH LEVA ATÉ 2 s)
    PROBE_TIME = 3.7       # s ATÉ O FIRMWARE TER VOLTADO PARA 115200: ELE ESPERA 3 s PELO PRIMEIRO BLOCO
    buffer = str()
    percentage = -1

    def setup(self):
        device.reconnect()

    def start(self):
        for session in range(self.SESSIONS):
            result = self.update(fast=(session == 0))

            if result is not None:
                return result

            sendEvent('event', f'a sessão caiu no meio sem ativar nada: recomeçando em {self.BAUD} baud')

        return sendEvent('error', f'a gravação caiu nas {self.SESSIONS} sessões: o aparelho segue na versão anterior')

    # UMA SESSÃO DE GRAVAÇÃO: None = CAIU NO MEIO E OUTRA SESSÃO RESOLVE; True/False = O APARELHO CONFIRMOU OU RECUSOU
    def update(self, fast):
        sendEvent('event', 'aguardando sincronização')
        self.buffer     = str()
        self.percentage = -1
        synced          = any(device.expect('$ETKAACK!', command='$ETKA!', timeout=5.0) for attempt in range(self.SYNC_TRIES))

        if not synced:
            return sendEvent('error', f'o etilômetro não respondeu ao $ETKA! em {self.SYNC_TRIES*5} s: nada foi gravado')

        sendEvent('success', 'Etilômetro Sincronizado', end='\n\n')
        self.drain(1.5)
        fileBytes = server.firmware.file['bytes']
        total     = len(fileBytes)
        md5       = hashlib.md5(fileBytes).hexdigest()
        device.clear()
        device.send(f'__updt__{total},{md5},{self.FAST_BAUD if fast else self.BAUD}')   # O FIRMWARE ANTIGO LÊ SÓ O TAMANHO

        if self.reply(('STARTING_UPDATE', '_UPDATE_FAIL_'), timeout=10) != 'STARTING_UPDATE':
            return sendEvent('error', 'etilômetro não iniciou a atualização')

        match = re.match(r'_(\d+)_', self.buffer)    # FIRMWARE NOVO: "_STARTING_UPDATE_<VELOCIDADE>_"; O ANTIGO SÓ "_STARTING_UPDATE_"
        speed = int(match.group(1)) if match else self.BAUD
        size  = self.FAST_CHUNK if match else self.CHUNK_SIZE
        sendEvent('event', f'update iniciado: {speed} baud, blocos de {size} bytes' + ('' if match else ' (firmware antigo)'))

        if not match:
            self.drain(0.5)

        self.percentage = 0
        first = self.probe(fileBytes[:size], speed) if speed != self.BAUD else 0

        if first is None:
            return None

        startProg = time()

        for offset in range(first, total, size):
            self.percentage = (offset/total)*100

            if self.write(fileBytes[offset:offset + size], offset, patient=(first == 0)) != 'written':
                self.setBaud(self.BAUD)
                sendEvent('error', f'atualização interrompida no byte {offset} de {total}')
                return None

        elapsed = int(time() - startProg)
        sendEvent('success', f'completed in {elapsed} seg! verifying result\n')
        result = self.reply(('_UPDATE_OK_', '_UPDATE_FAIL_'), timeout=30)
        self.setBaud(self.BAUD)

        if result is None:
            return sendEvent('event', 'sem confirmação do etilômetro (firmware antigo confirma só no reinício)')

        if result == '_UPDATE_FAIL_':
            return sendEvent('error', 'etilômetro recusou o firmware')

        return sendEvent('success', 'etilômetro atualizado, reiniciando')

    # O PRIMEIRO BLOCO CONFIRMA A VELOCIDADE NOVA; SEM O "written" ESPERA O FIRMWARE VOLTAR PARA 115200 E A SESSÃO SEGUE NELA
    def probe(self, chunk, speed):
        switched = time()
        reply    = self.write(chunk, 0, tries=1, timeout=self.PROBE_WAIT) if self.setBaud(speed) else None

        if reply == 'written':
            return len(chunk)

        self.drain(max(0.0, switched + self.PROBE_TIME - time()))
        self.setBaud(self.BAUD)

        if reply == '_UPDATE_FAIL_':
            return None

        sendEvent('event', f'sem resposta a {speed} baud: a sessão segue a {self.BAUD}')
        return 0

    # patient=False NA VELOCIDADE NOVA: SEM RESPOSTA NÃO REENVIA (O APARELHO PODE JÁ ESTAR EM 115200 E O BLOCO VIRARIA LIXO NOS COMANDOS)
    def write(self, chunk, offset, tries=MAX_TRIES, timeout=5.0, patient=True):
        chunkString = base64.b64encode(chunk).decode('utf-8')
        header      = f'{chunkString}=#{offset}'   # '=' ANTES DO OFFSET: O FIRMWARE ANTIGO PARA DE DECODIFICAR NO '='
        message     = f'${header}:{zlib.crc32(header.encode()):08x}!'
        sample      = (message[:25] + ' ... ' + message[-25:])

        for attempt in range(tries):
            startTime = time()

            if not self.clear():
                return None

            device.send(message, breakLine=False)
            reply = self.ack(offset + len(chunk), timeout)

            timePassed = int((time() - startTime) * 1000)
            sendEvent('python', f'{timePassed}ms - {len(chunkString)} bytes - {self.percentage:.2f}% - {reply} - chunk: {sample}', 'red')

            if reply in ('written', '_UPDATE_FAIL_'):
                return reply

            if reply is None and not patient:
                return None

        return None

    # "written#N" DO FIRMWARE NOVO (VALE SÓ O "#N" SE UMA LETRA SE PERDEU); N ANTES DO FIM DESTE BLOCO É A RESPOSTA ATRASADA DE OUTRO ENVIO
    def ack(self, end, timeout):
        deadline = time() + timeout

        while True:
            reply = self.reply(('written', '#', 'resend', '_UPDATE_FAIL_'), max(0.0, deadline - time()))
            match = re.match(r'#?(\d+)', self.buffer)

            if reply not in ('written', '#'):
                return reply

            if reply == 'written' and not match:    # FIRMWARE ANTIGO: "written" SEM O OFFSET
                return 'written'

            if match and int(match.group(1)) >= end:
                return 'written'

    # O QUE VEIO DEPOIS DA RESPOSTA FICA NO BUFFER: NO ÚLTIMO BLOCO O "written" E O "_UPDATE_OK_" CHEGAM JUNTOS
    def reply(self, tokens, timeout=5.0):
        startTime = time()

        while True:
            found = [(self.buffer.index(token), token) for token in tokens if token in self.buffer]

            if found:
                index, token = min(found)
                self.buffer  = self.buffer[index + len(token):]
                return token

            left = timeout - (time() - startTime)

            if left <= 0:
                return None

            self.buffer += device.get(left) or ''

    # LÊ E DESCARTA EM VEZ DE DORMIR: O CONVERSOR CH340 REPETE O ÚLTIMO PACOTE QUANDO A PORTA FICA SEM LEITURA E EMBARALHA A RESPOSTA SEGUINTE
    def drain(self, seconds):
        deadline = time() + seconds

        while time() < deadline:
            device.get(deadline - time())

        self.buffer = str()

    # O QUE CHEGOU ANTES DO ENVIO NÃO É RESPOSTA DO BLOCO; SEM A PORTA (CABO SOLTO) A SESSÃO CAI E O start() TENTA OUTRA
    def clear(self):
        self.buffer = str()

        try:
            device.device.reset_input_buffer()
        except (AttributeError, OSError, PortError) as error:
            sendEvent('error', f'a porta serial sumiu: {error}')
            return False

        return True

    # SÓ O LADO DO PC: O APARELHO TROCA A VELOCIDADE DELE SOZINHO DENTRO DA SESSÃO
    def setBaud(self, speed):
        try:
            device.device.baudrate = speed
        except (AttributeError, ValueError, OSError, PortError) as error:
            sendEvent('error', f'a porta não aceitou {speed} baud: {error}')
            return False

        return self.clear()


updater = SerialUpdater()
