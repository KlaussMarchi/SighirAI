import base64
import requests
import functools
from time import sleep
from time import time as getTime
import sys, os, unidecode, re, json

def millis():
    return int(getTime()*1000)

def sendEvent(eventType, message, color='blue', delay=0.0, end='\n', top='', repeat=False):
    status = eventType

    pythonColors = {
        'black'     : '\033[30m',
        'red'       : '\033[31m',
        'green'     : '\033[32m',
        'yellow'    : '\033[33m',
        'blue'      : '\033[34m',
        'magenta'   : '\033[35m', 
        'cyan'      : '\033[36m',
        'white'     : '\033[37m',
        'orange'    : '\033[38;5;208m',
        'gray'      : '\033[38;5;244m',
        'light_gray': '\033[38;5;250m',
        'dark_gray' : '\033[38;5;240m',
        'brown'     : '\033[38;5;94m',
        'purple'    : '\033[38;5;129m',
        'reset'     : '\033[0m'
    }
    
    if eventType == 'success':
        status = True
        color  = 'blue'

    if eventType == 'error':
        status = False
        color  = 'red'

    if eventType == 'event':
        status = None
        color = 'green'

    status  = True if eventType == 'success' else False if eventType == 'error' else None
    color   = pythonColors[color]
    reset   = pythonColors['white']

    if repeat:
        print(f'{top}{color}[{eventType}]{reset}', message, f'{color}[{eventType}]{reset}', end=end)
    else:
        print(f'{top}{color}[{eventType}]{reset}', message, end=end)    

    if delay > 0.0: 
        sleep(delay)

    return status


# RETORNA CAMINHO FUNCIONANDO COM PYINSTALLER
def getPath(path):
    try:
        basePath = sys._MEIPASS
    except Exception:
        basePath = os.path.abspath(".")

    return os.path.join(basePath, path)



def cleanText(sentence):
    sentence = sentence.lower().strip().replace(' ', '')
    sentence = unidecode.unidecode(sentence) 
    sentence = re.sub(r'[^a-zA-Z0-9\s]', '', sentence) 
    sentence = re.sub(r'\s+', ' ', sentence).strip() 
    return sentence


def showLogo(version):
    print()
    print(f'''                                                                                                                                                                                                                
                @@@@@@@@@@@@@@   @@@@@@@@  @@@@@@@@@@@@@@@   @@@@@@@  @@@@@@@@ @@@@@@@@  @@@@@@@@@@@@@@@               
              @@@@@@@@@@@@@@@@@@ @@@@@@@@ @@@@@@@@@@@@@@@@@ @@@@@@@@  @@@@@@@@ @@@@@@@@  @@@@@@@@@@@@@@@@@             
              @@@@@@@@@@@@@@@@@@ @@@@@@@@ @@@@@@@@@@@@@@@@@ @@@@@@@@  @@@@@@@@ @@@@@@@@  @@@@@@@@@@@@@@@@@             
              @@@@@@@@@@@@@@@@@@ @@@@@@@@ @@@@@@@@@@@@@@@@@ @@@@@@@@  @@@@@@@@ @@@@@@@@  @@@@@@@@@@@@@@@@@             
              @@@@@@@@           @@@@@@@@ @@@@@@@@          @@@@@@@@  @@@@@@@@ @@@@@@@@  @@@@@@@  @@@@@@@@             
              @@@@@@@@@@@@@@@@@  @@@@@@@@ @@@@@@@@  @@@@@@@ @@@@@@@@@@@@@@@@@@ @@@@@@@@  @@@@@@@@@@@@@@@@@             
              @@@@@@@@@@@@@@@@@@ @@@@@@@@ @@@@@@@@  @@@@@@@ @@@@@@@@@@@@@@@@@@ @@@@@@@@  @@@@@@@@@@@@@@@@              
               @@@@@@@@@@@@@@@@@ @@@@@@@@ @@@@@@@@  @@@@@@@ @@@@@@@@@@@@@@@@@@ @@@@@@@@  @@@@@@@@@@@@@@@@@             
                        @@@@@@@@ @@@@@@@@ @@@@@@@@  @@@@@@@ @@@@@@@@  @@@@@@@@ @@@@@@@@  @@@@@@@  @@@@@@@@             
              @@@@@@@@  @@@@@@@@ @@@@@@@@ @@@@@@@@  @@@@@@@ @@@@@@@@  @@@@@@@@ @@@@@@@@  @@@@@@@  @@@@@@@@             
              @@@@@@@@@@@@@@@@@@ @@@@@@@@ @@@@@@@@@@@@@@@@@ @@@@@@@@  @@@@@@@@ @@@@@@@@  @@@@@@@  @@@@@@@@             
              @@@@@@@@@@@@@@@@@@ @@@@@@@@ @@@@@@@@@@@@@@@@@ @@@@@@@@  @@@@@@@@ @@@@@@@@  @@@@@@@  @@@@@@@@             
               @@@@@@@@@@@@@@@@  @@@@@@@@  @@@@@@@@@@@@@@@@  @@@@@@@  @@@@@@@@ @@@@@@@@  @@@@@@@  @@@@@@@@             
                                                    {version}                                                                                                                                                                                               
       '''
    )

