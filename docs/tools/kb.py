#!/usr/bin/env python3
"""
kb.py — indexador e busca da base de conhecimento Sighir (pasta docs/).

Compartilhado pelas três IAs (Tester, Server, Helper). Só usa a biblioteca padrão;
para PDF usa o `pdftotext` (poppler) se existir, senão o `pypdf` se estiver instalado.

    python kb.py atualizar            extrai texto do que mudou, regenera INDEX.md, casos_notion.md
                                      e troubleshooting.md (da página raiz do Notion sincronizada)
    python kb.py busca termo [termo]  busca sem acento/caixa em tudo que foi indexado
    python kb.py busca termo --codigo inclui o código-fonte do firmware (hardware/Main)
    python kb.py ler main.pdf --pagina 5    lê o texto extraído de um documento
    python kb.py lista                lista o que está indexado
    python kb.py novidades            documentos novos/alterados ainda não revisados
    python kb.py revisado <doc> --descricao "..." --quando "..."   registra a revisão no catálogo
    python kb.py status               extratores disponíveis e frescor do índice

O índice (docs/.index/) é gerado e fica fora do git. O catálogo curado (tools/catalogo.json)
é versionado: é nele que a IA registra, para cada documento, o que ele é e quando consultar.
"""

import os
import re
import sys
import csv
import json
import time
import shutil
import hashlib
import argparse
import subprocess
import unicodedata
from io import StringIO
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

TOOLS    = os.path.dirname(os.path.abspath(__file__))
DOCS     = os.path.dirname(TOOLS)
INDEX    = os.path.join(DOCS, '.index')
TEXTS    = os.path.join(INDEX, 'text')
MANIFEST = os.path.join(INDEX, 'manifest.json')
CATALOG  = os.path.join(TOOLS, 'catalogo.json')
INDEX_MD = os.path.join(DOCS, 'INDEX.md')
CASES_MD = os.path.join(DOCS, 'casos_notion.md')
TROUBLE_MD = os.path.join(DOCS, 'troubleshooting.md')
# gerados e refeitos a cada sincronização: fora do índice/novidades, mas entram na busca
GENERATED = ('INDEX.md', 'casos_notion.md', 'notion_mapa.md', 'servidor_resumo.md')
NOTION_CFG = os.path.join(TOOLS, 'notion.json')
FIRMWARE = os.path.join(DOCS, 'hardware', 'Main')

TEXT_EXT  = {'.md', '.txt'}
IMAGE_EXT = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
CODE_EXT  = {'.h', '.ino', '.cpp', '.c'}
SKIP_DIRS = {'.index', '.git', '__pycache__', 'tools', 'build'}
AUTO_BEGIN = '<!-- KB:AUTO:BEGIN -->'
AUTO_END   = '<!-- KB:AUTO:END -->'
NOTION_ID  = re.compile(r'\s+[0-9a-f]{32}')
BOILER     = ('Inclua uma visão geral da tarefa e detalhes relacionados.',
              '[https://app.notion.com](https://app.notion.com)')


def say(msg=''):
    print(msg, flush=True)


def norm(text):
    """minúsculas e sem acento: 'Resolução' e 'resolucao' casam."""
    text = unicodedata.normalize('NFKD', text or '')
    return ''.join(c for c in text if not unicodedata.combining(c)).lower()


def rel(path):
    return os.path.relpath(path, DOCS).replace('\\', '/')


def cleanName(name):
    """tira o ID de 32 hex que o Notion cola no nome dos arquivos."""
    base, ext = os.path.splitext(name)
    return NOTION_ID.sub('', base).replace('_all', '').strip() + ext


def keyOf(relpath):
    """chave estável de um documento: caminho sem os IDs do Notion (que mudam a cada export),
    normalizado. Mantém o sufixo _all: o Notion exporta X.csv e X_all.csv, que são arquivos distintos."""
    parts = []
    for part in relpath.split('/'):
        base, ext = os.path.splitext(part)
        parts.append(NOTION_ID.sub('', base).strip() + ext)
    return norm('/'.join(parts))


def sha1(path):
    h = hashlib.sha1()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def loadJson(path, default):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def saveJson(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=1, sort_keys=True)
    os.replace(tmp, path)


# ----------------------------------------------------------------- extração

def findPdftotext():
    found = shutil.which('pdftotext')
    if found:
        return found

    candidates = []
    for base in (os.environ.get('ProgramFiles', r'C:\Program Files'),
                 os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)'),
                 os.environ.get('LOCALAPPDATA', '')):
        if not base:
            continue
        candidates += [os.path.join(base, 'Git', 'mingw64', 'bin', 'pdftotext.exe'),
                       os.path.join(base, 'Programs', 'Git', 'mingw64', 'bin', 'pdftotext.exe')]
        try:
            for name in os.listdir(base):
                if name.lower().startswith('poppler'):
                    candidates += [os.path.join(base, name, 'Library', 'bin', 'pdftotext.exe'),
                                   os.path.join(base, name, 'bin', 'pdftotext.exe')]
        except OSError:
            pass

    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def hasPypdf():
    try:
        import pypdf  # noqa: F401
        return True
    except Exception:
        return False


