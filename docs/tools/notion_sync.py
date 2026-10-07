#!/usr/bin/env python3
"""
notion_sync.py — sincroniza o Notion da Sighir com docs/Notion/ (base compartilhada das três IAs).

Só usa a biblioteca padrão. Grava no mesmo formato do export "Markdown & CSV" do Notion
(`Título <id>.md`, `Banco <id>_all.csv`, pasta do banco com uma página por linha), então o `kb.py`
e o `casos_notion.md` funcionam igual — e depois da sincronização ele roda o `kb.py atualizar`,
que também regenera o `troubleshooting.md` a partir da página raiz.

Dois caminhos, mesmo resultado:
  • API do Notion (token de integração): Claude ou Gemini, Windows ou Linux.
        python notion_sync.py token ntn_xxx        guarda o token (docs/.notion_token, fora do git)
        python notion_sync.py sincronizar          incremental: só baixa o que mudou no Notion
        python notion_sync.py sincronizar --limpar remove arquivos locais que não existem mais no Notion
  • Conector Notion do Claude (sem token): a IA busca pelo MCP e entrega o resultado bruto aqui.
        python notion_sync.py plano                o roteiro (ids, fontes, o que buscar)
        python notion_sync.py mcp-banco ID arq     linhas de um banco (query "rows") → CSV + lista do que buscar
        python notion_sync.py mcp-pagina arq...    página (resultado do fetch) → .md
        python notion_sync.py mcp-fim              fecha: estado + kb.py atualizar + resumo

    python notion_sync.py status                   token, última sincronização, pendências

Configuração versionada em tools/notion.json (raiz, seções omitidas, bancos). Estado em
docs/Notion/.sync.json. Seções com senha (ex.: "Credenciais") nunca são gravadas.
"""

import os
import re
import sys
import csv
import json
import time
import hashlib
import argparse
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from io import StringIO
from datetime import datetime, timedelta, timezone

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

TOOLS      = os.path.dirname(os.path.abspath(__file__))
DOCS       = os.path.dirname(TOOLS)
NOTION     = os.path.join(DOCS, 'Notion')
STATE      = os.path.join(NOTION, '.sync.json')
CONFIG     = os.path.join(TOOLS, 'notion.json')
TOKEN_FILE = os.path.join(DOCS, '.notion_token')
API        = 'https://api.notion.com/v1'
VERSION    = '2022-06-28'
BRT        = timezone(timedelta(hours=-3))
ID32       = re.compile(r'([0-9a-f]{8})-?([0-9a-f]{4})-?([0-9a-f]{4})-?([0-9a-f]{4})-?([0-9a-f]{12})')
TITLE_KEYS = ('Nome', 'Name', 'Problema', 'Título', 'Titulo', 'Title', 'Tarefa', 'title')


def say(msg=''):
    print(msg, flush=True)


def norm(text):
    text = unicodedata.normalize('NFKD', text or '')
    return ''.join(c for c in text if not unicodedata.combining(c)).lower().strip()


def rel(path):
    return os.path.relpath(path, DOCS).replace('\\', '/')


def hexid(value):
    """qualquer forma de id do Notion (url, uuid com hífen) → 32 hex."""
    m = ID32.search((value or '').lower())
    return ''.join(m.groups()) if m else None


def uuid(value):
    h = hexid(value)
    return f'{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}' if h else value


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
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def safeName(title, limit=50):
    """nome de arquivo como o export do Notion: 50 caracteres, sem os proibidos no Windows."""
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', (title or '').replace('\n', ' '))
    name = re.sub(r'\s+', ' ', name).strip()[:limit].strip().rstrip('.')
    return name or 'Sem título'


def brt(value):
    """ISO do Notion → '28/08/2025 18:03 (BRT)' (formato do export; o kb.py lê DD/MM/AAAA)."""
    if not value:
        return ''
    if len(value) == 10:
        try:
            return datetime.strptime(value, '%Y-%m-%d').strftime('%d/%m/%Y')
        except ValueError:
            return value
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return value
    if dt.tzinfo:
        dt = dt.astimezone(BRT)
    return f'{dt:%d/%m/%Y %H:%M} (BRT)'


def writeText(path, text):
    """grava só se mudou; devolve 'novo', 'alterado' ou '' (igual)."""
    existed = os.path.exists(path)
    if existed:
        with open(path, encoding='utf-8', errors='replace') as f:
            if f.read() == text:
                return ''
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)
    return 'alterado' if existed else 'novo'


# ----------------------------------------------------------------- conteúdo sensível

SECRET = re.compile(r'(?i)(\**\s*(senha|password|passwd|token|api[_ ]?key)\s*\**\s*[:=]\s*\**\s*)(\S.*)$')


def scrub(md, sections):
    """tira as seções cujo título contém um item de `sections` (até o próximo título do mesmo
    nível ou acima) e mascara linhas 'Senha: ...' que tenham sobrado em qualquer lugar."""
    wanted = [norm(s) for s in sections]
    out, skipping = [], None
    for line in md.split('\n'):
        m = re.match(r'^(#{1,6})\s+(.*)$', line.strip())
        if m:
            level = len(m.group(1))
            if skipping is not None and level <= skipping:
                skipping = None
            if skipping is None and any(w and w in norm(m.group(2)) for w in wanted):
                skipping = level
                continue
        if skipping is not None:
            continue
        out.append(SECRET.sub(lambda s: s.group(1) + '[omitido]', line) if 'CF:' not in line else line)
    return '\n'.join(out)


GENERIC_TOGGLES = {'abrir', 'ver', 'ver mais', 'mais', 'detalhes', 'expandir', 'clique aqui'}


def toggleHead(text, depth, pad):
    """toggle → título (### no 1º nível, igual nos dois caminhos). Toggle genérico ("Abrir") não vira
    título: o conteúdo segue no fluxo do item de cima."""
    if norm(re.sub(r'[*`]', '', text)) in GENERIC_TOGGLES or not text.strip():
        return []
    level = 3 + depth
    return ['', '#' * level + ' ' + text, ''] if level <= 6 else [pad + f'**{text}**']


# ----------------------------------------------------------------- estado

