"""
Testes do notion_sync.py — sem rede, numa pasta temporária (não toca em docs/Notion).

    python docs/tools/test_notion_sync.py

Cobrem os dois caminhos (API com token e conector MCP do Claude): conversão para markdown no mesmo
estilo, remoção de seções com senha, nomes de arquivo iguais aos do export, sincronização incremental
e a trava que impede apagar arquivos quando alguma página falhou.
"""

import os
import sys
import json
import shutil
import tempfile
import contextlib
from io import StringIO

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
import notion_sync as ns  # noqa: E402

CFG = {'raiz': {'id': 'a' * 32, 'titulo': 'Raiz'}, 'omitir_secoes': ['Credenciais'],
       'so_tabela': ['Estoque'], 'bancos': {}, 'max_anexo_mb': 1,
       'pessoas': {'11111111-2222-3333-4444-555555555555': 'Fulano'}}


@contextlib.contextmanager
def sandbox():
    """DOCS/NOTION/STATE do módulo apontando para uma pasta temporária."""
    tmp = tempfile.mkdtemp(prefix='notion_sync_test_')
    saved = (ns.DOCS, ns.NOTION, ns.STATE, ns.runKb)
    ns.runKb = lambda: {}                         # não reindexa a base real durante o teste
    ns.DOCS, ns.NOTION = tmp, os.path.join(tmp, 'Notion')
    ns.STATE = os.path.join(ns.NOTION, '.sync.json')
    os.makedirs(ns.NOTION)
    try:
        with contextlib.redirect_stdout(StringIO()):
            yield tmp
    finally:
        ns.DOCS, ns.NOTION, ns.STATE, ns.runKb = saved
        shutil.rmtree(tmp, ignore_errors=True)


def testHelpers():
    assert ns.hexid('https://app.notion.com/p/25079b90eb7380048323ce9f5903d098?pvs=204') == \
        '25079b90eb7380048323ce9f5903d098'
    assert ns.hexid('25079b90-eb73-804e-87fd-000b08bf7c52') == '25079b90eb73804e87fd000b08bf7c52'
    # 50 caracteres, como o export (é isso que mantém os nomes estáveis entre export e sincronização)
    assert ns.safeName('Etilômetro Reiniciando (Reiniciamentos Inesperados)') == \
        'Etilômetro Reiniciando (Reiniciamentos Inesperados'
    assert ns.safeName('a/b:c?') == 'abc' and ns.safeName('') == 'Sem título'
    assert ns.brt('2025-08-28T21:03:00.000Z') == '28/08/2025 18:03 (BRT)'
    assert ns.brt('2026-09-02') == '02/09/2026'


def testScrub():
    md = '\n'.join(['# Página', '## 💳 Credenciais', '- **Usuário**: x', '- **Senha**: segredo',
                    '### Sub', 'ainda omitido', '## 📄 Documentos', 'fica', 'Senha: 1234',
                    'CF:passwd$Sighir2024!'])
    out = ns.scrub(md, ['Credenciais'])
    assert 'segredo' not in out and 'ainda omitido' not in out and 'Credenciais' not in out
    assert 'fica' in out and 'Senha: [omitido]' in out and 'CF:passwd$Sighir2024!' in out