def pdfText(path):
    """texto do PDF com \\f entre páginas. Retorna (texto, motor) ou (None, motivo)."""
    exe = findPdftotext()
    if exe:
        try:
            out = subprocess.run([exe, '-enc', 'UTF-8', path, '-'], capture_output=True, timeout=180)
            if out.returncode == 0:
                return out.stdout.decode('utf-8', errors='replace'), 'pdftotext'
        except (OSError, subprocess.SubprocessError):
            pass

    try:
        from pypdf import PdfReader
        reader = PdfReader(path)
        return '\f'.join((page.extract_text() or '') for page in reader.pages), 'pypdf'
    except ImportError:
        return None, 'sem extrator de PDF (instale poppler/pdftotext ou pip install pypdf)'
    except Exception as err:
        return None, f'pypdf falhou: {err}'


def csvText(path):
    raw = open(path, encoding='utf-8-sig', errors='replace').read()
    rows = list(csv.reader(StringIO(raw)))
    if not rows:
        return ''
    head = rows[0]
    lines = []
    for row in rows[1:]:
        pairs = [f'{h}: {v}' for h, v in zip(head, row) if v.strip()]
        if pairs:
            lines.append(' | '.join(pairs))
    return '\n'.join(lines)


def xlsxText(path):
    try:
        import openpyxl
    except ImportError:
        return None
    try:
        book = openpyxl.load_workbook(path, read_only=True, data_only=True)
        out = []
        for sheet in book.worksheets:
            out.append(f'## Aba {sheet.title}')
            for row in sheet.iter_rows(values_only=True):
                cells = [str(c) for c in row if c not in (None, '')]
                if cells:
                    out.append(' | '.join(cells))
        return '\n'.join(out)
    except Exception:
        return None


def extract(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in TEXT_EXT:
        return open(path, encoding='utf-8', errors='replace').read(), 'texto'
    if ext == '.csv':
        return csvText(path), 'csv'
    if ext == '.pdf':
        return pdfText(path)
    if ext == '.xlsx':
        text = xlsxText(path)
        return (text, 'xlsx') if text is not None else (None, 'openpyxl ausente')
    return None, 'sem texto'


def titleOf(text, relpath):
    for line in (text or '').splitlines():
        line = line.strip().strip('#').strip()
        if len(line) >= 4 and not line.startswith(('---', '|', '<')):
            return line[:110]
    return cleanName(os.path.basename(relpath))


# ----------------------------------------------------------------- varredura

def walkDocs():
    for root, dirs, files in os.walk(DOCS):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith('.'))
        relroot = rel(root)
        if relroot.startswith('hardware/Main'):
            dirs[:] = []
            continue
        for name in sorted(files):
            if name.startswith('.') or name in GENERATED:
                continue
            yield os.path.join(root, name)