class State:
    def __init__(self):
        self.data = loadJson(STATE, {})
        self.data.setdefault('itens', {})     # id → {tipo, titulo, arquivo, editado, pasta, filhos, anexos, hash}
        self.seen = set()                     # arquivos (rel. a docs/) produzidos nesta rodada
        self.changed, self.added = [], []
        self.before = {i.get('arquivo') for i in self.data['itens'].values() if i.get('arquivo')}
        for item in self.data['itens'].values():
            self.before |= set(item.get('anexos') or [])

    def item(self, nid):
        return self.data['itens'].get(nid)

    def put(self, nid, **fields):
        item = self.data['itens'].setdefault(nid, {})
        item.update(fields)
        return item

    def mark(self, path, how):
        """how: 'novo' / 'alterado' / '' (sem mudança)."""
        r = rel(path)
        self.seen.add(r)
        target = self.added if how == 'novo' else self.changed if how else None
        if target is not None and r not in self.added and r not in self.changed:
            target.append(r)

    def folderFor(self, nid, parent, title):
        """pasta das linhas de um banco / subpáginas: estável entre rodadas; nomes repetidos no mesmo
        lugar ganham o sufixo do export ('Tarefas 2af7-dae8')."""
        item = self.item(nid) or {}
        if item.get('pasta'):
            return os.path.join(DOCS, item['pasta'])
        base = safeName(title)
        taken = {i.get('pasta') for k, i in self.data['itens'].items() if k != nid and i.get('pasta')}
        path = os.path.join(parent, base)
        if rel(path) in taken:
            path = os.path.join(parent, f'{base} {nid[:4]}-{nid[-4:]}')
        self.put(nid, pasta=rel(path))
        return path

    def save(self, engine, final=False):
        """no caminho MCP cada comando é um processo: o que mudou vai se acumulando em 'sessao'
        até o mcp-fim."""
        if engine == 'mcp':
            sess = self.data.setdefault('sessao', {})
            for key, items in (('novos', self.added), ('alterados', self.changed), ('vistos', self.seen)):
                sess.setdefault(key, [])
                sess[key] += [r for r in items if r not in sess[key]]
            self.added, self.changed = [], []
        if final or engine == 'api':
            self.data['atualizado'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
            self.data['motor'] = engine
        saveJson(STATE, self.data)


# ----------------------------------------------------------------- anexos

class Files:
    """baixa anexos (PDF, imagem) e escolhe nomes estáveis; nomes repetidos na mesma pasta viram
    'main 1.pdf', 'main 2.pdf' (como no export)."""

    def __init__(self, state, max_mb):
        self.state, self.max = state, max_mb * 1024 * 1024
        self.claimed = {}   # (pasta, nome minúsculo) → chave do anexo
        self.failed = []

    def target(self, folder, name, key):
        stem, ext = os.path.splitext(safeName(name, 120))
        n = 0
        while True:
            cand = f'{stem}{" " + str(n) if n else ""}{ext}'
            owner = self.claimed.get((folder, cand.lower()))
            if owner in (None, key):
                self.claimed[(folder, cand.lower())] = key
                return os.path.join(folder, cand)
            n += 1

    def fetch(self, url, folder, name, key, edited=None):
        """devolve o caminho local (ou None). Não baixa de novo se o anexo não mudou."""
        known = self.state.data.setdefault('anexos', {}).get(key)
        if known and os.path.exists(os.path.join(DOCS, known['arquivo'])) and \
                (edited is None or known.get('editado') == edited):
            path = os.path.join(DOCS, known['arquivo'])
            self.claimed[(folder, os.path.basename(path).lower())] = key
            self.state.mark(path, '')
            return path
        path = self.target(folder, name, key)
        if not url:
            return path if os.path.exists(path) else None
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'sighir-notion-sync'})
            with urllib.request.urlopen(req, timeout=120) as resp:
                size = int(resp.headers.get('Content-Length') or 0)
                if size > self.max:
                    self.failed.append(f'{name}: {size // 1048576} MB (acima do limite)')
                    return None
                data = resp.read(self.max + 1)
            if len(data) > self.max:
                self.failed.append(f'{name}: acima do limite')
                return None
        except Exception as err:
            if os.path.exists(path):        # URL assinada expirou, mas o arquivo já existe
                self.state.mark(path, '')
                return path
            self.failed.append(f'{name}: {err}')
            return None
        os.makedirs(folder, exist_ok=True)
        how = 'novo'
        try:
            how = 'alterado' if open(path, 'rb').read() != data else ''
        except OSError:
            pass
        wrote = bool(how)
        if wrote:
            with open(path, 'wb') as f:
                f.write(data)
        self.state.data['anexos'][key] = {'arquivo': rel(path), 'editado': edited}
        self.state.mark(path, how)
        return path


def link(path, base):
    return urllib.parse.quote(os.path.relpath(path, base).replace('\\', '/'))


# ----------------------------------------------------------------- API do Notion

def findToken():
    for var in ('NOTION_TOKEN', 'SIGHIR_NOTION_TOKEN'):
        if os.environ.get(var, '').strip():
            return os.environ[var].strip(), f'variável {var}'
    try:
        token = open(TOKEN_FILE, encoding='utf-8').read().strip()
        if token:
            return token, rel(TOKEN_FILE)
    except OSError:
        pass
    return None, None


class NotionError(Exception):
    pass


class Rest:
    def __init__(self, token):
        self.token = token
        self.calls = 0

    def call(self, method, path, body=None):
        url = path if path.startswith('http') else API + path
        data = json.dumps(body).encode() if body is not None else None
        for attempt in range(6):
            req = urllib.request.Request(url, data=data, method=method, headers={
                'Authorization': f'Bearer {self.token}', 'Notion-Version': VERSION,
                'Content-Type': 'application/json', 'User-Agent': 'sighir-notion-sync'})
            try:
                self.calls += 1
                with urllib.request.urlopen(req, timeout=60) as resp:
                    return json.loads(resp.read().decode('utf-8'))
            except urllib.error.HTTPError as err:
                detail = err.read().decode('utf-8', 'replace')[:300]
                if err.code == 429 or err.code >= 500:
                    time.sleep(float(err.headers.get('Retry-After') or 2 ** attempt))
                    continue
                if err.code == 401:
                    raise NotionError('token recusado (401): confira o token da integração')
                if err.code == 404:
                    raise NotionError(f'não encontrado ou sem acesso (404) — a integração precisa ser '
                                      f'conectada à página raiz no Notion (••• → Conexões): {path}')
                raise NotionError(f'HTTP {err.code} em {path}: {detail}')
            except (urllib.error.URLError, TimeoutError, ConnectionError) as err:
                if attempt >= 3:
                    raise NotionError(f'sem conexão com a API do Notion: {err}')
                time.sleep(2 ** attempt)
        raise NotionError(f'API do Notion não respondeu: {path}')

    def paged(self, method, path, body=None):
        out, cursor = [], None
        while True:
            if method == 'GET':
                sep = '&' if '?' in path else '?'
                resp = self.call('GET', f'{path}{sep}page_size=100' + (f'&start_cursor={cursor}' if cursor else ''))
            else:
                resp = self.call('POST', path, dict(body or {}, page_size=100, **({'start_cursor': cursor} if cursor else {})))
            out += resp.get('results', [])
            if not resp.get('has_more'):
                return out
            cursor = resp.get('next_cursor')

    def children(self, block_id):
        return self.paged('GET', f'/blocks/{uuid(block_id)}/children')


def richText(items, md=True):
    out = []
    for t in items or []:
        s = t.get('plain_text', '')
        if md and s.strip():
            a = t.get('annotations') or {}
            lead, core, trail = re.match(r'^(\s*)(.*?)(\s*)$', s, re.S).groups()
            if a.get('code'):
                core = f'`{core}`'
            if a.get('bold'):
                core = f'**{core}**'
            if t.get('href') and t.get('type') == 'text':
                core = f'[{core}]({t["href"]})'
            s = lead + core + trail
        out.append(s)
    return ''.join(out)


def propValue(p):
    kind = p.get('type')
    v = p.get(kind)
    if v is None:
        return ''
    if kind in ('title', 'rich_text'):
        return richText(v, md=False).strip()
    if kind in ('select', 'status'):
        return v.get('name', '')
    if kind == 'multi_select':
        return ', '.join(o.get('name', '') for o in v)
    if kind == 'date':
        return brt(v.get('start')) + (f" → {brt(v['end'])}" if v.get('end') else '')
    if kind in ('people',):
        return ', '.join(u.get('name') or u.get('id', '') for u in v)
    if kind in ('created_by', 'last_edited_by'):
        return v.get('name') or v.get('id', '')
    if kind == 'checkbox':
        return 'Yes' if v else 'No'
    if kind in ('created_time', 'last_edited_time'):
        return brt(v)
    if kind == 'formula':
        inner = v.get(v.get('type'))
        return brt(inner.get('start')) if isinstance(inner, dict) else ('' if inner is None else str(inner))
    if kind == 'relation':
        return ', '.join(hexid(r.get('id')) or '' for r in v)
    if kind == 'rollup':
        inner = v.get(v.get('type'))
        if isinstance(inner, list):
            return ', '.join(propValue(i) for i in inner)
        return brt(inner.get('start')) if isinstance(inner, dict) else ('' if inner is None else str(inner))
    if kind == 'files':
        return ', '.join(f.get('name', '') for f in v)
    if kind == 'unique_id':
        return f"{v.get('prefix') or ''}{'-' if v.get('prefix') else ''}{v.get('number')}"
    if kind == 'verification':
        return v.get('state', '')
    return str(v) if not isinstance(v, (dict, list)) else ''


def titleOf(props):
    for p in (props or {}).values():
        if p.get('type') == 'title':
            return richText(p.get('title'), md=False).strip()
    return ''


