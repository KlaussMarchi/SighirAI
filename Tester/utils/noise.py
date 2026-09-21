import re

# Comandos que o etilômetro emite SOZINHO na serial (não são resposta a nada).
# Origem: docs/hardware/objects/telemetry/. O NextSerial troca o uart para a
# Serial (USB) assim que ela recebe dados (serial/index.h:62-66), então todo o
# tráfego de telemetria — requests periódicos, acks e comandos de bloqueio —
# passa a sair na porta que o tester está lendo. Nada disso deve ser tratado
# como resposta: é lixo do ponto de vista do tester (mas é vital pro device,
# não mexer no firmware).
telemetryNoise = [
    'SttReq',                # suntech: request a cada 2s
    '$ETACK!',               # mix / mix2: keep-alive a cada 5 min
    'AT+QACC?',              # entrack: request de ignição a cada 2s
    'AT+ID?',                # entrack: setup
    'AT+ASSISTMASK0900=2',   # entrack: setup
    'AT+RELAYMODE=1',        # entrack: setup
    'AT+LOG=5',              # entrack: setup
]

# Mesma coisa, mas com parte variável (id do módulo, número da porta, pinos).
noisePatterns = [
    r'CMD;[^;]*;04;0[12]',              # suntech: bloqueio / desbloqueio
    r'AT\+GPIOVALUE=\d+,\d+',           # entrack: bloqueio / desbloqueio
    r'\+QACC:(high|low)',               # entrack: resposta de ignição do módulo
    r'port changed to \d+',             # debug do NextSerial
    r'Serial2 Started at RX=\d+ e TX=\d+',
]


class NoiseFilter:
    def __init__(self):
        self.tokens   = list(telemetryNoise)
        self.patterns = [re.compile(pattern) for pattern in noisePatterns]

    def getTokens(self, keep=None):
        """Tokens a remover. Um token cujo texto se confunda com o alvo do
        expect() é preservado — o protocol.json, por exemplo, espera 'SttReq'
        como resposta no teste do Suntech."""
        keeps = [item for item in (keep or []) if item]

        if not keeps:
            return self.tokens

        return [token for token in self.tokens
                if not any(token in item or item in token for item in keeps)]

    def clean(self, text, keep=None):
        """Remove o lixo de telemetria e devolve só o conteúdo útil.
        Se a string for lixo puro, o retorno é ''."""
        if not text:
            return ''

        for token in self.getTokens(keep):
            text = text.replace(token, ' ')

        for pattern in self.patterns:
            text = pattern.sub(' ', text)

        return re.sub(r'\s+', ' ', text).strip()

    def isNoise(self, text, keep=None):
        """True quando a string só tem lixo de telemetria (nada aproveitável)."""
        return bool(text) and not self.clean(text, keep)


noise = NoiseFilter()