def update(force=False, quiet=False):
    writeTroubleshooting()      # antes da varredura: o arquivo gerado já entra no índice desta rodada
    old = loadJson(MANIFEST, {})
    new = {}
    seen_hash = {}
    changed, added, extracted, problems = [], [], 0, []
    os.makedirs(TEXTS, exist_ok=True)

    for path in walkDocs():
        relpath = rel(path)
        ext = os.path.splitext(path)[1].lower()
        stat = os.stat(path)
        prev = old.get(relpath)

        if prev and not force and prev.get('size') == stat.st_size and prev.get('mtime') == int(stat.st_mtime):
            entry = prev
        else:
            digest = sha1(path)
            if prev and prev.get('sha1') == digest and not force and \
               (not prev.get('text') or os.path.exists(os.path.join(INDEX, prev['text']))):
                entry = dict(prev, size=stat.st_size, mtime=int(stat.st_mtime))
            else:
                entry = {'size': stat.st_size, 'mtime': int(stat.st_mtime), 'sha1': digest,
                         'ext': ext, 'key': keyOf(relpath)}
                if ext in IMAGE_EXT:
                    entry.update(kind='imagem', title=cleanName(os.path.basename(path)))
                elif ext == '.sqlite3':
                    entry.update(kind='banco', title='snapshot do banco de produção (SQLite)')
                else:
                    text, engine = extract(path)
                    if text is None:
                        entry.update(kind='sem-texto', title=cleanName(os.path.basename(path)), note=engine)
                        if ext == '.pdf':
                            problems.append(f'{relpath}: {engine}')
                    else:
                        name = hashlib.sha1(relpath.encode('utf-8')).hexdigest()[:16] + '.txt'
                        with open(os.path.join(TEXTS, name), 'w', encoding='utf-8') as f:
                            f.write(text)
                        entry.update(kind=ext.lstrip('.'), engine=engine, text='text/' + name,
                                     chars=len(text), pages=(text.count('\f') + 1) if ext == '.pdf' else None,
                                     title=titleOf(text, relpath))
                        extracted += 1
                (added if not prev else changed).append(relpath)

        entry = dict(entry, key=keyOf(relpath))
        # o Notion exporta X.csv e X_all.csv, muitas vezes com o mesmo conteúdo: indexo uma vez só
        dup = seen_hash.get(entry.get('sha1'))
        entry = dict(entry, alias_of=dup) if dup else {k: v for k, v in entry.items() if k != 'alias_of'}
        seen_hash.setdefault(entry.get('sha1'), relpath)
        new[relpath] = entry

    removed = sorted(set(old) - set(new))
    for relpath in removed:
        textfile = old[relpath].get('text')
        if textfile and os.path.exists(os.path.join(INDEX, textfile)):
            os.remove(os.path.join(INDEX, textfile))

    saveJson(MANIFEST, new)
    writeCases(new)
    writeIndex(new)

    if not quiet or added or changed or removed or problems:
        say(f'kb: {len(new)} arquivos no índice | extraídos agora: {extracted} | '
            f'novos: {len(added)} | alterados: {len(changed)} | removidos: {len(removed)}')
        for tag, items in (('novo', added), ('alterado', changed), ('removido', removed)):
            for item in items[:15]:
                say(f'  [{tag}] {item}')
            if len(items) > 15:
                say(f'  ... +{len(items) - 15} {tag}s')
        for item in problems:
            say(f'  [aviso] {item}')
        pend = pending(new)
        if pend:
            say(f'  {len(pend)} documento(s) sem revisão no catálogo — veja: python kb.py novidades')
    return new


# ----------------------------------------------------------------- catálogo e INDEX.md

def pending(manifest):
    """documentos relevantes (PDF, md fora do Notion, planilhas) sem revisão registrada."""
    catalog = loadJson(CATALOG, {})
    out = []
    for relpath, entry in manifest.items():
        if entry.get('alias_of') or entry.get('kind') in ('imagem', 'banco'):
            continue
        interesting = entry.get('ext') in ('.pdf', '.xlsx') or \
            (entry.get('ext') == '.md' and not relpath.startswith('Notion/')) or \
            isCasesTable(relpath)
        if not interesting:
            continue
        item = catalog.get(entry['key'])
        if not item or item.get('sha1') != entry.get('sha1'):
            out.append(relpath)
    return sorted(out)


def isCasesTable(relpath):
    n = norm(relpath)
    return 'resolucao de problemas' in n and n.endswith('.csv')


def describe(entry):
    catalog = loadJson(CATALOG, {})
    item = catalog.get(entry.get('key'), {})
    return item.get('descricao'), item.get('quando')


def human(size):
    for unit in ('B', 'KB', 'MB', 'GB'):
        if size < 1024:
            return f'{size:.0f} {unit}'
        size /= 1024
    return f'{size:.0f} TB'