def testFlavored():
    content = '\n'.join([
        '## 🚚 Suporte', '---', '<details>', '<summary>Troubleshooting</summary>',
        '\t<details>', '\t<summary>Problemas de Sopro</summary>',
        '\t\t1. Verificar versão', '\t\t2. Ajustar (CF:blowProb\\$0.5!)<br>→ detalhe',
        '\t\t\t- subitem', '\t\t<details>', '\t\t<summary>Abrir</summary>', '\t\t\tfio azul', '\t\t</details>',
        '\t</details>', '</details>', '<columns>', '\t<column ratio="50">', '\t\t<callout color="gray_bg">',
        '\t\t\t`STT;1;2`', '\t\t</callout>', '\t</column>', '</columns>',
        '<pdf src="file://%7B%22source%22%3A%22attachment%3Aabc%3Amain.pdf%22%7D"></pdf>',
        '<unknown url="https://app.notion.com/p/x#y" alt="bookmark"/>',
        'Tabela -\\> installed'])
    with sandbox() as tmp:
        files = ns.Files(ns.State(), 1)
        ctx = {'id': 'p', 'folder': ns.NOTION, 'base': ns.NOTION, 'attach': []}
        open(os.path.join(ns.NOTION, 'main.pdf'), 'w').close()
        md = ns.flavored(content, ctx, files)
    assert '### Troubleshooting' in md and '#### Problemas de Sopro' in md
    assert '1. Verificar versão' in md and 'CF:blowProb$0.5!' in md and '→ detalhe' in md
    assert '  - subitem' in md                      # recuo relativo da lista preservado
    assert 'Abrir' not in md and 'fio azul' in md    # toggle genérico não vira título
    assert '> `STT;1;2`' in md                       # callout vira citação
    assert '[PDF: main.pdf](main.pdf)' in md and 'bookmark' not in md
    assert 'Tabela -> installed' in md


def testFlavoredFileBlock():
    """formato novo do conector (out/2026): anexos como notion-file-block://<bloco>/<uuid>?...&name=x"""
    fb = 'notion-file-block://27e79b90-eb73-80c7/{u}?space_id=e2b4&name={n}'
    content = '\n'.join([f'<pdf src="{fb.format(u="u1", n="main.pdf")}"></pdf>',
                         f'<pdf src="{fb.format(u="u2", n="main.pdf")}"></pdf>',
                         f'![]({fb.format(u="u3", n="foto.png")})',
                         f'![]({fb.format(u="u4", n="sumiu.png")})'])
    with sandbox() as tmp:
        files = ns.Files(ns.State(), 1)
        ctx = {'id': 'p', 'folder': ns.NOTION, 'base': ns.NOTION, 'attach': []}
        for name in ('main.pdf', 'main 1.pdf', 'foto.png'):
            open(os.path.join(ns.NOTION, name), 'w').close()
        md = ns.flavored(content, ctx, files)
    assert ns.fileName(fb.format(u='u1', n='main.pdf')) == ('main.pdf', 'u1')
    assert '[PDF: main.pdf](main.pdf)' in md and '[PDF: main 1.pdf](main%201.pdf)' in md, md
    assert '![foto.png](foto.png)' in md and '[imagem: sumiu.png]' in md and 'notion-file-block' not in md, md


def testMcpProps():
    props = {'Problema': 'X', 'Status': 'Concluído', 'date:Data:start': '2025-08-28T21:03:00.000Z',
             'date:Data:is_datetime': 1, 'Empresa': '["Predileto"]',
             'Responsável': '["user://11111111-2222-3333-4444-555555555555", "user://desconhecido"]',
             'url': 'https://app.notion.com/p/' + 'b' * 32}
    out = ns.mcpProps(props, 'Problema', CFG['pessoas'])
    assert out == {'Status': 'Concluído', 'Empresa': 'Predileto', 'Responsável': 'Fulano',
                   'Data': '28/08/2025 18:03 (BRT)'}, out
    # fetch de página: pessoas vêm como tag <mention-user>
    tag = '<mention-user url="user://11111111-2222-3333-4444-555555555555"></mention-user>'
    assert ns.mcpProps({'Responsável': [tag]}, 'Problema', CFG['pessoas']) == {'Responsável': 'Fulano'}


