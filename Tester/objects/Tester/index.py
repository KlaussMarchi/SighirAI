from utils.functions import sendEvent, getPath
from utils.classes import CustomForms
from utils.variables import telemetries
from objects.Tester.protocol import Protocol
from objects.Updater.index import updater
from objects.Server.index import server
from objects.Device.index import device
from objects.Serial.index import serial
from time import sleep
import subprocess


class SighirTester:
    device   = None
    forms    = None
    protocol = None
    
    mainOptions = {
        'general': 'Teste Geral',
        'register': 'Cadastrar Dispositivo',
        'update': 'Atualização de Firmware',
        'update_wifi': 'Atualização de Firmare (Versão Antiga)',
        'serial': 'Teste Serial',
        'reset': 'Reiniciar Aparelho',
        'restart': 'Reiniciar Programa',
    }
    
    def __init__(self):
        self.forms    = CustomForms()
        self.protocol = Protocol()

    def start(self):
        boards = len(device.getPorts().values())
        
        if boards > 0 and CustomForms().getBool('Atualizar Drivers?'):
            subprocess.run([getPath('assets/files/driver.exe')], check=True)
            sleep(0.5)

        if boards > 0 and CustomForms().getBool('Conectar Etilômetro?'):
            device.select()
            sleep(0.5)
            self.protocol.sync()

        self.forms.set(self.mainOptions)
        choice = self.forms.get()

        if choice == 'general':
            self.forms.set({value: key for key, value in telemetries.items()})
            telemetry = self.forms.get('selecione a telemetria')
            self.protocol.setup(telemetry)
            self.protocol.start()
        
        if choice == 'update':
            server.update()
            server.firmware.download()
            updater.setup()
            updater.start()

        if choice == 'update_wifi':
            if not self.forms.getBool('Deseja Realmente Desconfigurar Aparelho?'):
                return

            self.protocol.command('ssid', 'Sighir')
            self.protocol.command('passwd', 'Sighir2024')
            self.protocol.command('esp_id', 'admin_sighir')
            
            print()
            sendEvent('success', 'aperte enter quando o etilômetro atualizar');
            input()

            self.protocol.command('$erase!')
            self.protocol.command('$ETRS!')
            
        if choice == 'serial':
            serial.setup()
            serial.start()

        if choice == 'register':
            server.update()
            server.register()

        if choice == 'reset':
            device.send('$ETRS!')
            sleep(1.0)
            device.disconnect()
            device.connect()

tester = SighirTester()