def writeIndex(manifest):
    now = datetime.now().strftime('%d/%m/%Y %H:%M')
    groups = {'curados': [], 'hardware': [], 'notion_pdf': [], 'notion_tab': [], 'notion_pag': {},
              'imagens': 0, 'outros': []}

    for relpath, entry in sorted(manifest.items()):
        if entry.get('alias_of'):
            continue
        kind = entry.get('kind')
        if kind == 'imagem':
            groups['imagens'] += 1
        elif relpath.startswith('Notion/'):
            if entry.get('ext') == '.pdf':
                groups['notion_pdf'].append((relpath, entry))
            elif entry.get('ext') in ('.csv', '.xlsx'):
                groups['notion_tab'].append((relpath, entry))
            else:
                folder = cleanName(relpath.split('/')[1]) if relpath.count('/') > 1 else '(raiz)'
                groups['notion_pag'].setdefault(folder, []).append(relpath)
        elif relpath.startswith('hardware/'):
            groups['hardware'].append((relpath, entry))
        elif '/' not in relpath and entry.get('ext') == '.md':
            groups['curados'].append((relpath, entry))
        else:
            groups['outros'].append((relpath, entry))

    fw = firmwareVersion()
    pend = set(pending(manifest))
    lines = [AUTO_BEGIN, '',
             f'## Catálogo automático (gerado por `tools/kb.py atualizar` em {now})', '',
             'Não edite este bloco à mão: descrições vêm de `tools/catalogo.json` '
             '(registre com `kb.py revisado`). ⚠ = novo/alterado e ainda não revisado.', '']

    def row(relpath, entry, extra=''):
        desc, when = describe(entry)
        mark = ' ⚠' if relpath in pend else ''
        text = desc or entry.get('title') or ''
        if when:
            text += f' — *quando:* {when}'
        return f'| `{relpath}`{mark} | {text}{extra} |'

    lines += ['### Documentos curados (docs/*.md)', '', '| arquivo | conteúdo |', '|---|---|']
    lines += [row(r, e) for r, e in groups['curados']]
    lines += ['', '### Firmware (docs/hardware/)', '',
              f'Código-fonte real do etilômetro em `hardware/Main/` (versão no `Main.ino`: **{fw or "?"}**). '
              'Busque no código com `kb.py busca termo --codigo`.', '',
              '| arquivo | conteúdo |', '|---|---|']
    lines += [row(r, e) for r, e in groups['hardware']]
    lines += ['', '### Notion — PDFs (manuais, protocolos, procedimentos)', '',
              '| arquivo | conteúdo |', '|---|---|']
    for relpath, entry in groups['notion_pdf']:
        pages = f' ({entry["pages"]} p.)' if entry.get('pages') else ''
        if entry.get('kind') == 'sem-texto':
            pages += f' — sem texto: {entry.get("note")}'
        lines.append(row(relpath, entry, pages))
    lines += ['', '### Notion — tabelas (bancos exportados)', '', '| arquivo | conteúdo |', '|---|---|']
    lines += [row(r, e) for r, e in groups['notion_tab']]
    if groups['notion_pag']:
        lines += ['', '### Notion — páginas (.md) por pasta', '']
        for folder, items in sorted(groups['notion_pag'].items()):
            lines.append(f'- **{folder}**: {len(items)} página(s)')
    if groups['outros']:
        lines += ['', '### Outros', '', '| arquivo | conteúdo |', '|---|---|']
        lines += [row(r, e, f' ({human(e.get("size", 0))})') for r, e in groups['outros']]
    lines += ['', f'Imagens soltas indexadas por nome: {groups["imagens"]}. '
              'Chamados de campo resumidos em `casos_notion.md` (gerado).', '', AUTO_END]
    block = '\n'.join(lines)

    try:
        current = open(INDEX_MD, encoding='utf-8').read()
    except OSError:
        current = '# Base de conhecimento Sighir\n\n'
    if AUTO_BEGIN in current and AUTO_END in current:
        head = current.split(AUTO_BEGIN)[0]
        tail = current.split(AUTO_END, 1)[1]
        text = head + block + tail
    else:
        text = current.rstrip() + '\n\n' + block + '\n'

    # só regrava se o conteúdo mudou (a data sozinha não conta — evita diff no git a cada sessão)
    def undated(value):
        return re.sub(r'em \d{2}/\d{2}/\d{4} \d{2}:\d{2}\)', 'em -)', value)

    if undated(text) != undated(current):
        with open(INDEX_MD, 'w', encoding='utf-8') as f:
            f.write(text)


def notionAge():
    """frase curta sobre a última sincronização do Notion (Notion/.sync.json do notion_sync.py)."""
    state = loadJson(os.path.join(DOCS, 'Notion', '.sync.json'), {})
    when = state.get('atualizado')
    if not when:
        return 'Notion: nunca sincronizado (export manual) — "sincronizar os documentos" atualiza'
    try:
        from datetime import timezone
        days = (datetime.now(timezone.utc) - datetime.fromisoformat(when)).total_seconds() / 86400
    except ValueError:
        return None
    text = f"Notion sincronizado há {days:.0f} dia(s)" if days >= 1 else 'Notion sincronizado hoje'
    return text + (' — sugira "sincronizar os documentos"' if days >= 14 else '')


def firmwareVersion():
    try:
        src = open(os.path.join(FIRMWARE, 'Main.ino'), encoding='utf-8', errors='replace').read()
        m = re.search(r'Device\s+device\s*\{\s*"([^"]+)"', src)
        return m.group(1) if m else None
    except OSError:
        return None


# ----------------------------------------------------------------- casos do Notion

