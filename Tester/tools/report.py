import os, platform, subprocess
from datetime import datetime
from tools import session
from tools.quality import STEPS

ROOT    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION = 1    # VERSÃO DO FORMATO DO default_settings.report QUE O SERVIDOR RENDERIZA (ESPECIFICAÇÃO COM O JEAN)
STATUS  = {True: 'aprovado', False: 'reprovado', None: 'nao_realizado'}


def testerVersion():
    try:
        out = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], cwd=ROOT, capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return None

    return out.stdout.strip() or None


# RELATÓRIO DE ENSAIO DE UM APARELHO COMO DADOS: VAI NO default_settings.report E O SERVIDOR GERA O PDF NO PORTAL
class Report:
    def __init__(self, esp, technician, notes):
        self.esp        = esp
        self.technician = technician
        self.notes      = notes
        self.events     = session.load(esp)
        self.now        = datetime.now()

    def update(self):
        self.quality = {e['etapa']: e for e in self.events if e['tipo'] == 'qualidade'}    # A ÚLTIMA RODADA DE CADA ETAPA VALE
        self.verdict = self.judge()
        device       = self.last('aparelho')
        temp         = self.data('temperatura')
        moments      = sorted(e['quando'] for e in self.events if e.get('quando'))
        blow         = next((self.data(step)['blowProb'] for step in STEPS if self.data(step).get('blowProb')), None)
        version      = testerVersion()

        self.report = {
            'versao': VERSION,
            'numero': f"RT-{self.now:%Y%m%d-%H%M}-{self.esp[-4:]}",
            'emitido_em': self.now.isoformat(timespec='seconds'),
            'tecnico': self.technician,
            'observacoes': self.notes or '',
            'software': 'Sighir Tester AI' + (f' ({version})' if version else ''),
            'sistema': f'{platform.system()} {platform.release()}',
            'periodo': {'inicio': moments[0], 'fim': moments[-1]} if moments else None,
            'veredito': self.verdict,
            'aparelho': {
                'esp_id': self.esp,
                'sensor_id': device.get('sensor_id'),
                'firmware': next((e['depois'] for e in reversed(self.events) if e['tipo'] == 'flash' and e.get('depois')), device.get('firmware')),
                'firmware_minimo': device.get('minimo'),
                'sensor_producao': None if not device else not device.get('debug'),
                'telemetria': device.get('telemetria')
            },
            'ambiente': {'temperatura': temp['temperatura']['media'], 'umidade': temp['umidade']['media']} if temp.get('temperatura') and temp.get('umidade') else None,
            'blow_prob': float(blow) if blow else None,
            'configuracao': self.last('configuracao').get('alteradas') if self.last('configuracao') else None,
            'firmware': [{key: e.get(key) for key in ('quando', 'antes', 'depois', 'build', 'empresa', 'ok', 'detalhe')}
                         for e in self.events if e['tipo'] == 'flash'],
            'ensaios': [self.test(step) for step in STEPS]
        }
        return self.report

    # APTO SÓ COM TODOS OS ENSAIOS DO PROCEDIMENTO FEITOS E APROVADOS, FIRMWARE NO MÍNIMO E SENSOR DE PRODUÇÃO
    def judge(self):
        device  = self.last('aparelho')
        failed  = [step for step in STEPS if step in self.quality and not self.quality[step]['ok']]
        missing = [step for step in STEPS if step not in self.quality]
        blocked = [text for bad, text in [(device.get('status') not in (None, 'ok'), f"firmware {device.get('firmware')} abaixo do mínimo {device.get('minimo')}"),
                                          (device.get('debug'), 'sensor de debug (build de bancada)')] if bad]
        score   = {'aprovados': len(STEPS) - len(failed) - len(missing), 'total': len(STEPS)}

        if not self.quality:
            return {'codigo': 'nao_realizado', 'titulo': 'ENSAIO NÃO REALIZADO', **score,
                    'texto': 'Nenhum ensaio de qualidade foi registrado para este aparelho: o relatório não atesta o funcionamento.'}

        if failed or blocked:
            return {'codigo': 'reprovado', 'titulo': 'REPROVADO — NÃO LIBERAR', **score,
                    'texto': 'Reprovado em: ' + ', '.join([STEPS[step][0] for step in failed] + blocked) + '.'}

        if missing:
            return {'codigo': 'incompleto', 'titulo': 'ENSAIO INCOMPLETO — NÃO LIBERAR', **score,
                    'texto': f'{len(missing)} ensaio(s) do procedimento não realizado(s): ' + ', '.join(STEPS[step][0] for step in missing) + '.'}

        return {'codigo': 'apto', 'titulo': 'APTO PARA PRODUÇÃO', **score,
                'texto': 'Todos os ensaios do procedimento aprovados em bancada: sensores, calibração, sopro e testes reais.'}

    def test(self, step):
        entry = self.quality.get(step) or {}
        return {'id': step, 'nome': STEPS[step][0], 'criterio': STEPS[step][1], 'situacao': STATUS[entry['ok'] if entry else None],
                'medido': entry.get('medido'), 'detalhe': entry.get('detalhe'), 'quando': entry.get('quando'), 'dados': entry.get('dados') or {}}

    def last(self, kind):
        return next((e for e in reversed(self.events) if e['tipo'] == kind), {})

    def data(self, step):
        return (self.quality.get(step) or {}).get('dados') or {}
