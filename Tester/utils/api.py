import requests
from typing import Literal

from utils.functions import (
    is_token_expiring, 
    api_exception_handler, 
    paginate_request, 
    extract_filename_from_disposition
)

BASE_URL = 'https://sighir.com:8000'
API      = f'{BASE_URL}/api/v2'
USER     = 'sighir@gmail.com'
PASS     = 'Acesso@Sighir01'

# ----------------------------------- Gerenciamento de Tokens -----------------------------------
stored_access_token  = ''
stored_refresh_token = ''

def set_tokens(access: str, refresh: str):
    global stored_access_token, stored_refresh_token
    stored_access_token = access or ''
    stored_refresh_token = refresh or ''

def fetch_access_token():
    r = requests.post(
        f"{API}/token/",
        json={"username": USER, "password": PASS},
        headers={"Content-Type": "application/json"},
        allow_redirects=True,
        timeout=30
    )

    result = r.json()
    if not r.ok:
        raise Exception(result.get('detail', 'Não foi possível obter token de autenticação'))

    access  = result.get("access", "")
    refresh = result.get("refresh", "")

    if not access or not refresh:
        raise Exception("Resposta de token inválida (sem access/refresh).")
    
    return access, refresh

def fetch_refresh_token(refresh_token):
    r = requests.post(
        f"{API}/token/refresh/",
        json={"refresh": refresh_token},
        headers={"Content-Type": "application/json"},
        allow_redirects=True,
        timeout=30
    )

    result = r.json()
    if not r.ok:
        fresh_access, fresh_refresh = fetch_access_token()
        set_tokens(fresh_access, fresh_refresh)
        raise Exception(result.get('detail', 'Erro ao dar refresh no token de autenticação'))

    access  = result.get("access", "")
    refresh = result.get("refresh") or refresh_token

    if not access or not refresh:
        raise Exception("Resposta de token inválida (sem access/refresh).")
    
    return access, refresh

def handle_access_token():
    """
    Garante que temos tokens válidos em cache:
    - Se não houver, faz login.
    - Se o access estiver perto de expirar, faz refresh.
    Retorna (access, refresh) atualizados.
    """
    global stored_access_token, stored_refresh_token

    access, refresh = stored_access_token, stored_refresh_token

    if access and is_token_expiring(access):
        access, refresh = fetch_refresh_token(refresh)

    if not access or not refresh:
        access, refresh = fetch_access_token()
    
    set_tokens(access, refresh)
    return access, refresh

# ----------------------------------- Consulta à API -----------------------------------
def handle_api_response(resp: requests.Response):
    """
    Converte httpx.Response em dict padronizado:
      - JSON com paginação (results/next/previous)
      - Texto puro
      - Binário (bytes + filename extraído de content-disposition)
    """
    content_type = resp.headers.get('content-type', '')
    disposition  = resp.headers.get('content-disposition', '')
    content_len  = resp.headers.get('Content-Length', '')

    if not content_len or content_len == '0':
        return { "status": "success", "data": None }

    if 'application/json' in content_type:
        data = resp.json()
        if isinstance(data, dict) and 'results' in data:
            return {
                "status": "success",
                "data": data.get("results"),
                "next": data.get("next"),
                "previous": data.get("previous"),
            }
        return {"status": "success", "data": data}

    if content_type.startswith('text/'):
        text_data = resp.text
        return {"status": "success", "data": text_data}

    # Caso binário
    blob     = resp.content 
    filename = extract_filename_from_disposition(disposition, default="download")
    return {"status": "success", "data": {"bytes": blob, "filename": filename}}

@paginate_request(default_until=0)
@api_exception_handler
def get_req(endpoint, use_base_url=False, custom_error_msg=''):
    headers   = {}
    access, _ = handle_access_token()
    prefix    = BASE_URL if use_base_url else API
    headers['Authorization'] = f'Bearer {access}'

    url = endpoint if endpoint.startswith('http') else prefix + endpoint

    r = requests.get(url, headers=headers, allow_redirects=True, timeout=30)

    if not r.ok:
        result = r.json()
        error_msg = result.get('detail', 'Erro desconhecido')
        raise Exception(custom_error_msg if custom_error_msg else error_msg)

    return handle_api_response(r)

@api_exception_handler
def delete_req(endpoint, use_base_url=False, custom_error_msg=''):
    """DELETE de verdade (hard delete). ATENÇÃO: `deleted=True` via PATCH NÃO
    apaga nada — nenhum queryset do servidor filtra por `deleted` (é só um query
    param opcional do IncrementalMixin), o registro continua visível em tudo.
    Os ViewSets são ModelViewSet puros, sem override de destroy => DELETE remove.
    Chaves estrangeiras caem em cascata (apagar um Device leva o Suntech junto)."""
    headers   = {}
    access, _ = handle_access_token()
    prefix    = BASE_URL if use_base_url else API
    headers['Authorization'] = f'Bearer {access}'

    if not endpoint.startswith('http') and not endpoint.endswith('/'):
        endpoint += '/'

    url = endpoint if endpoint.startswith('http') else prefix + endpoint
    r = requests.delete(url, headers=headers, allow_redirects=True, timeout=30)

    if not r.ok:
        result = r.json()
        error_msg = result.get('detail', 'Erro desconhecido')
        raise Exception(custom_error_msg if custom_error_msg else error_msg)

    return {"status": "success", "data": None}

@paginate_request(default_until=0)
@api_exception_handler
def post_req(endpoint, data, type: Literal['POST', 'PATCH'] = 'POST', use_base_url=False, custom_error_msg=''):
    headers   = {}
    access, _ = handle_access_token()
    prefix    = BASE_URL if use_base_url else API
    headers['Authorization'] = f'Bearer {access}'

    if endpoint.startswith('http'):
        url = endpoint
    else:
        if not endpoint.endswith('/'):
            endpoint += '/'
        url = prefix + endpoint

    if type == 'POST':
        req_func = requests.post
    else:
        req_func = requests.patch

    r = req_func(url, json=data, headers=headers, allow_redirects=True, timeout=30)

    if not r.ok:
        result = r.json()
        error_msg = result.get('detail', 'Erro desconhecido')
        raise Exception(custom_error_msg if custom_error_msg else error_msg)

    return handle_api_response(r)