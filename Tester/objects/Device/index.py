import serial
import serial.tools.list_ports
from time import sleep, time
from utils.functions import sendEvent
from utils.classes import CustomForms
from utils.noise import noise

class Device:
    device = None
    port   = None
    rate   = None
    data   = None

    def __init__(self, port=None, rate=9600, timeout=3.0):
        self.port = port
        self.rate = rate
        self.timeout = timeout

    def connect(self, delay=2.5):
        """`delay` NÃO é mais sleep cego: é o ORÇAMENTO de espera até o device
        ficar pronto. Abrir a porta USB mexe em DTR/RTS e pode resetar o ESP32,
        então ainda é preciso esperar — mas esperamos o `$ETKAACK!` (~0.3s com o
        device vivo) em vez de dormir 2.5s sempre.
        delay=0 => NÃO sonda (obrigatório no reconnect durante o flash: um
        `$ETKA!` no meio do stream de update corromperia o firmware)."""
        self.port = self.port if self.port is not None else self.scan()

        if self.port is None:
            self.device = None
            return sendEvent('error', 'no serial port found (verifique cabo USB / driver)', delay=2.0)

        sendEvent('event', f'trying connection: {self.port}')

        if self.device and self.device.is_open:
            return sendEvent('success', 'already connected')
        try:
            self.device = serial.Serial(self.port, self.rate, timeout=self.timeout)
        except Exception as error:
            self.device = None
            return sendEvent('error', error, delay=3.0)

        self.awaitReady(timeout=delay)
        return sendEvent('success', 'device connected successfully')

    def awaitReady(self, timeout=2.5):
        """Espera o device responder ao keep-alive. Volta assim que vier o
        `$ETKAACK!` — não dorme o tempo todo à toa."""
        if timeout <= 0:
            return True

        startTime = time()

        while time() - startTime < timeout:
            self.clear()

            if self.expect(target='ETKAACK', command='$ETKA!', timeout=1.0):
                return True

        return False
    
    def reconnect(self):
        if not bool(self.device and self.device.is_open):
            self.connect()
    
    def disconnect(self):
        if not self.device:
            return
        try:
            if self.device.is_open:
                self.device.close()
        except Exception as error:
            sendEvent('error', error)
    
    def getPorts(self):
        return {port.device: port.description for port in serial.tools.list_ports.comports() if 'n/a' not in port.description}
    
    def select(self):
        ports = self.getPorts()
        forms = CustomForms()
        forms.set(ports)
        choice = forms.get('Selecione a Porta')
        self.port = choice
        self.connect()
        
    def scan(self):
        ports  = self.getPorts()
        target = None

        if len(ports.values()) == 0:
            sendEvent('error', 'no port found')
            return None

        for i, (port, description) in enumerate(ports.items()):
            if 'usb' in description.lower():
                target = port

        # fallback cross-platform: se nenhuma descrição casar com 'usb'
        # (raro no Windows com COMx), usa a primeira porta disponível que não seja
        # Bluetooth — porta BT ("Serial Padrão por link Bluetooth", /dev/rfcomm*) nunca
        # é o etilômetro e segura o status por ~1 min em timeout
        if target is None:
            wired = [port for port, description in ports.items()
                     if 'bluetooth' not in description.lower() and 'rfcomm' not in port.lower()]

            if not wired:
                sendEvent('error', 'no port found (só portas Bluetooth: o etilômetro não está no USB)')
                return None

            target = wired[0]

        return target
    
    def send(self, msg, breakLine=True):
        msg = msg.strip() + ('\r\n' if breakLine else '')

        try:
            self.device.write(msg.encode())
            #sendEvent('python', f'sent: {msg.strip()}', 'red')
        except Exception as error:
            return sendEvent('error', error)
        
        return True
    
    def wait(self, timeout=5):
        startTime = time()

        while time() - startTime < timeout:
            if self.available():
                return True

        return False
    
    def decode(self, response, keep=None):
        text = response.decode('utf-8', errors='ignore')
        return noise.clean(text, keep)

    def get(self, timeout=7.0, keep=None):
        startTime = time()
        response = bytearray()

        try:
            while time() - startTime < timeout:
                size = self.device.in_waiting

                if size == 0:
                    sleep(0.005)
                    continue

                response.extend(self.device.read(size))

                if b'\n' not in response:
                    continue

                cleaned = self.decode(response, keep)

                # linha só de lixo de telemetria (SttReq, $ETACK!, AT+QACC?...):
                # descarta e segue lendo até sobrar algo útil ou estourar o timeout
                if not cleaned:
                    response = bytearray()
                    continue

                return cleaned

            return self.decode(response, keep)
        except Exception as error:
            sendEvent('error', error)
            return None


    def available(self):
        if not self.device:
            return 0
        
        totalBytes = self.device.in_waiting
        return totalBytes if totalBytes > 0 else 0
    
    def getResponse(self, msg):
        if not self.send(msg):
            return None

        return self.get(10)

    def clear(self, delay=0, quiet=0.15, maxWait=0.6):
        """Esvazia o buffer de entrada. Antes eram 1.0s de sleep fixo em TODA
        consulta; agora drena até a linha ficar em silêncio por `quiet`
        (teto `maxWait`) — o ruído de telemetria chega a cada 2s, então 60ms de
        silêncio já significa buffer limpo."""
        self.device.reset_input_buffer()
        startTime = time()
        lastByte  = time()

        while time() - startTime < maxWait:
            size = self.available()

            if size:
                try:
                    self.device.read(size)
                except Exception:
                    pass

                lastByte = time()
                continue

            if time() - lastByte >= quiet:
                break

            sleep(0.005)

        self.device.reset_input_buffer()

        if delay:
            sleep(delay)

    def expect(self, target='OK', command=None, fail=None, timeout=10):
        startTime  = time()
        buffer     = str()
        timePassed = 0

        if command is not None:
            self.send(command)

        while timePassed < timeout:
            timePassed = time() - startTime

            try:
                size = self.device.in_waiting

                if size == 0:
                    sleep(0.005)
                    continue

                buffer += self.device.read(size).decode('utf-8', errors='ignore')
            except OSError as error:
                # hiccup de USB (Errno 5) durante o flash: o device pode
                # re-enumerar; tenta reconectar e seguir sem derrubar a operação
                sendEvent('error', f'serial I/O hiccup: {error} (tentando reconectar)')
                self.disconnect()
                sleep(1.5)
                self.connect(delay=0)
                continue

            # o alvo (e o fail) fica preservado: o teste do Suntech, por exemplo,
            # espera justamente o 'SttReq' que em outros contextos é lixo
            cleaned = noise.clean(buffer, keep=[target, fail])

            if target in cleaned:
                return True

            if fail and fail in cleaned:
                return False

        return None

    def request(self, value, timeout=5.0):
        self.send(value)
        startTime = time()

        while time() - startTime < timeout:
            if not self.available():
                sleep(0.005)
                continue

            request = self.get(timeout=max(0.5, timeout - (time() - startTime)))

            # NÃO filtre por tamanho aqui: settings curtas são respostas válidas
            # (`ID:telemetry$` -> `$6!`, 3 chars). O lixo de telemetria já foi
            # removido pelo noise filter dentro do get() — o que sobrou é útil.
            if not request:
                continue

            return request

        return None


device = Device(rate=115200)