def b64url_decode(segment: str) -> bytes:
    padding = '=' * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)

def decode_jwt(token: str):
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return {}
        payload_bytes = b64url_decode(parts[1])
        return json.loads(payload_bytes.decode('utf-8'))
    except Exception:
        return {}

def is_token_expiring(token: str, leeway = 60) -> bool:
    payload = decode_jwt(token)
    exp = payload.get('exp')
    now = int(getTime())
    if not isinstance(exp, int):
        return True
    return (exp - now) <= leeway

def api_exception_handler(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        request_path = kwargs.get('request', args[0] if args else '')  # Para exibir no log
        try:
            return func(*args, **kwargs)
        except requests.exceptions.HTTPError as e:
            msg = f"({request_path}) - Erro HTTP: {e.response.status_code if e.response else 'desconhecido'} - {e}"
        except requests.exceptions.Timeout as e:
            msg = f"({request_path}) - Timeout: {e}"
        except requests.exceptions.RequestException as e:
            msg = f"({request_path}) - Erro de requisição: {e}"
        except Exception as e:
            msg = f"({request_path}) - Erro inesperado: {e}"

        return {"status": "error", "data": msg}
    
    return wrapper

def paginate_request(default_until=0, custom_error_msg=''):
    """
    Decorador que adiciona paginação automática à função decorada.

    A função decorada deve retornar um dicionário no formato:
        {
            "status": "success" | "error",
            "data": [...],
            "next": <url ou None>
        }

    O parâmetro 'until' pode ser definido dinamicamente na chamada da função:
        get_req('/endpoint/', until=3)
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(endpoint, *args, **kwargs):
            # Se o chamador passou `until`, usa ele; caso contrário, usa o default
            until = kwargs.pop('until', default_until)
            custom_msg = kwargs.pop('custom_error_msg', custom_error_msg)

            result = func(endpoint, *args, **kwargs)

            if result.get('status') == 'error':
                return result

            # Caso seja apenas a primeira página
            if not result.get('next') or until == 1:
                return result

            remaining = until - 1 if until > 0 else 0
            count = 0

            while result.get('next') and (until == 0 or count < remaining):
                next_result = func(result['next'], *args, **kwargs)

                if next_result.get('status') == 'error':
                    return next_result
                if not next_result.get('data'):
                    break

                result['data'].extend(next_result['data'])
                result['next'] = next_result.get('next')
                count += 1

            return result
        return wrapper
    return decorator

def extract_filename_from_disposition(disposition: str, default: str = "download") -> str:
    # RFC 6266 (simplificado)
    m = re.search(r'filename[^;=\n]*=((["\']).*?\2|[^;\n]*)', disposition or '', re.IGNORECASE)
    if not m:
        return default
    filename = m.group(1).strip().strip('\'"')
    return filename or default