class RestSync:
    """percorre a árvore a partir da raiz. Página que não mudou (last_edited_time) não é baixada de
    novo; as filhas dela são revisitadas pela lista guardada no estado."""

    def __init__(self, api, state, cfg, full=False):
        self.api, self.state, self.cfg, self.full = api, state, cfg, full
        self.files = Files(state, cfg.get('max_anexo_mb', 60))
        self.visited = set()
        self.tableOnly = [norm(t) for t in cfg.get('so_tabela', [])]
        self.skip = cfg.get('omitir_secoes', [])
        self.fetched = 0
        self.errors = 0

    def isTableOnly(self, title):
        return any(norm(title).startswith(t) for t in self.tableOnly if t)

    # ---- páginas
    def page(self, nid, folder, meta=None, root=False, tableOnly=False, pai=None):
        nid = hexid(nid)
        if not nid or nid in self.visited:
            return
        self.visited.add(nid)
        if meta is None:
            meta = self.api.call('GET', f'/pages/{uuid(nid)}')
        if meta.get('archived') or meta.get('in_trash'):
            return
        props = meta.get('properties') or {}
        title = titleOf(props) or 'Sem título'
        edited = meta.get('last_edited_time')
        path = os.path.join(folder, f'{safeName(title)} {nid}.md')
        sub = folder if root else self.state.folderFor(nid, folder, title)
        tableOnly = tableOnly or self.isTableOnly(title)
        prev = self.state.item(nid) or {}
        if not self.full and prev.get('editado') == edited and prev.get('arquivo') == rel(path) \
                and os.path.exists(path):
            self.state.mark(path, '')
            for a in prev.get('anexos') or []:
                self.state.seen.add(a)
            for kind, cid in prev.get('filhos') or []:
                self.child(kind, cid, sub, tableOnly, nid)
            return
        self.fetched += 1
        lines = [f'# {title}', '']
        isRow = (meta.get('parent') or {}).get('type') == 'database_id'
        if isRow:
            for name, p in props.items():
                if p.get('type') == 'title':
                    continue
                value = propValue(p)
                if value:
                    lines.append(f'{name}: {value}')
            lines.append('')
        ctx = {'folder': sub, 'base': os.path.dirname(path), 'kids': [], 'attach': []}
        lines += self.blocks(nid, ctx, 0, 0)
        text = scrub(re.sub(r'\n{3,}', '\n\n', '\n'.join(lines)).strip() + '\n', self.skip)
        self.state.mark(path, writeText(path, text))
        self.state.put(nid, tipo='pagina', titulo=title, arquivo=rel(path), editado=edited,
                       filhos=ctx['kids'], anexos=ctx['attach'], pai=pai)
        for kind, cid in ctx['kids']:
            self.child(kind, cid, sub, tableOnly, nid)

    def child(self, kind, cid, folder, tableOnly, pai=None):
        try:
            if kind == 'db':
                self.database(cid, folder, tableOnly, pai)
            else:
                self.page(cid, folder, tableOnly=tableOnly, pai=pai)
        except NotionError as err:
            self.errors += 1
            say(f'   aviso: {err}')

    # ---- bancos
    def database(self, nid, folder, tableOnly=False, pai=None):
        nid = hexid(nid)
        if not nid or nid in self.visited:
            return
        self.visited.add(nid)
        conf = self.cfg.get('bancos', {}).get(nid, {})
        if conf:
            folder = NOTION        # bancos da configuração ficam no topo, como no export
        meta = self.api.call('GET', f'/databases/{uuid(nid)}')
        title = richText(meta.get('title'), md=False).strip() or conf.get('titulo') or 'Sem título'
        tableOnly = (tableOnly or self.isTableOnly(title)) and not conf.get('paginas')
        rows = self.api.paged('POST', f'/databases/{uuid(nid)}/query')
        schema = list((meta.get('properties') or {}).items())
        cols = [n for n, p in schema if p.get('type') == 'title'] + \
               [n for n, p in schema if p.get('type') != 'title']
        buf = StringIO()
        w = csv.writer(buf, lineterminator='\n')
        w.writerow(cols)
        for row in rows:
            w.writerow([propValue(row['properties'][c]) if c in row.get('properties', {}) else '' for c in cols])
        csvPath = os.path.join(folder, f'{safeName(title)} {nid}_all.csv')
        self.state.mark(csvPath, writeText(csvPath, '﻿' + buf.getvalue()))
        sub = self.state.folderFor(nid, folder, title)
        self.state.put(nid, tipo='banco', titulo=title, arquivo=rel(csvPath), linhas=len(rows), pai=pai)
        if tableOnly:
            return
        for row in rows:
            try:
                self.page(row['id'], sub, meta=row, tableOnly=tableOnly, pai=nid)
            except NotionError as err:
                self.errors += 1
                say(f'   aviso: {err}')

    # ---- blocos → markdown
    def blocks(self, parent, ctx, toggle, indent):
        out, number = [], 0
        for b in self.api.children(parent):
            kind = b.get('type')
            number = number + 1 if kind == 'numbered_list_item' else 0
            out += self.block(b, kind, ctx, toggle, indent, number)
        return out

    def kids(self, b, ctx, toggle, indent):
        return self.blocks(b['id'], ctx, toggle, indent) if b.get('has_children') else []

    def block(self, b, kind, ctx, toggle, indent, number):
        data = b.get(kind) or {}
        pad = '  ' * indent
        text = richText(data.get('rich_text'))
        if kind == 'paragraph':
            return [pad + text if text.strip() else ''] + self.kids(b, ctx, toggle, indent + 1)
        if kind in ('heading_1', 'heading_2', 'heading_3'):
            line = ['', '#' * int(kind[-1]) + ' ' + text, '']
            return line + self.kids(b, ctx, toggle + 1, 0)
        if kind == 'toggle':
            return toggleHead(text, toggle, pad) + self.kids(b, ctx, toggle + 1, 0)
        if kind == 'bulleted_list_item':
            return [f'{pad}- {text}'] + self.kids(b, ctx, toggle, indent + 1)
        if kind == 'numbered_list_item':
            return [f'{pad}{number}. {text}'] + self.kids(b, ctx, toggle, indent + 1)
        if kind == 'to_do':
            return [f"{pad}- [{'x' if data.get('checked') else ' '}] {text}"] + self.kids(b, ctx, toggle, indent + 1)
        if kind == 'quote':
            return [f'{pad}> {text}'] + [pad + '> ' + l for l in self.kids(b, ctx, toggle, 0) if l.strip()]
        if kind == 'callout':
            icon = (data.get('icon') or {}).get('emoji', '')
            return [f'{pad}> {icon} {text}'.rstrip()] + [pad + '> ' + l for l in self.kids(b, ctx, toggle, 0) if l.strip()]
        if kind == 'code':
            return [f"{pad}```{data.get('language', '')}"] + [pad + l for l in richText(data.get('rich_text'), md=False).split('\n')] + [pad + '```']
        if kind == 'divider':
            return ['---']
        if kind == 'equation':
            return [f"{pad}$${data.get('expression', '')}$$"]
        if kind in ('image', 'pdf', 'file', 'video', 'audio'):
            return [pad + self.attachment(b, kind, data, ctx)]
        if kind in ('bookmark', 'embed', 'link_preview'):
            url = data.get('url', '')
            cap = richText(data.get('caption')) or url
            return [f'{pad}[{cap}]({url})'] if url else []
        if kind == 'child_page':
            ctx['kids'].append(['pagina', hexid(b['id'])])
            return [f"{pad}[{data.get('title') or 'Sem título'}] (subpágina)"]
        if kind == 'child_database':
            ctx['kids'].append(['db', hexid(b['id'])])
            return [f"{pad}[Banco: {data.get('title') or 'Sem título'}]"]
        if kind == 'link_to_page':
            target = data.get('page_id') or data.get('database_id')
            if target:
                ctx['kids'].append(['db' if data.get('type') == 'database_id' else 'pagina', hexid(target)])
            return []
        if kind == 'table':
            rows = [[richText(c) for c in (r.get('table_row') or {}).get('cells', [])]
                    for r in self.api.children(b['id'])]
            if not rows:
                return []
            lines = ['| ' + ' | '.join(rows[0]) + ' |', '|' + '---|' * len(rows[0])]
            return [''] + lines + ['| ' + ' | '.join(r) + ' |' for r in rows[1:]] + ['']
        if kind == 'synced_block':
            source = (data.get('synced_from') or {}).get('block_id')
            if source:
                try:
                    return self.blocks(source, ctx, toggle, indent)
                except NotionError:
                    return []
            return self.kids(b, ctx, toggle, indent)
        if kind in ('column_list', 'column'):
            return self.kids(b, ctx, toggle, indent)
        if kind in ('table_of_contents', 'breadcrumb', 'unsupported', 'template'):
            return []
        return ([pad + text] if text.strip() else []) + self.kids(b, ctx, toggle, indent + 1)

    def attachment(self, b, kind, data, ctx):
        caption = richText(data.get('caption'), md=False).strip()
        if data.get('type') == 'external':
            url = (data.get('external') or {}).get('url', '')
            return f'![{caption}]({url})' if kind == 'image' else f'[{caption or kind}: {url}]({url})'
        url = (data.get('file') or {}).get('url', '')
        name = data.get('name') or urllib.parse.unquote(os.path.basename(urllib.parse.urlparse(url).path)) or kind
        if kind == 'video':
            return f'[vídeo: {name}]'
        path = self.files.fetch(url, ctx['folder'], name, hexid(b['id']), b.get('last_edited_time'))
        if not path:
            return f'[{kind}: {name} (não baixado)]'
        ctx['attach'].append(rel(path))
        label = caption or os.path.basename(path)
        target = link(path, ctx['base'])
        return f'![{label}]({target})' if kind == 'image' else f'[{kind.upper()}: {label}]({target})'