class FakeApi:
    """API do Notion em memória: páginas, blocos e um banco."""

    def __init__(self):
        self.calls = 0
        self.edited = '2026-09-01T00:00:00.000Z'
        self.fail = set()
        root, db, row = 'a' * 32, 'd' * 32, 'e' * 32
        self.pages = {
            root: {'id': ns.uuid(root), 'last_edited_time': self.edited, 'parent': {'type': 'workspace'},
                   'properties': {'title': {'type': 'title', 'title': [{'plain_text': 'Raiz'}]}}},
        }
        self.row = {'id': ns.uuid(row), 'last_edited_time': self.edited, 'parent': {'type': 'database_id'},
                    'properties': {
                        'Problema': {'type': 'title', 'title': [{'plain_text': 'Etilômetro não pede teste'}]},
                        'Status': {'type': 'status', 'status': {'name': 'Concluído'}},
                        'Data': {'type': 'date', 'date': {'start': '2026-04-15T13:58:00.000-03:00'}},
                        'Responsável': {'type': 'people', 'people': [{'name': 'Fulano'}]}}}
        t = lambda s, **a: [{'type': 'text', 'plain_text': s, 'annotations': a}]  # noqa: E731
        self.blocks = {
            root: [
                {'id': '1', 'type': 'heading_2', 'heading_2': {'rich_text': t('💳 Credenciais')}},
                {'id': '2', 'type': 'paragraph', 'paragraph': {'rich_text': t('Senha: segredo')}},
                {'id': '3', 'type': 'heading_2', 'heading_2': {'rich_text': t('🚚 Suporte')}},
                {'id': '4', 'type': 'toggle', 'has_children': True, 'toggle': {'rich_text': t('Troubleshooting')}},
                {'id': '9', 'type': 'child_database', 'child_database': {'title': 'Resolução de Problemas'}},
            ],
            '4': [{'id': '5', 'type': 'numbered_list_item', 'numbered_list_item': {'rich_text': t('Primeiro')}},
                  {'id': '6', 'type': 'numbered_list_item', 'has_children': True,
                   'numbered_list_item': {'rich_text': t('Segundo', bold=True)}},
                  {'id': '8', 'type': 'code', 'code': {'language': 'text', 'rich_text': t('$ETEV01!')}}],
            '6': [{'id': '7', 'type': 'bulleted_list_item', 'bulleted_list_item': {'rich_text': t('detalhe')}}],
            row: [{'id': 'r1', 'type': 'heading_2', 'heading_2': {'rich_text': t('Solução')}},
                  {'id': 'r2', 'type': 'paragraph', 'paragraph': {'rich_text': t('Trocar o conjunto')}}],
        }
        self.dbid = '9'

    def call(self, method, path, body=None):
        self.calls += 1
        if path.startswith('/pages/'):
            return self.pages[ns.hexid(path)]
        if path.startswith('/databases/') and path.endswith('/query'):
            return {'results': [self.row]}
        if path.startswith('/databases/'):
            return {'title': [{'plain_text': 'Resolução de Problemas'}], 'properties': {
                'Problema': {'type': 'title'}, 'Status': {'type': 'status'}, 'Data': {'type': 'date'},
                'Responsável': {'type': 'people'}}}
        raise AssertionError(path)

    def paged(self, method, path, body=None):
        if method == 'POST':
            return self.call('POST', path, body)['results']
        return self.children(path.split('/')[2])

    def children(self, block_id):
        self.calls += 1
        key = ns.hexid(block_id) or block_id
        if key in self.fail:
            raise ns.NotionError('falha simulada')
        return self.blocks.get(key, [])


def run(api, full=False):
    state = ns.State()
    sync = ns.RestSync(api, state, CFG, full=full)
    sync.page(CFG['raiz']['id'], ns.NOTION, root=True)
    return state, sync


