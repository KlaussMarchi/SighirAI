"""
Gera docs/fluxograma_tester.pdf a partir de fluxograma_tester.html (Chrome/Edge headless).

    python docs/tools/fluxograma/render.py [--previa PASTA] [--dpi 110]

1ª passada: abre a página, deixa o layout rodar e lê a conferência automática (nós sobrepostos,
setas atravessando caixas, rótulos encostando, texto cortado, conteúdo invadindo o rodapé).
2ª passada: imprime o PDF A4 paisagem, com marcadores (um por página) e links internos.
--previa: salva cada página como PNG (pdftoppm) para revisar o resultado.

As fotos e telas dos anexos vêm de docs/Notion/ (export do Notion, fora do git).
"""
import os
import re
import sys
import json
import shutil
import argparse
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
HTML = HERE / 'fluxograma_tester.html'
OUT = HERE.parent.parent / 'fluxograma_tester.pdf'

CANDIDATES = [
    r'C:\Program Files\Google\Chrome\Application\chrome.exe',
    r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
    r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
    r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
]


def findBrowser():
    for name in ('google-chrome', 'chromium', 'chromium-browser', 'chrome', 'msedge'):
        path = shutil.which(name)
        if path:
            return path
    return next((c for c in CANDIDATES if os.path.exists(c)), None)


def run(browser, *args):
    base = [browser, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--no-first-run',
            '--virtual-time-budget=5000', '--allow-file-access-from-files', '--window-size=1122,793']
    return subprocess.run(base + list(args), capture_output=True, text=True, encoding='utf-8', errors='replace',
                          timeout=180)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--previa', help='pasta onde salvar cada página como PNG (para revisão)')
    p.add_argument('--dpi', type=int, default=110)
    p.add_argument('--geo', help='mostra x, y, largura e altura de cada caixa deste fluxo (ex.: f2)')
    args = p.parse_args()

    browser = findBrowser()
    if not browser:
        print('Chrome/Edge não encontrado')
        return 1
    url = HTML.as_uri()

    missing = [m for m in re.findall(r'src="([^"]+)"', HTML.read_text(encoding='utf-8'))
               if not (HERE / m).resolve().exists()]
    if missing:
        print('imagens não encontradas (o export do Notion está em docs/Notion?):')
        for m in sorted(set(missing)):
            print('  -', m)

    dom = run(browser, '--dump-dom', url).stdout
    report = re.search(r'data-qa="([^"]*)"', dom)
    if not (re.search(r'data-done="1"', dom) and report):
        print('a página não terminou o layout (data-done ausente)')
        return 1
    unescape = lambda t: t.replace('&quot;', '"').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    issues = json.loads(unescape(report.group(1)))
    if args.geo:
        geo = json.loads(unescape(re.search(r'data-geo="([^"]*)"', dom).group(1)))
        for nid, (x, y, w, h) in geo.get(args.geo, {}).items():
            print(f'  {nid:5} x {x:5} .. {x + w:5}   y {y:4} .. {y + h:4}   ({w}x{h})')

    if OUT.exists():
        OUT.unlink()
    res = run(browser, f'--print-to-pdf={OUT}', '--no-pdf-header-footer', '--generate-pdf-document-outline', url)
    if not OUT.exists():
        print(res.stderr[-2000:])
        return 1
    print(f'PDF: {OUT}  ({OUT.stat().st_size / 1e6:.1f} MB)')

    if shutil.which('pdfinfo'):
        info = subprocess.run(['pdfinfo', str(OUT)], capture_output=True, text=True).stdout
        pages = re.search(r'Pages:\s+(\d+)', info)
        size = re.search(r'Page size:\s+(.+)', info)
        print(f"páginas: {pages.group(1) if pages else '?'} · {size.group(1).strip() if size else ''}")

    if args.previa:
        out = Path(args.previa)
        out.mkdir(parents=True, exist_ok=True)
        subprocess.run(['pdftoppm', '-r', str(args.dpi), '-png', str(OUT), str(out / 'pagina')], check=True)
        print(f'prévias: {out}')

    print(f'conferência: {len(issues)} problema(s)')
    for i in issues:
        print('  -', i)
    return 0 if not issues else 2


if __name__ == '__main__':
    sys.exit(main())