def parsePage(path):
    """página de chamado do Notion: título, propriedades e seções com conteúdo real."""
    text = open(path, encoding='utf-8', errors='replace').read()
    title, props, sections, current = None, {}, {}, None
    for line in text.splitlines():
        if line.startswith('# ') and title is None:
            title = line[2:].strip()
            continue
        if line.startswith('## '):
            current = line[3:].strip()
            sections[current] = []
            continue
        if current is None:
            m = re.match(r'^([^:]{2,40}):\s*(.*)$', line)
            if m:
                props[m.group(1).strip()] = m.group(2).strip()
            continue
        clean = line.strip()
        if not clean or clean in ('- [ ]', '- [ ]  ') or any(b in clean for b in BOILER):
            continue
        clean = re.sub(r'!\[[^\]]*\]\(([^)]*)\)', r'[imagem: \1]', clean)
        sections[current].append(clean)
    return title, props, sections


def writeCases(manifest):
    pages = sorted(r for r in manifest
                   if 'resolucao de problemas/' in norm(r) and r.endswith('.md') and r.count('/') == 2)
    if not pages:
        return
    cases = []
    for relpath in pages:
        title, props, sections = parsePage(os.path.join(DOCS, relpath))
        date = props.get('Data', '')
        m = re.match(r'(\d{2})/(\d{2})/(\d{4})', date)
        order = f'{m.group(3)}{m.group(2)}{m.group(1)}' if m else '0'
        cases.append((order, title, props, sections, relpath))
    cases.sort(key=lambda c: c[0], reverse=True)

    out = ['# Chamados de campo (Notion → Resolução de Problemas)', '',
           f'> **Gerado automaticamente** por `tools/kb.py atualizar` em {datetime.now():%d/%m/%Y %H:%M} '
           'a partir do export do Notion. Não edite: atualize o Notion, reexporte para `docs/Notion/` '
           'e rode o `kb.py atualizar`. As lições consolidadas ficam em `diagnostico.md`.', '',
           f'Total: {len(cases)} chamados.', '',
           '| data | placa | empresa | problema | tipo | status | solução? |', '|---|---|---|---|---|---|---|']
    for order, title, props, sections, relpath in cases:
        solved = 'sim' if sections.get('Solução') else '—'
        out.append(f"| {props.get('Data', '')[:10]} | {props.get('Placa do Veículo', '')} | "
                   f"{props.get('Empresa', '')} | {title} | {props.get('Tipo de problema', '')} | "
                   f"{props.get('Status', '')} | {solved} |")
    out.append('')
    for order, title, props, sections, relpath in cases:
        out += [f"## {title} — {props.get('Placa do Veículo', '?')} ({props.get('Data', '')[:10]})", '']
        meta = [f'{k}: {v}' for k, v in props.items() if v]
        out.append('- ' + ' · '.join(meta))
        for name, body in sections.items():
            if name.startswith('Arquivos') or not body:
                continue
            if name.startswith('Informações'):
                filled = [b for b in body if not re.match(r'^- [^:]+:\s*$', b)]
                if not filled:
                    continue
                body = filled
            out.append(f'- **{name}:** ' + ' '.join(b.lstrip('- ').strip() for b in body))
        out += [f'- Fonte: `{relpath}`', '']
    text = '\n'.join(out)
    try:
        if open(CASES_MD, encoding='utf-8').read().split('\n', 4)[4:] == text.split('\n', 4)[4:]:
            return
    except OSError:
        pass
    with open(CASES_MD, 'w', encoding='utf-8') as f:
        f.write(text)


# ----------------------------------------------------------------- troubleshooting (Notion)

def rootPage():
    """a página raiz sincronizada (ex.: Notion/Sighir Enterprise <id>.md), se existir."""
    cfg = loadJson(NOTION_CFG, {})
    root = cfg.get('raiz') or {}
    folder = os.path.join(DOCS, 'Notion')
    if not root.get('id') or not os.path.isdir(folder):
        return None
    for name in os.listdir(folder):
        if name.endswith('.md') and root['id'] in name.replace('-', ''):
            return os.path.join(folder, name)
    return None