def testRestSync():
    with sandbox():
        api = FakeApi()
        # child_database '9' → o id do bloco é o id do banco; o fake usa '9' como id curto
        api.blocks['a' * 32][-1]['id'] = 'd' * 32
        state, sync = run(api)
        root = os.path.join(ns.NOTION, f"Raiz {'a' * 32}.md")
        md = open(root, encoding='utf-8').read()
        assert 'segredo' not in md and 'Credenciais' not in md
        assert '### Troubleshooting' in md and '1. Primeiro' in md and '2. **Segundo**' in md
        assert '  - detalhe' in md and '$ETEV01!' in md
        csvs = [f for f in os.listdir(ns.NOTION) if f.endswith('_all.csv')]
        assert csvs == [f"Resolução de Problemas {'d' * 32}_all.csv"], csvs
        rowmd = open(os.path.join(ns.NOTION, 'Resolução de Problemas', f"Etilômetro não pede teste {'e' * 32}.md"),
                     encoding='utf-8').read()
        assert 'Status: Concluído' in rowmd and 'Data: 15/04/2026 13:58 (BRT)' in rowmd
        assert 'Responsável: Fulano' in rowmd and '## Solução' in rowmd
        state.save('api')

        # 2ª rodada sem mudança no Notion: nenhuma página baixada de novo
        api.calls = 0
        state2, sync2 = run(api)
        assert sync2.fetched == 0 and not state2.added and not state2.changed, (sync2.fetched, state2.changed)
        state2.save('api')

        # a linha foi editada: só ela é baixada
        api.row = dict(api.row, last_edited_time='2026-09-10T00:00:00.000Z')
        api.blocks['e' * 32][1]['paragraph']['rich_text'][0]['plain_text'] = 'Trocar o relé'
        state3, sync3 = run(api)
        assert sync3.fetched == 1 and len(state3.changed) == 1, (sync3.fetched, state3.changed)


def testNoDeleteOnError():
    with sandbox():
        api = FakeApi()
        api.blocks['a' * 32][-1]['id'] = 'd' * 32
        state, _ = run(api)
        state.save('api')
        rowfile = os.path.join(ns.NOTION, 'Resolução de Problemas', f"Etilômetro não pede teste {'e' * 32}.md")
        assert os.path.exists(rowfile)
        # a linha dá erro na próxima rodada: o arquivo dela não pode sumir
        api.row = dict(api.row, last_edited_time='2026-09-11T00:00:00.000Z')
        api.fail.add('e' * 32)
        state2, sync2 = run(api)
        assert sync2.errors == 1
        ns.finish(state2, 'api', CFG, quiet=True, complete=not sync2.errors)
        assert os.path.exists(rowfile)


def testMcpBankAndPage():
    with sandbox() as tmp:
        cfg = dict(CFG, bancos={'d' * 32: {'titulo': 'Resolução de Problemas', 'fonte': 'collection://fonte',
                                           'paginas': True, 'titulo_prop': 'Problema'}})
        rows = {'results': [{'Problema': 'Tela apagada', 'Status': 'Concluído',
                             'url': 'https://app.notion.com/p/' + 'e' * 32}]}
        rowsFile = os.path.join(tmp, 'rows.json')
        json.dump(rows, open(rowsFile, 'w', encoding='utf-8'))
        args = type('A', (), {'banco': 'd' * 32, 'arquivos': [rowsFile], 'todas': False, 'adotar': False})
        assert ns.mcpBank(args, cfg, ns.State()) == 0
        assert list(ns.State().data['fila']) == ['e' * 32]
        page = {'title': 'Tela apagada', 'page_last_edited_at': '2026-08-25T11:56:05Z',
                'text': '<page url="https://app.notion.com/p/' + 'e' * 32 + '">\n<ancestor-path>\n'
                        '<parent-data-source url="collection://fonte" name="Resolução de Problemas"/>\n'
                        '</ancestor-path>\n<properties>\n{"Problema":"Tela apagada","Status":"Concluído"}\n'
                        '</properties>\n<content>\n## Solução\nReconectar o fusível\n</content>\n</page>'}
        pageFile = os.path.join(tmp, 'page.json')
        json.dump(page, open(pageFile, 'w', encoding='utf-8'))
        ns.mcpPage(type('A', (), {'arquivos': [pageFile]}), cfg, ns.State())
        out = os.path.join(ns.NOTION, 'Resolução de Problemas', f"Tela apagada {'e' * 32}.md")
        text = open(out, encoding='utf-8').read()
        assert text.startswith('# Tela apagada\n\nStatus: Concluído') and 'Reconectar o fusível' in text
        assert not ns.State().data['fila']
        # 2ª consulta igual: nada para buscar
        assert ns.mcpBank(args, cfg, ns.State()) == 0 and not ns.State().data['fila']


