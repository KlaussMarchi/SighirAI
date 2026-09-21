import time
import requests
import urllib3

urllib3.disable_warnings()


# CLIENTE DA API DE PRODUCAO, RENOVA O TOKEN SOZINHO PORQUE O ACCESS DURA 300 S
class Api:
    URL     = 'https://sighir.com:8000/api/v2'
    USER    = 'sighir@gmail.com'
    PASS    = 'sighir12345'
    MARGIN  = 60
    TRIES   = 4

    def __init__(self):
        self.session = requests.Session()
        self.session.verify = False
        self.access  = None
        self.refresh = None
        self.exp     = 0

    # PEGA O PAR ACCESS/REFRESH DO ZERO
    def connect(self):
        res = self.session.post(f'{self.URL}/token/', json={'username': self.USER, 'password': self.PASS}, timeout=30)
        res.raise_for_status()
        data = res.json()
        self.access  = data['access']
        self.refresh = data['refresh']
        self.exp     = time.time() + 300 - self.MARGIN
        return True

    # RENOVA ANTES DE VENCER, CAI PRO LOGIN SE O REFRESH TAMBEM MORREU
    def check(self):
        if self.access and time.time() < self.exp:
            return True

        if self.refresh:
            res = self.session.post(f'{self.URL}/token/refresh/', json={'refresh': self.refresh}, timeout=30)

            if res.status_code == 200:
                self.access = res.json()['access']
                self.exp    = time.time() + 300 - self.MARGIN
                return True

        return self.connect()

    # GET COM RETENTATIVA: 401 RENOVA O TOKEN, 5XX ESPERA E TENTA DE NOVO
    def get(self, endpoint, **params):
        for n in range(self.TRIES):
            self.check()
            headers = {'Authorization': f'Bearer {self.access}'}

            try:
                res = self.session.get(f'{self.URL}/{endpoint}', params=params, headers=headers, timeout=120)
            except requests.RequestException:
                time.sleep(2 * (n + 1))
                continue

            if res.status_code == 200:
                return res.json()

            if res.status_code == 401:
                self.exp = 0
                continue

            if res.status_code >= 500:
                time.sleep(2 * (n + 1))
                continue

            res.raise_for_status()

        raise RuntimeError(f'{endpoint} falhou em {self.TRIES} tentativas')

    # ESCRITA. SO A TABELA anomalies E PERMITIDA, O RESTO DO SERVIDOR E LEITURA
    def send(self, method, endpoint, data=None):
        if not endpoint.startswith('anomalies/'):
            raise PermissionError(f'escrita bloqueada fora de anomalies/: {method} {endpoint}')

        for n in range(self.TRIES):
            self.check()
            headers = {'Authorization': f'Bearer {self.access}'}

            try:
                res = self.session.request(method, f'{self.URL}/{endpoint}', json=data, headers=headers, timeout=60)
            except requests.RequestException:
                time.sleep(2 * (n + 1))
                continue

            if res.status_code in (200, 201, 204):
                return res.json() if res.content else {}

            if res.status_code == 401:
                self.exp = 0
                continue

            if res.status_code >= 500:
                time.sleep(2 * (n + 1))
                continue

            raise RuntimeError(f'{method} {endpoint} -> {res.status_code}: {res.text[:200]}')

        raise RuntimeError(f'{method} {endpoint} falhou em {self.TRIES} tentativas')

    # PAGINA ATE O FIM SEGUINDO O next, SEM ASSUMIR QUANTAS PAGINAS EXISTEM
    def getData(self, endpoint, **params):
        params.setdefault('limit', 2000)
        page = 1
        rows = []

        while True:
            data = self.get(endpoint, page=page, **params)

            if isinstance(data, list):
                return data

            rows += data.get('results', [])

            if not data.get('next'):
                return rows

            page += 1


api = Api()