def writeTroubleshooting():
    """extrai a seção "Troubleshooting" da página raiz do Notion para docs/troubleshooting.md
    (toggles viram títulos; os subtítulos sobem de nível). Sem a página raiz, não mexe no arquivo."""
    page = rootPage()
    if not page:
        return
    lines = open(page, encoding='utf-8', errors='replace').read().split('\n')
    start = level = None
    for i, line in enumerate(lines):
        m = re.match(r'^(#{1,6})\s+(.*)$', line)
        if m and norm(m.group(2)).strip() == 'troubleshooting':
            start, level = i, len(m.group(1))
            break
    if start is None:
        return
    body = []
    for line in lines[start + 1:]:
        m = re.match(r'^(#{1,6})\s+(.*)$', line)
        if m and len(m.group(1)) <= level:
            break
        if m:
            line = '#' * max(2, len(m.group(1)) - level + 1) + ' ' + m.group(2)
        line = re.sub(r'\]\((?!https?:|#)([^)]+)\)', r'](Notion/\1)', line)
        body.append(line)
    text = '\n'.join(['# Troubleshooting de campo (checklists da equipe)', '',
                      f'> **Gerado automaticamente** por `tools/kb.py atualizar` em {datetime.now():%d/%m/%Y %H:%M} a '
                      f'partir do Notion (Sighir Enterprise → Suporte → Troubleshooting, `{rel(page)}`).',
                      '> Não edite aqui: edite no Notion e sincronize ("sincronizar os documentos" → '
                      '`sincronizar.md`).',
                      '> A versão por sintoma — causas, evidências no servidor e no firmware — está em `diagnostico.md`; '
                      'os menus citados estão em `operacao_telas.md` §7 ("Configurações, página 2, Teste Serial" = '
                      'CONFIG 2 → **Teste de Telemetria**).', '']
                     + body).rstrip() + '\n'
    text = re.sub(r'\n{3,}', '\n\n', text)
    try:
        if open(TROUBLE_MD, encoding='utf-8').read().split('\n', 3)[3:] == text.split('\n', 3)[3:]:
            return
    except OSError:
        pass
    with open(TROUBLE_MD, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)


# ----------------------------------------------------------------- busca

STOPWORDS = {'a', 'o', 'as', 'os', 'e', 'de', 'da', 'do', 'das', 'dos', 'em', 'no', 'na', 'nos', 'nas',
             'com', 'para', 'por', 'um', 'uma', 'que', 'se', 'ao', 'the', 'of', 'and', 'or'}


def docText(relpath, entry):
    if not entry.get('text'):
        return ''
    try:
        return open(os.path.join(INDEX, entry['text']), encoding='utf-8', errors='replace').read()
    except OSError:
        return ''


def numbered(text):
    """[(linha, página, texto)] — páginas separadas por \\f (pdftotext/pypdf). splitlines()
    não serve: ele também quebra no \\f e a contagem de páginas se perde."""
    out, lineno = [], 0
    for page, chunk in enumerate(text.split('\f'), 1):
        for line in chunk.split('\n'):
            lineno += 1
            out.append((lineno, page, line.rstrip('\r')))
    return out


def codeFiles():
    for root, dirs, files in os.walk(FIRMWARE):
        dirs[:] = [d for d in dirs if d not in ('assets', 'build') and not d.startswith('.')]
        for name in files:
            path = os.path.join(root, name)
            if os.path.splitext(name)[1].lower() in CODE_EXT and os.path.getsize(path) < 300_000:
                yield path


def search(terms, limit=8, folder=None, code=False, per_doc=3):
    manifest = loadJson(MANIFEST, {})
    if not manifest:
        manifest = update(quiet=True)
    phrase = ' '.join(norm(t) for t in terms).strip()
    words = [w for w in re.split(r'\s+', phrase) if w]
    wanted = [w for w in words if w not in STOPWORDS] or words
    wanted = list(dict.fromkeys(wanted))
    if not wanted:
        say('informe ao menos um termo')
        return 1

    corpus = []
    for relpath, entry in manifest.items():
        if entry.get('alias_of') or not entry.get('text'):
            continue
        if folder and not norm(relpath).startswith(norm(folder)):
            continue
        corpus.append((relpath, entry.get('title', ''), docText(relpath, entry)))
    for relpath in GENERATED:
        path = os.path.join(DOCS, relpath)
        if os.path.exists(path) and (not folder or norm(relpath).startswith(norm(folder))):
            corpus.append((relpath, relpath, open(path, encoding='utf-8', errors='replace').read()))
    if code:
        for path in codeFiles():
            corpus.append((rel(path), 'firmware', open(path, encoding='utf-8', errors='replace').read()))

    docfreq = {t: 0 for t in wanted}
    prepared = []
    for relpath, title, text in corpus:
        low = norm(text)
        counts = {t: low.count(t) for t in wanted}
        for t in wanted:
            docfreq[t] += 1 if counts[t] else 0
        if any(counts.values()):
            prepared.append((relpath, title, text, low, counts))

    total = max(len(corpus), 1)
    ranked = []
    for relpath, title, text, low, counts in prepared:
        hits = sum(1 for t in wanted if counts[t])
        score = 0.0
        for t in wanted:
            if counts[t]:
                idf = 1.0 + (total / (1 + docfreq[t])) ** 0.5
                score += (1 + (counts[t] ** 0.5)) * idf
        score *= hits / len(wanted)
        if len(wanted) > 1 and phrase in low:
            score *= 1.8
        if relpath.endswith('.md') and '/' not in relpath:
            score *= 1.25
        ranked.append((score, hits, relpath, title, text))
    ranked.sort(key=lambda r: (-r[1], -r[0]))

    if not ranked:
        say(f'nada encontrado para: {" ".join(terms)}')
        return 1

    say(f'{len(ranked)} documento(s) com "{" ".join(terms)}" — mostrando {min(limit, len(ranked))}:')
    for n, (score, hits, relpath, title, text) in enumerate(ranked[:limit], 1):
        say(f'\n[{n}] {relpath}  ({hits}/{len(wanted)} termos) — {title[:90]}')
        best = []
        for lineno, page, line in numbered(text):
            low = norm(line)
            got = sum(1 for t in wanted if t in low) + (2 if len(wanted) > 1 and phrase in low else 0)
            if got:
                best.append((got, lineno, page, line.strip()))
        best.sort(key=lambda b: (-b[0], b[1]))
        for got, lineno, pg, line in sorted(best[:per_doc], key=lambda b: b[1]):
            where = f'p.{pg} L{lineno}' if relpath.endswith('.pdf') else f'L{lineno}'
            say(f'    {where}: {line[:220]}')
    say('\nabrir: python kb.py ler <arquivo> [--pagina N | --linhas A-B | --grep termo]')
    return 0