# ----------------------------------------------------------------- conector MCP (Claude)

def readFetch(path):
    """resultado do notion-fetch: o JSON inteiro (como a ferramenta devolve/salva) ou só o texto."""
    raw = open(path, encoding='utf-8-sig', errors='replace').read()
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            data = next((d for d in data if isinstance(d, dict) and 'text' in d), {})
            if isinstance(data.get('text'), str) and data['text'].lstrip().startswith('{'):
                data = json.loads(data['text'])
        return data if isinstance(data, dict) else {'text': raw}
    except ValueError:
        return {'text': raw}


def fileName(src):
    """<pdf src="file://%7B...attachment:uuid:nome.pdf...%7D"> → (nome.pdf, uuid)
    <pdf src="notion-file-block://<bloco>/<uuid>?space_id=...&name=nome.pdf"> → (nome.pdf, uuid)"""
    if src.startswith('notion-file-block://'):
        url = urllib.parse.urlparse(src)
        name = (urllib.parse.parse_qs(url.query).get('name') or [''])[0]
        key = url.path.strip('/') or url.netloc
        return (name or key or None), key
    try:
        info = json.loads(urllib.parse.unquote(src[len('file://'):]))
        parts = info.get('source', '').split(':', 2)
        return (parts[-1] or None), (parts[1] if len(parts) == 3 else parts[-1])
    except ValueError:
        tail = urllib.parse.unquote(os.path.basename(urllib.parse.urlparse(src).path))
        return (tail or None), src


def flavored(content, ctx, files):
    """markdown do Notion (MCP: <details>, <columns>, tabs) → markdown simples, no mesmo estilo que a
    API produz: toggle vira título (### no 1º nível), lista mantém o recuo relativo."""
    out, stack, table = [], [], None
    for raw in content.split('\n'):
        tabs = len(raw) - len(raw.lstrip('\t'))
        s = raw.strip()
        base = stack[-1][1] + 1 if stack else 0
        pad = '  ' * max(0, tabs - base)
        quote = '> ' if any(k == 'callout' for k, _ in stack) else ''
        if s in ('<details>', '<columns>') or s.startswith(('<column', '<callout', '<details ')) \
                and not s.startswith('</'):
            kind = 'callout' if s.startswith('<callout') else s.strip('<>').split()[0]
            stack.append((kind, tabs))
            continue
        if s in ('</details>', '</columns>', '</column>', '</callout>'):
            if stack:
                stack.pop()
            continue
        m = re.match(r'^<summary>(.*)</summary>$', s)
        if m:
            out += toggleHead(clean(m.group(1)), sum(1 for k, _ in stack if k == 'details') - 1, '')
            continue
        if s.startswith('<table'):
            table = []
            continue
        if table is not None:
            if s.startswith('</table'):
                if table:
                    out += ['', '| ' + ' | '.join(table[0]) + ' |', '|' + '---|' * len(table[0])]
                    out += ['| ' + ' | '.join(r) + ' |' for r in table[1:]] + ['']
                table = None
            elif s.startswith('<tr'):
                table.append([])
            elif table:
                table[-1] += [clean(c) for c in re.findall(r'<td[^>]*>(.*?)</td>', s)]
            continue
        if s in ('<empty-block/>', '---'):
            out.append('' if s != '---' else '---')
            continue
        m = re.match(r'^<(pdf|file|video|audio|image)\s+src="([^"]*)"', s)
        if m:
            name, key = fileName(m.group(2)) if m.group(2) else (None, None)
            if m.group(2).startswith('http') and m.group(1) == 'image':
                s = f'![]({m.group(2)})'
            elif m.group(2).startswith('http'):          # arquivo externo (Drive etc.): só o link
                out.append(f'{pad}{quote}[{m.group(1)}: {m.group(2)}]({m.group(2)})')
                continue
            elif name:
                # o conector não baixa anexos: aponta para o arquivo local (export/API), com a mesma
                # regra de nomes repetidos ('main.pdf', 'main 1.pdf', ...)
                local = files.target(ctx['folder'], name, key)
                name = os.path.basename(local)
                if not os.path.exists(local):
                    ctx.setdefault('missing', []).append(rel(local))
                where = f'({link(local, ctx["base"])})' if os.path.exists(local) else ''
                if where:
                    ctx['attach'].append(rel(local))
                    files.state.seen.add(rel(local))
                out.append(f'{pad}{quote}[{m.group(1).upper()}: {name}]{where}')
                continue
            else:
                continue
        if re.match(r'^<unknown\b', s):
            continue
        m = re.match(r'^<page url="([^"]*)"[^>]*>(.*)</page>$', s)
        if m:
            out.append(f'{pad}[{clean(m.group(2)) or "Sem título"}] (subpágina)')
            continue
        m = re.match(r'^<database url="([^"]*)"[^>]*>(.*)</database>$', s)
        if m:
            out.append(f'{pad}[Banco: {clean(m.group(2)) or "sem título"}]')
            continue
        s = re.sub(r'!\[([^\]]*)\]\((https?://[^)]+)\)', lambda im: image(im, ctx, files), s)
        s = re.sub(r'!\[([^\]]*)\]\((notion-file-block://[^)]+)\)', lambda im: blockImage(im, ctx, files), s)
        for part in clean(s).split('\n'):
            if part.startswith('#'):
                out += ['', part, '']
            else:
                out.append(f'{pad}{quote}{part}' if part else '')
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(out)).strip()


def clean(s):
    s = re.sub(r'<br\s*/?>', '\n', s)
    s = re.sub(r'<mention-[a-z-]+ url="([^"]*)"[^>]*>(.*?)</mention-[a-z-]+>', r'\2', s)
    s = re.sub(r'<mention-[a-z-]+ url="([^"]*)"[^>]*/>', r'\1', s)
    s = re.sub(r'</?(span|u|color|mark|s|sub|sup)\b[^>]*>', '', s)
    s = re.sub(r'\s*\{(toggle|color)="[^"]*"\}', '', s)
    return re.sub(r'\\([$_~#<>|\-\[\]()!])', r'\1', s)     # escapes do markdown do Notion (\$, \>)


def image(m, ctx, files):
    url = m.group(2)
    name = urllib.parse.unquote(os.path.basename(urllib.parse.urlparse(url).path)) or 'imagem.png'
    if 'amazonaws.com' not in url and 'notion' not in url:
        return m.group(0)
    key = hashlib.sha1(urllib.parse.urlparse(url).path.encode()).hexdigest()[:16]
    path = files.fetch(url, ctx['folder'], name, key)
    if not path:
        return f'[imagem: {name}]'
    ctx['attach'].append(rel(path))
    return f'![{m.group(1) or os.path.basename(path)}]({link(path, ctx["base"])})'


