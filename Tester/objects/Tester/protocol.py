from utils.functions import sendEvent, getPath
from objects.Device.index import device
from utils.classes import CustomForms
from utils.variables import telemetries, settings
from time import sleep
import json


class Protocol:
    forms  = CustomForms()
    checklist = None
    telemetry = 'mix'

    def __init__(self):
        self.checklist = json.load(open(getPath('protocol.json'), 'r', encoding='utf-8')) 

    def sync(self):
        sendEvent('event', 'aguardando etilometro')
        sleep(1.5)

        while True:
            device.send('$ETKA!')

            if device.expect('ETKAACK', timeout=5.0):
                break
        
        sendEvent('success', 'etilometro sincronizado')

    def setup(self, telemetry):
        self.telemetry = next((key for key, value in telemetries.items() if value == telemetry), None)
        device.reconnect()
        self.sync()

        if self.forms.getBool('configurar etilômetro?'):
            self.config(telemetry)

    def config(self, telemetry):
        settings['telemetry'] = telemetry

        for key, value in settings.items():
            cmd = f'CF:{key}${value}!'
            sendEvent('event', f'sending {cmd}')
            device.send(cmd)
            sleep(1.0)

        device.send('$ETRS!')
        device.reconnect()
        self.sync()

    def start(self):
        options = {'standard': 'Procedimento Padrão'}
        options.update({data['value']: data['label'] for data in self.checklist})
        options.update({'exit': 'Voltar ao Menu'})

        self.forms.set(options)
        choice = self.forms.get()

        if choice == 'exit':
            return None

        if choice != 'standard':
            return self.test(choice)
        
        for option in self.checklist:
            self.test(option['value'])

    def test(self, key):
        target = self.getTarget(key)
        
        if 'any' in target.keys():
            commands = target.get('any')
        elif self.telemetry in target:
            commands = target[self.telemetry]
        else:
            sendEvent('error', f"teste \"{target['label']}\" indisponível para telemetria '{self.telemetry}' (pulando)")
            return True
        
        sendEvent('event', f"testando \"{target['label']}\"")
        device.clear(0.5)

        for command in commands:
            responses = command['response']
            request   = command['value']

            if len(responses) == 0:
                sendEvent('success', 'event check', end='\n\n')
                continue
            
            if 'STT;0360000001' in request:
                for i in range(4): device.send(request); sleep(0.5)

            for response in responses:
                if not self.validate(request, response):
                    if self.forms.getBool('tentar novamente?'):
                        return self.test(key)
                
                device.clear()
        
        return True

    def getTarget(self, itemValue):
        for i, option in enumerate(self.checklist):
            if option['value'] == itemValue:
                return self.checklist[i]
        
        return self.checklist[0]

    def validate(self, request, desired):
        expected = desired.get('value')
        timeout  = desired.get('timeout')
        delay = desired.get('delay')
        fail  = desired.get('fail')

        sendEvent('command', request, 'blue')
        sendEvent('expecting', expected, 'green')
        sleep(1.5)

        result = device.expect(expected, request, fail, timeout)

        if result is True:
            sendEvent('success', 'event check', end='\n\n')
            if delay > 0: sleep(delay)
            return True
        
        if result is False:
            sendEvent('error', f'falha em {expected}')
            return False
        
        if result is None:
            sendEvent('error', f'timeout em {expected}')
            return False
        
    def command(self, key, value=None):
        cmd = f'CF:{key}${value}!' if value is not None else key
        sendEvent('event', f'sending {cmd}')
        device.send(cmd)
        sleep(1.2)