def findDoc(name, manifest):
    if name in manifest:
        return name
    target = norm(name.replace('\\', '/'))
    hits = [r for r in manifest if norm(r).endswith(target) or target in norm(cleanName(os.path.basename(r)))]
    hits = [h for h in hits if not manifest[h].get('alias_of')] or hits
    if len(hits) == 1:
        return hits[0]
    if hits:
        exact = [h for h in hits if norm(os.path.basename(h)) == target]
        if len(exact) == 1:
            return exact[0]
        say('mais de um documento casa com esse nome:')
        for h in hits[:20]:
            say(f'  {h}')
        return None
    say(f'nenhum documento indexado casa com: {name}')
    return None


def read(name, page=None, lines=None, grep=None):
    manifest = loadJson(MANIFEST, {}) or update(quiet=True)
    relpath = findDoc(name, manifest)
    if not relpath:
        return 1
    entry = manifest[relpath]
    if entry.get('alias_of'):
        relpath, entry = entry['alias_of'], manifest[entry['alias_of']]
    text = docText(relpath, entry)
    if not text:
        say(f'{relpath}: sem texto extraído ({entry.get("note") or entry.get("kind")})')
        return 1
    say(f'== {relpath} ({entry.get("pages") or "-"} p., {entry.get("chars", len(text))} caracteres)')
    rows = numbered(text)
    if page:
        total = rows[-1][1] if rows else 1
        if not 1 <= page <= total:
            say(f'página fora do intervalo 1-{total}')
            return 1
        rows = [r for r in rows if r[1] == page]
    if lines:
        a, _, b = lines.partition('-')
        a = max(int(a or 1), 1)
        b = int(b) if b else a + 80
        rows = [r for r in rows if a <= r[0] <= b]
    if grep:
        g = norm(grep)
        for lineno, pg, row in rows:
            if g in norm(row):
                say(f'p.{pg} L{lineno}: {row}' if entry.get('pages') else f'L{lineno}: {row}')
        return 0
    for lineno, pg, row in rows:
        say(row)
    return 0


# ----------------------------------------------------------------- revisão

def listDocs(folder=None):
    manifest = loadJson(MANIFEST, {}) or update(quiet=True)
    for relpath, entry in sorted(manifest.items()):
        if folder and not norm(relpath).startswith(norm(folder)):
            continue
        extra = f' [{entry.get("pages")} p.]' if entry.get('pages') else ''
        alias = f' (= {entry["alias_of"]})' if entry.get('alias_of') else ''
        say(f'{relpath}{extra}{alias} — {entry.get("title", "")[:80]}')
    return 0


def novidades():
    manifest = loadJson(MANIFEST, {}) or update(quiet=True)
    pend = pending(manifest)
    if not pend:
        say('nenhuma novidade: todos os documentos relevantes estão revisados no catálogo.')
        return 0
    say(f'{len(pend)} documento(s) novos ou alterados desde a última revisão:')
    for relpath in pend:
        entry = manifest[relpath]
        pages = f', {entry["pages"]} p.' if entry.get('pages') else ''
        say(f'  - {relpath} ({entry.get("chars", 0)} caracteres{pages}) — {entry.get("title", "")[:80]}')
    say('\nPara cada um: leia (kb.py ler), incorpore fatos novos nos docs curados que couberem '
        '(diagnostico.md, telemetrias.md...) e registre: '
        'kb.py revisado "<arquivo>" --descricao "o que é" --quando "quando consultar"')
    return 0


