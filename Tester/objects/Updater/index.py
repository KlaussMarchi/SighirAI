from objects.Device.index import device
from utils.functions import sendEvent
from time import sleep, time
import base64, io
from objects.Server.index import server

class SerialUpdater:
    CHUNK_SIZE = 2048
    device = None
    percentage = -1
    
    def setup(self):
        device.reconnect()

    def start(self):
        sendEvent('event', 'aguardando sincronização')
        
        while True:
            device.send('$ETKA!')
            
            if device.expect('$ETKAACK!', timeout=5.0):
                break
        
        sendEvent('success', 'Etilômetro Sincronizado', end='\n\n')
        sleep(1.5)
        device.expect('STARTING_UPDATE', command='__updt__')
        sendEvent('event', 'update iniciado')
        sleep(0.5)
        self.upload()

    def upload(self):
        self.percentage = 0
        startProg = time()
        fileBytes = server.firmware.file['bytes']

        firmware = io.BufferedReader(io.BytesIO(fileBytes))
        total = len(fileBytes)
        sum   = 0.0

        while self.percentage < 100:
            chunk = firmware.read(self.CHUNK_SIZE)
            self.write(chunk, self.percentage)
            device.expect('written')
            
            sum = (sum + len(chunk))
            self.percentage = (sum/total)*100

        timeout = int(time() - startProg)
        sendEvent('success', f'completed in {timeout} seg! verifying result\n')
        sleep(11.0)
        line = device.get()
        sendEvent('arduino', line, 'blue')

    def write(self, chunk, percentage):
        chunkString = base64.b64encode(chunk).decode('utf-8')
        startTime   = time()

        message = f'${chunkString}!'
        sample  = (message[:25] + ' ... ' + message[-25:])
        device.send(message, breakLine=False)
        
        timePassed = int((time() - startTime) * 1000)
        logText    = f'{timePassed}ms - {len(chunkString)} bytes - {percentage:.2f}% - chunk: {sample}'
        sendEvent('python', logText, 'red')


updater = SerialUpdater()
