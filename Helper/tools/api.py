"""
Cliente da API de produção (https://sighir.com:8000/api/v2) para o Sighir Helper AI.

Leitura livre. Escrita só por PATCH em devices/ e telemetries/, campo a campo de uma lista
permitida, e só com confirmação (o helper.py mostra antes/depois e exige --sim).
Sem DELETE: remover cadastro é tarefa do Tester (server-delete), com confirmação do usuário.
Produção é um SQLite num t2.large: pagine de 2000 no máximo e NUNCA use limit=all.
"""

import os
import json
import time
import base64
import requests
import urllib3

urllib3.disable_warnings()

URL  = os.environ.get('SIGHIR_API_URL', 'https://sighir.com:8000/api/v2')
USER = os.environ.get('SIGHIR_API_USER', 'sighir@gmail.com')
PASS = os.environ.get('SIGHIR_API_PASS', 'sighir12345')

# o login custa ~1,3 s (hash de senha no servidor) e o refresh ~0,15 s: guardo os tokens entre
# execuções (access dura 5 min, refresh 24 h) — fora do git, em .sighir/
TOKENS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.sighir', 'token.json')

# desde a migração do servidor (24/09/2026) a instalação é o próprio device (plate → Vehicle,
# telemetry_company = CNPJ, telemetry = módulo); o chip mora no módulo (telemetries/). etilometers/
# virou só leitura aqui: é uma visão dos devices instalados.
WRITABLE = {
    'devices': {'need_update', 'software_version', 'series_num', 'company', 'sensor_id', 'location',
                'plate', 'vehicle_type', 'telemetry', 'telemetry_company', 'installer', 'is_operating',
                'nickname', 'camera_service'},
    'telemetries': {'chip', 'model'},
}


class Api:
    TRIES = 4

    def __init__(self):
        self.session = requests.Session()
        self.session.verify = False
        self.access = None
        self.refresh = None
        self.exp = 0
        self.load()

    @staticmethod
    def expiry(token):
        try:
            part = token.split('.')[1]
            part += '=' * (-len(part) % 4)
            return json.loads(base64.urlsafe_b64decode(part))['exp']
        except Exception:
            return 0

    def load(self):
        try:
            with open(TOKENS, encoding='utf-8') as f:
                data = json.load(f)
            if data.get('url') == URL and data.get('user') == USER:
                self.access, self.refresh = data.get('access'), data.get('refresh')
                self.exp = self.expiry(self.access or '') - 30
        except (OSError, ValueError):
            pass

    def save(self):
        try:
            os.makedirs(os.path.dirname(TOKENS), exist_ok=True)
            with open(TOKENS, 'w', encoding='utf-8') as f:
                json.dump({'url': URL, 'user': USER, 'access': self.access, 'refresh': self.refresh}, f)
        except OSError:
            pass

    def login(self):
        res = self.session.post(f'{URL}/token/', json={'username': USER, 'password': PASS}, timeout=30)
        res.raise_for_status()
        data = res.json()
        self.access, self.refresh = data['access'], data['refresh']
        self.exp = self.expiry(self.access) - 30
        self.save()

    def check(self):
        if self.access and time.time() < self.exp:
            return
        if self.refresh and time.time() < self.expiry(self.refresh) - 30:
            try:
                res = self.session.post(f'{URL}/token/refresh/', json={'refresh': self.refresh}, timeout=30)
                if res.status_code == 200:
                    self.access = res.json()['access']
                    self.exp = self.expiry(self.access) - 30
                    self.save()
                    return
            except requests.RequestException:
                pass
        self.login()

    def request(self, method, endpoint, **kw):
        last = None
        offline = 0
        for n in range(self.TRIES):
            try:
                self.check()
                headers = {'Authorization': f'Bearer {self.access}'}
                res = self.session.request(method, f'{URL}/{endpoint.lstrip("/")}', headers=headers,
                                           timeout=90, **kw)
            except (requests.ConnectionError, requests.Timeout) as err:
                # sem rede/servidor fora: 2 tentativas bastam (evita ~20 s de espera em comando simples)
                last = str(err)
                offline += 1
                if offline >= 2:
                    break
                time.sleep(1)
                continue
            except requests.RequestException as err:
                last = str(err)
                time.sleep(2 * (n + 1))
                continue
            if res.status_code == 401:
                self.exp = 0
                self.access = None
                continue
            if res.status_code >= 500:
                last = f'HTTP {res.status_code}'
                time.sleep(2 * (n + 1))
                continue
            return res
        raise RuntimeError(f'{method} {endpoint} falhou: {last}')

    def get(self, endpoint, **params):
        if str(params.get('limit', '')).lower() in ('all', '0'):
            raise ValueError('limit=all/0 derruba o servidor de produção — use paginação')
        res = self.request('GET', endpoint, params=params)
        if res.status_code == 404:
            return None
        res.raise_for_status()
        return res.json()

    def rows(self, endpoint, limit=500, max_rows=5000, **params):
        """lista paginada seguindo `next` (máx. max_rows linhas)."""
        params['limit'] = min(limit, 2000)
        page, out = 1, []
        while True:
            data = self.get(endpoint, page=page, **params)
            if data is None:
                return out
            if isinstance(data, list):
                return data[:max_rows]
            out += data.get('results', [])
            if not data.get('next') or len(out) >= max_rows:
                return out[:max_rows]
            page += 1

    def patch(self, resource, pk, data):
        allowed = WRITABLE.get(resource)
        if not allowed:
            raise PermissionError(f'escrita bloqueada em {resource}/ (permitido: {", ".join(WRITABLE)})')
        bad = set(data) - allowed
        if bad:
            raise PermissionError(f'campos não permitidos em {resource}: {", ".join(sorted(bad))}')
        res = self.request('PATCH', f'{resource}/{pk}/', json=data)
        if res.status_code not in (200, 202, 204):
            raise RuntimeError(f'PATCH {resource}/{pk} -> {res.status_code}: {res.text[:300]}')
        return res.json() if res.content else {}


api = Api()