def blockImage(m, ctx, files):
    """![](notion-file-block://...&name=x.png): o conector não baixa; aponta para a cópia local (export/API)."""
    name, key = fileName(m.group(2))
    local = files.target(ctx['folder'], name or 'imagem.png', key)
    if not os.path.exists(local):
        ctx.setdefault('missing', []).append(rel(local))
        return f'[imagem: {os.path.basename(local)}]'
    ctx['attach'].append(rel(local))
    files.state.seen.add(rel(local))
    return f'![{m.group(1) or os.path.basename(local)}]({link(local, ctx["base"])})'


def mcpProps(props, titleKey, people=None, titles=None):
    """propriedades do fetch/rows do MCP → {nome: texto} no formato do export. Pessoas vêm como
    user://id: o nome sai de notion.json → "pessoas" (o conector não lista convidados). Relações com
    linhas do mesmo banco viram o título da linha (`titles`); ponteiros de fórmula são descartados."""
    people, titles = people or {}, titles or {}

    def person(v):
        v = str(v)
        tag = re.match(r'^<mention-[a-z-]+ url="([^"]*)"', v)    # fetch da página: <mention-user url="user://…">
        if tag:
            v = tag.group(1)
        if v.startswith(('user://', 'bot://')):
            return people.get(v.split('://', 1)[1], '')
        if v.startswith('formulaResult://'):
            return ''
        if v.startswith('https://app.notion.com/p/') and hexid(v) in titles:
            return titles[hexid(v)]
        return v

    out, dates = {}, {}
    for key, value in (props or {}).items():
        if key in ('url', 'title', titleKey, 'createdTime') or key.endswith(':is_datetime'):
            continue
        m = re.match(r'^date:(.+):(start|end)$', key)
        if m:
            dates.setdefault(m.group(1), {})[m.group(2)] = value
            continue
        if isinstance(value, str) and value.startswith('[') and value.endswith(']'):
            try:
                value = json.loads(value)
            except ValueError:
                pass
        if isinstance(value, list):
            value = ', '.join(p for p in (person(v) for v in value) if p)
        elif isinstance(value, bool):
            value = 'Yes' if value else 'No'
        elif isinstance(value, str) and re.match(r'^\d{4}-\d{2}-\d{2}T', value):
            value = brt(value)
        value = '' if value is None else person(value).strip()
        out[key] = value
    for name, d in dates.items():
        out[name] = brt(d.get('start')) + (f" → {brt(d['end'])}" if d.get('end') else '')
    return out


def guessTitleKey(row, conf):
    if conf.get('titulo_prop') and conf['titulo_prop'] in row:
        return conf['titulo_prop']
    for k in TITLE_KEYS:
        if k in row:
            return k
    # sem nome conhecido: o 1º texto "simples" (não lista, pessoa, link, data ou fórmula)
    plain = [k for k, v in row.items() if isinstance(v, str) and k != 'url' and not k.startswith('date:')
             and not v.startswith(('[', 'user://', 'bot://', 'http', 'formulaResult://'))]
    return plain[0] if plain else None


def bankOf(state, cfg, source=None, nid=None):
    """(id, conf) do banco pela fonte (collection://…) ou id — configurados ou descobertos na varredura."""
    known = dict(state.data.get('bancos', {}))
    known.update(cfg.get('bancos', {}))
    for bid, conf in known.items():
        if (source and conf.get('fonte') == source) or (nid and bid == nid):
            return bid, conf
    return None, {}


def isTableOnly(cfg, title):
    return any(norm(title).startswith(norm(t)) for t in cfg.get('so_tabela', []) if t)


def parentFolder(state, cfg, pai):
    """pasta onde ficam os filhos de `pai` (a raiz põe os filhos direto em Notion/)."""
    if not pai or pai == hexid(cfg['raiz']['id']):
        return NOTION
    item = state.item(pai) or {}
    return os.path.join(DOCS, item['pasta']) if item.get('pasta') else NOTION


def enqueue(state, nid, **info):
    """põe na fila da varredura MCP (se ainda não foi feito nesta sincronização)."""
    nid = hexid(nid)
    if not nid or nid in state.data.setdefault('feitos', []):
        return
    fila = state.data.setdefault('fila', {})
    fila[nid] = dict(fila.get(nid, {}), **{k: v for k, v in info.items() if v is not None})


def done(state, nid):
    state.data.setdefault('fila', {}).pop(nid, None)
    if nid not in state.data.setdefault('feitos', []):
        state.data['feitos'].append(nid)


def bankFolders(state, cfg, bid, conf):
    """(pasta do CSV, pasta das linhas) de um banco. Bancos da configuração ficam no topo (como no
    export); os descobertos ficam dentro da página onde aparecem."""
    title = conf.get('titulo') or 'Sem título'
    base = NOTION if bid in cfg.get('bancos', {}) else parentFolder(state, cfg, conf.get('pai'))
    return base, state.folderFor(bid, base, title)


