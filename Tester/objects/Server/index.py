import json
from time import sleep
from datetime import datetime
from utils.functions import sendEvent
from utils.classes import CustomForms
from utils.api import get_req, post_req
from objects.Device.index import device
from prompt_toolkit import prompt


class Firmware:
    def __init__(self, server):
        self.server = server
        self.file = None
    
    def download(self):
        esp_id = self.server.getDeviceInfo('ID:esp_id$', 'MIC')
        sleep(1.5)

        data  = {'esp_id': esp_id}
        result = post_req('/update', data, use_base_url=True)

        if result['status'] == 'error':
            return sendEvent('error', 'Não foi possível baixar o arquivo de atualização')

        self.file = result['data']

        # /update é "one-shot": ao servir, o servidor zera need_update e a
        # próxima chamada volta 204 No Content (data=None). Se não veio firmware,
        # provavelmente need_update está False — re-arme com PATCH /devices/{id}.
        if not self.file or not self.file.get('bytes'):
            self.file = None
            return sendEvent('error', 'servidor não retornou firmware (need_update=False? re-arme via PATCH /devices/{id})')

        filename = self.file.get('filename')
        total    = len(self.file['bytes'])
        sendEvent('success', f'firmware "{filename}" baixado: {total} bytes')
        return True


class Server:
    def __init__(self):
        self.companies   = []
        self.working = False
        self.firmware = Firmware(self)  
        self.forms    = CustomForms()

    def update(self):
        sendEvent('event', 'obtendo dados do servidor')
        self.working = False

        result = get_req('/companies?type=transportation')
  
        if result['status'] == 'error' or not result['data']:
            return sendEvent('error', 'conexão com o servidor')

        self.companies = result['data']
        sendEvent('success', 'database carregada', end='\n\n')

    def register(self):
        manual = not self.forms.getBool('Extração de Dados Automática?')

        if not manual:
            data = {
                'company': self.selectCompany(),
                'series_num': self.selectNumber(),
                'id': self.getDeviceInfo('ID:esp_id$', 'MIC'),
                'sensor_id': self.getDeviceInfo('sensor_id', 'ETL'),
                'timestamp': self.getDeadline(datetime.now()),
                'suntech': self.getSuntech(),
                'need_update': True
            }
        else:
            data = {
                'company': self.selectCompany(),
                'series_num': input('Número de Série: '), 
                'id': input('ID do Aparelho: '),            
                'sensor_id': input('ID do Sensor: '),            
                'timestamp': self.getDeadline(datetime.now()),
                'suntech': self.getSuntech(),    
                'need_update': True
            }

        # 00299
        # MIC0014246467341799
        # ETL3550904305917103
        # 1700023877

        has_telemetry = (data['suntech'] != 'N/A')

        if has_telemetry:
            result = post_req('/suntechs', {'id': data['suntech']})

            if result['status'] == 'error':
                return sendEvent('error', f'não foi possível registrar o chip suntech: {result.get("data")}')

        data['chip'] = 'N/A' if not has_telemetry else input('Número do Chip Suntech: ')
        print()

        sendEvent('ATENÇÃO', f'insira e etiqueta: {data["series_num"]}', 'orange')
        input('aperte enter para continuar ')

        sendEvent('event', f'Tentando Registrar {data["id"]}')
        result = post_req('/devices', data)
        
        if result['status'] == 'error':
            return sendEvent('error', f'erro ao registrar dispositivo: {result.get("data")}')
        
        sendEvent('success', f'Device {data["id"]} registrado com sucesso!')
        print(json.dumps(result, ensure_ascii=False, indent=4))
    
    def getDeadline(self, date):
        if isinstance(date, str):
            date = datetime.fromisoformat(date)

        return date.strftime('%Y-%m-%d %H:%M:%S')

    def getSuntech(self):
        value = input('digite o ID suntech: ').strip()

        if len(value) == 0:
            return 'N/A'
        
        return value

    def selectNumber(self):
        result = get_req('/devices')

        if result['status'] == 'error':
            sendEvent('error', 'erro no servidor')
            sleep(1.5)
            return self.selectNumber()
        
        devices = result['data']
        length  = max([int(item['series_num']) for item in devices])
        last    = str(length + 1).zfill(5)
        target  = prompt('Número de Série: ', default=last)
        return target
    
    def getDeviceInfo(self, cmd, include=''):
        sendEvent('event', f'searching: {cmd}')
        response = device.request(cmd, timeout=10).strip()

        if len(response) == 0 or include not in response:
            sendEvent('error', f'invalid: {response}')
            sleep(1.5)
            return self.getDeviceInfo(cmd)
        
        id = response[response.find('$')+1:response.find('!')].replace('$', '').strip()
        sendEvent('success', f'response: {id}', end='\n\n')
        return id

    def selectCompany(self):
        self.forms.set({item['value']: item['label'] for item in self.companies})
        self.company = self.forms.get('Selecione a Empresa')

        for company in self.companies:
            if company.get('value') == self.company:
                self.company = company.get('id')

        return self.company


server = Server()