def testMcpCrawl():
    """varredura: a raiz cita uma subpágina e um banco novos → entram na fila; ao fim, o que não veio
    do Notion vai para Notion/.antigos/ e o mapa é gerado."""
    root, sub, db = 'a' * 32, 'b' * 32, 'c' * 32
    with sandbox() as tmp:
        cfg = dict(CFG, bancos={})
        state = ns.State()
        ns.mcpStart(cfg, state)
        assert list(ns.State().data['fila']) == [root]
        old = os.path.join(ns.NOTION, 'Velho export 1234.md')
        open(old, 'w').write('x')

        def page(pid, content, path='Raiz'):
            f = os.path.join(tmp, f'{pid}.json')
            json.dump({'path': path, 'page_last_edited_at': '2026-09-01T00:00:00Z', 'text':
                       f'<page url="https://app.notion.com/p/{pid}">\n<properties>\n{{"title":"T{pid[0]}"}}\n'
                       f'</properties>\n<content>\n{content}\n</content>\n</page>'}, open(f, 'w', encoding='utf-8'))
            return f
        rootContent = ('## 💳 Credenciais\n<page url="https://app.notion.com/p/' + 'f' * 32 + '">Senhas</page>\n'
                       '## 📄 Docs\n<page url="https://app.notion.com/p/' + sub + '">Estoque X</page>\n'
                       '<database url="https://app.notion.com/p/' + db + '" data-source-url="collection://z">'
                       'Fornecedores</database>')
        ns.mcpPage(type('A', (), {'arquivos': [page(root, rootContent)]}), cfg, ns.State())
        fila = ns.State().data['fila']
        assert set(fila) == {sub, db}, fila            # a página dentro de "Credenciais" não entra
        ns.mcpPage(type('A', (), {'arquivos': [page(sub, 'conteúdo')]}), cfg, ns.State())
        assert os.path.exists(os.path.join(ns.NOTION, f'Tb {sub}.md'))
        rows = os.path.join(tmp, 'rows.json')
        json.dump({'results': [{'Nome': 'Fornecedor 1', 'url': 'https://app.notion.com/p/' + 'e' * 32}]},
                  open(rows, 'w', encoding='utf-8'))
        ns.mcpBank(type('A', (), {'banco': db, 'arquivos': [rows], 'todas': False, 'adotar': False}),
                   dict(cfg, so_tabela=['Fornecedores']), ns.State())
        assert not ns.State().data['fila']              # só tabela: nenhuma linha vira página
        report = ns.finish(ns.State(), 'mcp', cfg, clean=True, quiet=True)
        assert report['completa'] and report['arquivados'] == 1 and not os.path.exists(old)
        assert os.path.exists(os.path.join(tmp, report['pasta_arquivo'], 'Velho export 1234.md'))
        mapa = open(os.path.join(tmp, 'notion_mapa.md'), encoding='utf-8').read()
        assert 'Fornecedores' in mapa and 'Tb' in mapa, mapa


if __name__ == '__main__':
    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith('test') and callable(fn):
            try:
                fn()
                print(f'ok  {name}')
            except Exception as err:
                failed += 1
                import traceback
                traceback.print_exc()
                print(f'FALHOU  {name}: {err}')
    print('\ntodos passaram' if not failed else f'\n{failed} teste(s) falharam')
    sys.exit(1 if failed else 0)