def mcpBank(args, cfg, state):
    ident = args.banco
    bid, conf = bankOf(state, cfg, source=ident if ident.startswith('collection://') else None, nid=hexid(ident))
    if not bid:
        say('banco desconhecido: ele precisa aparecer numa página já gravada (mcp-pagina) ou em tools/notion.json')
        return 2
    rows, more = [], False
    for path in args.arquivos:
        data = readFetch(path)
        part = data.get('results')
        if part is None and data.get('text'):
            part = json.loads(data['text']).get('results', [])
        rows += part or []
        more = bool(data.get('has_more'))
    title = conf.get('titulo') or 'Sem título'
    titleKey = guessTitleKey(rows[0], conf) if rows else conf.get('titulo_prop')
    titles = {hexid(r.get('url')): r.get(titleKey) for r in rows if titleKey and r.get(titleKey)}
    cols = [titleKey] if titleKey else []
    table = []
    for row in rows:
        props = mcpProps(row, titleKey, cfg.get('pessoas'), titles)
        for c in props:
            if c not in cols:
                cols.append(c)
        table.append((hexid(row.get('url')), row.get(titleKey, '') if titleKey else '', props))
    buf = StringIO()
    w = csv.writer(buf, lineterminator='\n')
    w.writerow(cols)
    for rid, rtitle, props in table:
        w.writerow([rtitle] + [props.get(c, '') for c in cols[1:]])
    base, folder = bankFolders(state, cfg, bid, conf)
    csvPath = os.path.join(base, f'{safeName(title)} {bid}_all.csv')
    how = writeText(csvPath, '﻿' + buf.getvalue())
    state.mark(csvPath, how)
    tableOnly = isTableOnly(cfg, title) and not conf.get('paginas')
    known = state.item(bid) or {}
    hashes = known.get('hashes') or {}
    want, now = [], {}
    for rid, rtitle, props in table:
        h = hashlib.sha1(json.dumps([rtitle, props], sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]
        now[rid] = h
        if tableOnly or not rid:
            continue
        item = state.item(rid) or {}
        adopted = False
        if args.adotar and rid not in hashes and not item.get('editado'):
            # 1ª sincronização por cima de um export: adota a página já exportada (mesmo nome/id)
            local = os.path.join(folder, f'{safeName(rtitle)} {rid}.md')
            if os.path.exists(local):
                item = state.put(rid, tipo='pagina', titulo=rtitle, arquivo=rel(local), anexos=[], pai=bid)
                adopted = True
        exists = item.get('arquivo') and os.path.exists(os.path.join(DOCS, item['arquivo']))
        if args.todas or not exists or (hashes.get(rid) != h and not adopted):
            want.append((rid, rtitle))
            enqueue(state, rid, tipo='pagina', titulo=rtitle, pai=bid)
        else:
            state.mark(os.path.join(DOCS, item['arquivo']), '')
            for a in item.get('anexos') or []:
                state.seen.add(a)
            state.put(rid, pai=bid)
            done(state, rid)
    gone = [] if more else [rid for rid in hashes if rid not in now]
    for rid in gone:
        state.data['itens'].pop(rid, None)       # o arquivo vira "antigo" e é arquivado no mcp-fim
    state.put(bid, tipo='banco', titulo=title, arquivo=rel(csvPath), linhas=len(rows), hashes=now,
              titulo_prop=titleKey, pai=conf.get('pai'), incompleto=more)
    done(state, bid)
    state.save('mcp')
    say(f'{title}{" (" + conf["grupo"] + ")" if conf.get("grupo") else ""}: {len(rows)} linhas, '
        f'CSV {how or "igual"}' + (', só tabela' if tableOnly else f', {len(want)} página(s) para buscar')
        + (f', {len(gone)} saíram do Notion' if gone else ''))
    if more:
        say('   ATENÇÃO: has_more=true — o banco tem mais de 100 linhas. Faça notion-fetch do banco, pegue a URL '
            'de uma view e consulte em mode "view" (page_size 100, start_cursor) passando TODOS os arquivos aqui.')
    return 0


def mcpSource(args, cfg, state):
    bid = hexid(args.banco)
    extra = state.data.setdefault('bancos', {}).setdefault(bid, {})
    extra['fonte'] = args.fonte
    for key, value in (('titulo', args.titulo), ('vista', args.vista), ('pai', hexid(args.pai) if args.pai else None)):
        if value:
            extra[key] = value
    enqueue(state, bid, tipo='banco', fonte=args.fonte, titulo=args.titulo)
    state.save('mcp')
    say(f'banco registrado: {bid} → {args.fonte}' + (f' ("{args.titulo}")' if args.titulo else '')
        + (f' view {args.vista}' if args.vista else ''))
    return 0


CHILD_PAGE = re.compile(r'<page url="([^"]+)"[^>]*>(.*?)</page>')
CHILD_DB = re.compile(r'<database url="([^"]+)"([^>]*)>(.*?)</database>')


def mcpPage(args, cfg, state):
    files = Files(state, cfg.get('max_anexo_mb', 60))
    rootId = hexid(cfg['raiz']['id'])
    for path in args.arquivos:
        data = readFetch(path)
        text = data.get('text', '')
        nid = hexid((re.search(r'<page url="([^"]+)"', text) or [None, data.get('url', '')])[1] or '')
        if not nid:
            say(f'{path}: não parece um resultado de fetch de página (sem <page url=...>)')
            continue
        m = re.search(r'<properties>\s*(\{.*?\})\s*</properties>', text, re.S)
        props = json.loads(m.group(1)) if m else {}
        content = re.search(r'<content>\n?(.*?)\n?</content>', text, re.S)
        content = content.group(1) if content else ''
        source = re.search(r'<parent-data-source url="([^"]+)"', text)
        bid, conf = bankOf(state, cfg, source=source.group(1)) if source else (None, {})
        queued = state.data.get('fila', {}).get(nid, {})
        bank = (state.item(bid) or {}) if bid else {}
        titleKey = bank.get('titulo_prop') or (guessTitleKey(props, conf) if bid else 'title')
        title = props.get(titleKey) or props.get('title') or queued.get('titulo') or data.get('title') or 'Sem título'
        if nid == rootId:
            folder, sub, pai = NOTION, NOTION, None
        elif bid:
            folder = bankFolders(state, cfg, bid, conf)[1]
            sub, pai = state.folderFor(nid, folder, title), bid
        else:
            pai = queued.get('pai') or (state.item(nid) or {}).get('pai')
            if pai:
                folder = parentFolder(state, cfg, pai)
            else:
                parts = [p.strip() for p in (data.get('path') or '').split(' / ') if p.strip()]
                folder = os.path.join(NOTION, *[safeName(p) for p in parts[1:]]) if len(parts) > 1 else NOTION
            sub = state.folderFor(nid, folder, title)
        out = os.path.join(folder, f'{safeName(title)} {nid}.md')
        ctx = {'id': nid, 'folder': sub, 'base': os.path.dirname(out), 'attach': [], 'missing': []}
        lines = [f'# {title}', '']
        if bid:
            lines += [f'{k}: {v}' for k, v in mcpProps(props, titleKey, cfg.get('pessoas')).items() if v] + ['']
        lines.append(flavored(content, ctx, files))
        md = scrub(re.sub(r'\n{3,}', '\n\n', '\n'.join(lines)).strip() + '\n', cfg.get('omitir_secoes', []))
        state.mark(out, writeText(out, md))
        state.put(nid, tipo='pagina', titulo=title, arquivo=rel(out), anexos=ctx['attach'], pai=pai,
                  editado=data.get('page_last_edited_at'))
        done(state, nid)
        # filhos: subpáginas e bancos citados no conteúdo entram na fila da varredura
        kids = 0
        scrubbed = scrub(content, cfg.get('omitir_secoes', []))
        for url, name in CHILD_PAGE.findall(scrubbed):
            cid = hexid(url)
            if cid and cid != nid and cid not in state.data.get('feitos', []):
                enqueue(state, cid, tipo='pagina', titulo=clean(name).strip() or None, pai=nid)
                kids += 1
        for url, attrs, name in CHILD_DB.findall(scrubbed):
            cid = hexid(url)
            fonte = re.search(r'data-source-url="([^"]+)"', attrs)
            if not cid or cid in state.data.get('feitos', []):
                continue
            if cid not in cfg.get('bancos', {}):
                extra = state.data.setdefault('bancos', {}).setdefault(cid, {})
                extra.update({'titulo': clean(name).strip() or extra.get('titulo') or 'Sem título', 'pai': nid})
                if fonte:
                    extra['fonte'] = fonte.group(1)
            enqueue(state, cid, tipo='banco', pai=nid, fonte=fonte.group(1) if fonte else None)
            kids += 1
        if ctx['missing']:
            miss = state.data.setdefault('sessao', {}).setdefault('faltando', [])
            miss += [m for m in ctx['missing'] if m not in miss]
        say(f'ok  {rel(out)}' + (f'  (+{len(ctx["attach"])} anexo(s))' if ctx['attach'] else '')
            + (f'  [{kids} filho(s) na fila]' if kids else ''))
    for fail in files.failed:
        say(f'   anexo não baixado: {fail}')
    state.save('mcp')
    return 0


def mcpStart(cfg, state):
    """começa uma varredura completa pelo conector: raiz + bancos configurados na fila."""
    state.data['fila'], state.data['feitos'] = {}, []
    state.data['sessao'] = {'novos': [], 'alterados': [], 'vistos': [], 'faltando': []}
    enqueue(state, cfg['raiz']['id'], tipo='pagina', titulo=cfg['raiz']['titulo'])
    for bid, conf in cfg.get('bancos', {}).items():
        enqueue(state, bid, tipo='banco', titulo=conf.get('titulo'), fonte=conf.get('fonte'))
    state.save('mcp')
    say('varredura iniciada.')
    return mcpNext(cfg, state)


def mcpNext(cfg, state):
    fila = state.data.get('fila', {})
    if not fila:
        say('fila vazia: tudo buscado → python notion_sync.py mcp-fim --arquivar')
        return 0
    pages = [(k, v) for k, v in fila.items() if v.get('tipo') != 'banco']
    banks = [(k, v) for k, v in fila.items() if v.get('tipo') == 'banco']
    say(f'fila: {len(pages)} página(s), {len(banks)} banco(s). Salve cada resultado (JSON inteiro) em scratch/.')
    for bid, info in banks:
        conf = bankOf(state, cfg, nid=bid)[1] or info
        fonte = conf.get('fonte') or info.get('fonte')
        name = conf.get('titulo') or info.get('titulo') or ''
        vista = conf.get('vista') or info.get('vista')
        if vista:
            say(f'  banco {bid} "{name}": notion-query-data-sources '
                f'{{"mode":"view","view_url":"{vista}","page_size":100}}  →  mcp-banco {bid} <arquivo...>')
        elif fonte:
            say(f'  banco {bid} "{name}": notion-fetch {bid} (título, fontes e views) → para CADA fonte:')
            say('      mcp-fonte <id> collection://… --titulo "<banco - fonte>" --vista view://… [--pai <página>]')
            say(f'      (a 1ª fonte usa o id {bid}; as outras usam o id da própria collection)')
        else:
            say(f'  banco {bid} "{name}": sem fonte — notion-fetch {bid}, pegue <data-source url="collection://…"> '
                f'→ mcp-fonte {bid} collection://…')
    for pid, info in pages:
        say(f'  página {pid} "{info.get("titulo") or ""}": notion-fetch {pid}  →  mcp-pagina <arquivo>')
    return 0


def plan(cfg, state):
    say('Sincronização pelo conector Notion do Claude (sem token) — varredura completa da árvore:')
    say('  1. notion_sync.py mcp-inicio            (fila = raiz + bancos da configuração)')
    say('  2. notion_sync.py mcp-proximos          (o que buscar agora; repita até a fila esvaziar)')
    say('     página → notion-fetch → mcp-pagina <arquivo...>   (subpáginas/bancos citados entram na fila)')
    say('     banco  → notion-query-data-sources mode "view" (sem cota; o "rows" tem cota por workspace)')
    say('              → mcp-banco <id> <arquivo...>; banco sem view registrada: notion-fetch → mcp-fonte')
    say('  3. notion_sync.py mcp-fim --arquivar    (estado, arquivamento do que saiu do Notion, mapa, kb.py)')
    say('Resultado grande a ferramenta já salva sozinha: passe o caminho dela. PDFs novos não vêm pelo conector.')
    return mcpNext(cfg, state) if state.data.get('fila') else 0


# ----------------------------------------------------------------- fechamento

def archive(paths):
    """move arquivos que saíram do Notion para Notion/.antigos/<data>/ (recuperável; o kb ignora)."""
    if not paths:
        return None
    dest = os.path.join(NOTION, '.antigos', datetime.now().strftime('%Y%m%d-%H%M%S'))
    for r in paths:
        src = os.path.join(DOCS, r)
        target = os.path.join(dest, os.path.relpath(src, NOTION))
        os.makedirs(os.path.dirname(target), exist_ok=True)
        os.replace(src, target)
    for root, dirs, names in sorted(os.walk(NOTION), key=lambda t: -len(t[0])):
        if root != NOTION and '.antigos' not in root and not os.listdir(root):
            os.rmdir(root)
    return rel(dest)


def finish(state, engine, cfg, clean=False, quiet=False, complete=True):
    """fecha a sincronização: o que saiu do Notion é arquivado (só com a rodada completa), o estado é
    salvo, o mapa e o kb.py são atualizados."""
    feitos = set(state.data.get('feitos') or [])
    sess = state.data.get('sessao', {}) if engine == 'mcp' else {}
    if engine == 'mcp':
        complete = complete and not state.data.get('fila')
        state.added = sess.get('novos', []) + state.added
        state.changed = sess.get('alterados', []) + state.changed
        state.seen |= set(sess.get('vistos', []))
        if complete and feitos:
            state.data['itens'] = {k: v for k, v in state.data['itens'].items() if k in feitos}
    elif complete:
        state.data['itens'] = {k: v for k, v in state.data['itens'].items()
                               if v.get('arquivo') in state.seen or v.get('tipo') == 'banco'}
    known = tracked(state) | state.seen
    legacy = []
    for root, dirs, names in os.walk(NOTION):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for n in names:
            r = rel(os.path.join(root, n))
            if not n.startswith('.') and r not in known:
                legacy.append(r)
    archived = None
    if clean and complete:
        archived = archive(sorted(legacy))
        state.data['anexos'] = {k: v for k, v in state.data.get('anexos', {}).items()
                                if v.get('arquivo') not in legacy}
    added, changed = list(state.added), list(state.changed)
    missing = sess.get('faltando', [])
    state.added, state.changed = [], []
    state.data.pop('sessao', None)
    state.save(engine, final=True)
    writeMap(state, cfg)
    kbChanges = runKb()
    report = {'motor': engine, 'completa': complete, 'novos': added, 'alterados': changed,
              'arquivados': len(legacy) if archived else 0, 'pasta_arquivo': archived,
              'fora_do_notion': 0 if archived else len(legacy), 'pdf_sem_copia': missing, 'kb': kbChanges}
    if quiet:
        return report
    say(f'\nNotion → docs/Notion ({engine}{"" if complete else ", INCOMPLETA"}): {len(added)} novo(s), '
        f'{len(changed)} alterado(s)' + (f', {len(legacy)} arquivado(s) em {archived}' if archived else ''))
    for tag, items in (('+', added), ('~', changed)):
        for r in items[:40]:
            say(f'  {tag} {r}')
        if len(items) > 40:
            say(f'  {tag} ... e mais {len(items) - 40}')
    if not complete:
        say(f"  a fila ainda tem {len(state.data.get('fila') or {})} item(ns) — nada foi arquivado (mcp-proximos)")
    elif legacy and not archived:
        say(f'  {len(legacy)} arquivo(s) em docs/Notion não vieram do Notion (use --arquivar)')
    for name in missing:
        say(f'  PDF citado no Notion sem cópia local (o conector não baixa; use a API): {name}')
    if kbChanges:
        say(f"\nkb.py: {kbChanges.get('pendentes', 0)} documento(s) para revisar (kb.py novidades)"
            + (f" | {', '.join(kbChanges.get('mudancas', [])[:6])}" if kbChanges.get('mudancas') else ''))
    return report


def writeMap(state, cfg):
    """docs/notion_mapa.md: a árvore do Notion como foi sincronizada, com o arquivo local de cada item."""
    items = state.data.get('itens', {})
    kids = {}
    for nid, item in items.items():
        kids.setdefault(item.get('pai'), []).append(nid)
    rootId = hexid(cfg['raiz']['id'])
    lines = ['# Mapa do Notion (gerado)', '',
             f"> Gerado por `tools/notion_sync.py` em {datetime.now():%d/%m/%Y %H:%M}. Árvore da página "
             f"**{cfg['raiz']['titulo']}** como foi sincronizada, com o arquivo local de cada item "
             '(caminhos relativos a `docs/`). Não edite: "sincronizar os documentos" refaz.', '']

    def walk(nid, depth, seen):
        if nid in seen:
            return
        seen.add(nid)
        item = items.get(nid, {})
        kind = 'banco' if item.get('tipo') == 'banco' else 'página'
        extra = f", {item.get('linhas')} linhas" if kind == 'banco' else ''
        lines.append(f"{'  ' * depth}- **{item.get('titulo') or 'Sem título'}** ({kind}{extra}) → "
                     f"`{item.get('arquivo', '?')}`")
        for a in (item.get('anexos') or [])[:40]:
            if a.lower().endswith('.pdf'):
                lines.append(f"{'  ' * (depth + 1)}- PDF `{a}`")
        children = sorted(kids.get(nid, []), key=lambda k: (items[k].get('tipo') != 'banco',
                                                            norm(items[k].get('titulo', ''))))
        for i, cid in enumerate(children):
            if items[cid].get('pai') == nid and item.get('tipo') == 'banco' and i >= 60:
                lines.append(f"{'  ' * (depth + 1)}- … e mais {len(children) - 60} linha(s)")
                break
            walk(cid, depth + 1, seen)

    seen = set()
    if rootId in items:
        walk(rootId, 0, seen)
    for nid, item in items.items():                 # bancos da configuração e órfãos
        if nid not in seen and (item.get('pai') in (None, rootId)) and nid != rootId:
            walk(nid, 1, seen)
    writeText(os.path.join(DOCS, 'notion_mapa.md'), '\n'.join(lines) + '\n')


def tracked(state):
    out = {i.get('arquivo') for i in state.data['itens'].values() if i.get('arquivo')}
    for i in state.data['itens'].values():
        out |= set(i.get('anexos') or [])
    out |= {a.get('arquivo') for a in state.data.get('anexos', {}).values()}
    # arquivos locais citados pelas páginas rastreadas (ex.: imagens de páginas adotadas de um export)
    for page in [r for r in out if r and r.endswith('.md')]:
        path = os.path.join(DOCS, page)
        try:
            text = open(path, encoding='utf-8', errors='replace').read()
        except OSError:
            continue
        for target in re.findall(r'\]\(([^)\s]+)\)', text):
            if '://' in target or target.startswith('#'):
                continue
            local = os.path.normpath(os.path.join(os.path.dirname(path), urllib.parse.unquote(target)))
            if os.path.isfile(local):
                out.add(rel(local))
    return out


def runKb():
    try:
        import contextlib
        sys.path.insert(0, TOOLS)
        import kb
        with contextlib.redirect_stdout(StringIO()) as log:
            manifest = kb.update(quiet=True)
        changes = [l.strip() for l in log.getvalue().splitlines() if l.strip().startswith('[')]
        return {'pendentes': len(kb.pending(manifest)), 'mudancas': changes[:12]}
    except Exception as err:
        return {'erro': str(err)}


# ----------------------------------------------------------------- comandos

def cmdStatus(cfg, check):
    state = loadJson(STATE, {})
    token, where = findToken()
    say(f"raiz: {cfg['raiz']['titulo']} ({cfg['raiz']['id']})")
    if token:
        line = f'API: token em {where}'
        if check:
            try:
                me = Rest(token).call('GET', '/users/me')
                line += f" — válido ({me.get('name') or me.get('bot', {}).get('workspace_name') or 'ok'})"
                Rest(token).call('GET', f"/pages/{uuid(cfg['raiz']['id'])}")
                line += ', raiz acessível'
            except NotionError as err:
                line += f' — {err}'
        say(line)
    else:
        say('API: sem token (NOTION_TOKEN ou docs/.notion_token). Claude com conector Notion: use `plano`.')
    when = state.get('atualizado')
    if when:
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(when)).total_seconds() / 86400
        say(f"última sincronização: {brt(when)} ({age:.1f} dia(s)) via {state.get('motor')}; "
            f"{len(state.get('itens', {}))} itens rastreados")
    else:
        say('última sincronização: nunca (docs/Notion veio de export manual ou está vazio)')
    for bid, conf in cfg.get('bancos', {}).items():
        pend = (state.get('itens', {}).get(bid) or {}).get('pendentes') or []
        if pend:
            say(f"  {conf.get('titulo')} ({conf.get('grupo', '')}): {len(pend)} página(s) listadas e não buscadas")
    return 0


