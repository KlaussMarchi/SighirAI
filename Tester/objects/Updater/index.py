from objects.Device.index import device
from utils.functions import sendEvent
from time import sleep, time
import base64, zlib
from objects.Server.index import server


# ATUALIZAÇÃO DE FIRMWARE PELO SERIAL: BLOCOS EM BASE64 COM OFFSET E CRC, REENVIADOS ATÉ O "written"
class SerialUpdater:
    CHUNK_SIZE = 2048
    MAX_TRIES  = 5
    SYNC_TRIES = 12    # 60 s: O cmdFlash JÁ SINCRONIZOU ANTES, SEM RESPOSTA AQUI O APARELHO SAIU DA USB
    buffer = str()
    device = None
    percentage = -1

    def setup(self):
        device.reconnect()

    def start(self):
        sendEvent('event', 'aguardando sincronização')
        self.buffer = str()
        synced      = any(device.expect('$ETKAACK!', command='$ETKA!', timeout=5.0) for attempt in range(self.SYNC_TRIES))

        if not synced:
            return sendEvent('error', f'o etilômetro não respondeu ao $ETKA! em {self.SYNC_TRIES*5} s: nada foi gravado')

        sendEvent('success', 'Etilômetro Sincronizado', end='\n\n')
        sleep(1.5)
        fileBytes = server.firmware.file['bytes']

        if not device.expect('STARTING_UPDATE', command=f'__updt__{len(fileBytes)}', fail='_UPDATE_FAIL_'):
            return sendEvent('error', 'etilômetro não iniciou a atualização')

        sendEvent('event', 'update iniciado')
        sleep(0.5)
        return self.upload(fileBytes)

    def upload(self, fileBytes):
        startProg = time()
        total     = len(fileBytes)

        for offset in range(0, total, self.CHUNK_SIZE):
            self.percentage = (offset/total)*100

            if not self.write(fileBytes[offset:offset + self.CHUNK_SIZE], offset):
                return sendEvent('error', f'atualização interrompida no byte {offset} de {total}')

        elapsed = int(time() - startProg)
        sendEvent('success', f'completed in {elapsed} seg! verifying result\n')
        result = self.reply(('_UPDATE_OK_', '_UPDATE_FAIL_'), timeout=30)

        if result is None:
            return sendEvent('event', 'sem confirmação do etilômetro (firmware antigo confirma só no reinício)')

        if result == '_UPDATE_FAIL_':
            return sendEvent('error', 'etilômetro recusou o firmware')

        return sendEvent('success', 'etilômetro atualizado, reiniciando')

    def write(self, chunk, offset):
        chunkString = base64.b64encode(chunk).decode('utf-8')
        header      = f'{chunkString}=#{offset}'   # '=' ANTES DO OFFSET: O FIRMWARE ANTIGO PARA DE DECODIFICAR NO '='
        message     = f'${header}:{zlib.crc32(header.encode()):08x}!'
        sample      = (message[:25] + ' ... ' + message[-25:])

        for attempt in range(self.MAX_TRIES):
            startTime = time()
            device.send(message, breakLine=False)
            reply = self.reply(('written', 'resend', '_UPDATE_FAIL_'))

            timePassed = int((time() - startTime) * 1000)
            sendEvent('python', f'{timePassed}ms - {len(chunkString)} bytes - {self.percentage:.2f}% - {reply} - chunk: {sample}', 'red')

            if reply == 'written':
                return True

            if reply == '_UPDATE_FAIL_':
                return False

        return False

    # O QUE VEIO DEPOIS DA RESPOSTA FICA NO BUFFER: NO ÚLTIMO BLOCO O "written" E O "_UPDATE_OK_" CHEGAM JUNTOS
    def reply(self, tokens, timeout=5.0):
        startTime = time()

        while time() - startTime < timeout:
            for token in tokens:
                if token in self.buffer:
                    self.buffer = self.buffer.split(token, 1)[1]
                    return token

            self.buffer += device.get(timeout - (time() - startTime)) or ''

        return None


updater = SerialUpdater()