def reviewed(names, descricao=None, quando=None, everything=False):
    manifest = loadJson(MANIFEST, {}) or update(quiet=True)
    catalog = loadJson(CATALOG, {})
    targets = pending(manifest) if everything else []
    for name in names or []:
        found = findDoc(name, manifest)
        if found:
            targets.append(found)
    if not targets:
        say('nada para registrar')
        return 1
    for relpath in dict.fromkeys(targets):
        entry = manifest[relpath]
        item = catalog.get(entry['key'], {})
        item.update(arquivo=relpath, sha1=entry.get('sha1'), revisado=datetime.now().strftime('%Y-%m-%d'))
        if descricao:
            item['descricao'] = descricao
        if quando:
            item['quando'] = quando
        catalog[entry['key']] = item
        say(f'revisado: {relpath}')
    saveJson(CATALOG, catalog)
    writeIndex(manifest)
    return 0


def status():
    manifest = loadJson(MANIFEST, {})
    exe = findPdftotext()
    say(f'docs: {DOCS}')
    say(f'pdftotext: {exe or "não encontrado"} | pypdf: {"sim" if hasPypdf() else "não"}')
    if not manifest:
        say('índice: ainda não gerado (rode: python kb.py atualizar)')
        return 1
    age = (time.time() - os.path.getmtime(MANIFEST)) / 3600
    kinds = {}
    for entry in manifest.values():
        kinds[entry.get('kind')] = kinds.get(entry.get('kind'), 0) + 1
    say(f'índice: {len(manifest)} arquivos, atualizado há {age:.1f} h | ' +
        ', '.join(f'{k}={v}' for k, v in sorted(kinds.items(), key=lambda kv: str(kv[0]))))
    say(f'firmware em hardware/Main: {firmwareVersion() or "ausente"}')
    say(f'pendentes de revisão: {len(pending(manifest))}')
    say(notionAge() or '')
    return 0


def main():
    p = argparse.ArgumentParser(prog='kb', description='Base de conhecimento Sighir (docs/)')
    sub = p.add_subparsers(dest='cmd', required=True)

    a = sub.add_parser('atualizar', help='indexa o que mudou e regenera INDEX.md/casos_notion.md')
    a.add_argument('--forcar', action='store_true', help='reextrai tudo')
    a.add_argument('--silencioso', action='store_true', help='só fala se algo mudou')
    a.add_argument('--json', action='store_true', help='só um resumo em JSON (usado pelo boot.py das IAs)')

    b = sub.add_parser('busca', help='busca termos (sem acento/caixa)')
    b.add_argument('termos', nargs='+')
    b.add_argument('-n', type=int, default=8, help='máximo de documentos')
    b.add_argument('--pasta', help='restringe a uma pasta (ex.: Notion, hardware)')
    b.add_argument('--codigo', action='store_true', help='inclui o código-fonte do firmware')

    r = sub.add_parser('ler', help='mostra o texto extraído de um documento')
    r.add_argument('nome')
    r.add_argument('--pagina', type=int)
    r.add_argument('--linhas', help='intervalo, ex.: 120-200')
    r.add_argument('--grep', help='só as linhas que contêm o termo')

    l = sub.add_parser('lista', help='lista o que está indexado')
    l.add_argument('--pasta')

    sub.add_parser('novidades', help='documentos novos/alterados sem revisão no catálogo')

    v = sub.add_parser('revisado', help='registra a revisão de documentos no catálogo')
    v.add_argument('nomes', nargs='*')
    v.add_argument('--descricao')
    v.add_argument('--quando')
    v.add_argument('--tudo', action='store_true', help='marca todos os pendentes (sem descrição)')

    sub.add_parser('status', help='extratores e frescor do índice')

    args = p.parse_args()
    if args.cmd == 'atualizar':
        if args.json:
            import contextlib
            with contextlib.redirect_stdout(StringIO()) as log:
                manifest = update(force=args.forcar, quiet=True)
            changes = [l.strip() for l in log.getvalue().splitlines() if l.strip().startswith('[')]
            print(json.dumps({'arquivos': len(manifest), 'pendentes': len(pending(manifest)),
                              'firmware': firmwareVersion(), 'notion': notionAge(), 'mudancas': changes[:12]},
                             ensure_ascii=False))
            return 0
        update(force=args.forcar, quiet=args.silencioso)
        return 0
    if args.cmd == 'busca':
        return search(args.termos, args.n, args.pasta, args.codigo)
    if args.cmd == 'ler':
        return read(args.nome, args.pagina, args.linhas, args.grep)
    if args.cmd == 'lista':
        return listDocs(args.pasta)
    if args.cmd == 'novidades':
        return novidades()
    if args.cmd == 'revisado':
        return reviewed(args.nomes, args.descricao, args.quando, args.tudo)
    if args.cmd == 'status':
        return status()
    return 1


if __name__ == '__main__':
    sys.exit(main())