def cmdToken(value):
    value = (value or '').strip()
    if not re.match(r'^(ntn_|secret_)\w{20,}$', value):
        say('token inválido: o token de integração interna do Notion começa com ntn_ (ou secret_)')
        return 2
    try:
        me = Rest(value).call('GET', '/users/me')
    except NotionError as err:
        say(f'o Notion recusou: {err}')
        return 1
    with open(TOKEN_FILE, 'w', encoding='utf-8') as f:
        f.write(value + '\n')
    say(f"token salvo em {rel(TOKEN_FILE)} (fora do git) — integração: {me.get('name') or 'ok'}")
    say('Lembre de conectar a integração à página raiz no Notion: ••• → Conexões → adicionar.')
    return 0


def cmdSync(cfg, args):
    token, where = findToken()
    if not token:
        say('Sem token da API do Notion. Opções:\n'
            '  • criar a integração (uma vez) e rodar: python notion_sync.py token ntn_...\n'
            '  • no Claude com o conector Notion: python notion_sync.py plano')
        return 3
    state = State()
    sync = RestSync(Rest(token), state, cfg, full=args.tudo)
    started = time.time()
    try:
        sync.page(cfg['raiz']['id'], NOTION, root=True)
        for bid in cfg.get('bancos', {}):
            sync.child('db', bid, NOTION, False)
    except NotionError as err:
        say(f'falhou: {err}')
        if sync.api.calls <= 2:
            return 1
        say('(sincronização parcial: nada foi removido; rode de novo)')
        state.save('api')
        return 1
    for fail in sync.files.failed:
        say(f'   anexo não baixado: {fail}')
    if sync.errors:
        say(f'({sync.errors} item(ns) com erro: nada foi removido nesta rodada)')
    report = finish(state, 'api', cfg, clean=args.limpar, quiet=args.json, complete=not sync.errors)
    report.update({'paginas_baixadas': sync.fetched, 'chamadas_api': sync.api.calls,
                   'segundos': round(time.time() - started, 1)})
    if args.json:
        print(json.dumps(report, ensure_ascii=False))
    else:
        say(f'({sync.fetched} página(s) baixadas, {sync.api.calls} chamadas, {time.time() - started:.0f}s)')
    return 0


def main():
    p = argparse.ArgumentParser(prog='notion_sync', description='Notion → docs/Notion (base das IAs Sighir)')
    sub = p.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('status', help='token, última sincronização')
    s.add_argument('--testar', action='store_true', help='confere o token na API')
    t = sub.add_parser('token', help='guarda o token da integração (docs/.notion_token)')
    t.add_argument('valor')
    y = sub.add_parser('sincronizar', help='sincroniza pela API (incremental)')
    y.add_argument('--tudo', action='store_true', help='baixa tudo de novo, mesmo o que não mudou')
    y.add_argument('--arquivar', '--limpar', dest='limpar', action='store_true',
                   help='move para Notion/.antigos/ o que não veio do Notion (só com a rodada completa)')
    y.add_argument('--json', action='store_true')
    sub.add_parser('plano', help='roteiro para sincronizar pelo conector MCP do Claude')
    sub.add_parser('mcp-inicio', help='começa a varredura completa pelo conector (fila = raiz + bancos)')
    sub.add_parser('mcp-proximos', help='o que ainda falta buscar na varredura')
    fo = sub.add_parser('mcp-fonte', help='registra a fonte (collection://…) de um banco descoberto')
    fo.add_argument('banco')
    fo.add_argument('fonte')
    fo.add_argument('--titulo', help='nome do banco (sem o emoji), quando a raiz não mostra')
    fo.add_argument('--vista', help='view://… para consultar em mode "view" (sem a cota do mode "rows")')
    fo.add_argument('--pai', help='página onde o banco aparece (fonte extra de um banco com várias fontes)')
    b = sub.add_parser('mcp-banco', help='linhas de um banco (resultado do query rows/view) → CSV')
    b.add_argument('banco', help='id do banco ou collection://…')
    b.add_argument('arquivos', nargs='+', help='um ou mais resultados (páginas da consulta)')
    b.add_argument('--todas', action='store_true', help='lista todas as páginas para buscar')
    b.add_argument('--adotar', action='store_true',
                   help='1ª vez sobre um export: páginas já exportadas contam como atualizadas')
    g = sub.add_parser('mcp-pagina', help='página (resultado do fetch) → .md')
    g.add_argument('arquivos', nargs='+')
    f = sub.add_parser('mcp-fim', help='fecha a sincronização MCP (estado + mapa + kb.py)')
    f.add_argument('--arquivar', action='store_true',
                   help='varredura completa: move para Notion/.antigos/ o que não veio do Notion')
    f.add_argument('--json', action='store_true')

    args = p.parse_args()
    cfg = loadJson(CONFIG, None)
    if not cfg:
        say(f'configuração ausente ou inválida: {rel(CONFIG)}')
        return 2
    if args.cmd == 'status':
        return cmdStatus(cfg, args.testar)
    if args.cmd == 'token':
        return cmdToken(args.valor)
    if args.cmd == 'sincronizar':
        return cmdSync(cfg, args)
    state = State()
    if args.cmd == 'plano':
        return plan(cfg, state)
    if args.cmd == 'mcp-inicio':
        return mcpStart(cfg, state)
    if args.cmd == 'mcp-proximos':
        return mcpNext(cfg, state)
    if args.cmd == 'mcp-fonte':
        return mcpSource(args, cfg, state)
    if args.cmd == 'mcp-banco':
        return mcpBank(args, cfg, state)
    if args.cmd == 'mcp-pagina':
        return mcpPage(args, cfg, state)
    if args.cmd == 'mcp-fim':
        report = finish(state, 'mcp', cfg, clean=args.arquivar, quiet=args.json)
        if args.json:
            print(json.dumps(report, ensure_ascii=False))
        return 0
    return 1


if __name__ == '__main__':
    sys.exit(main())
