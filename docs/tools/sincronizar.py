#!/usr/bin/env python3
"""
sincronizar.py — "sincronizar os documentos": atualiza toda a base docs/ de uma vez.

    python docs/tools/sincronizar.py            servidor + Notion + índice
    python docs/tools/sincronizar.py --sem-snapshot   não baixa o banco de produção (148 MB)

1. Servidor de produção (servidor.py): docs/servidor_resumo.md e, havendo a chave, o snapshot do banco;
   contrato.py diferenca avisa se a API ou o banco mudaram (docs/migracao_servidor.md).
2. Notion (notion_sync.py), a árvore inteira da página raiz, com arquivamento do que saiu do Notion:
   - com token → sincroniza pela API aqui mesmo;
   - sem token → prepara a varredura pelo conector do Claude (mcp-inicio) e mostra a fila. A IA busca cada
     item e fecha com `notion_sync.py mcp-fim --arquivar` (docs/sincronizar.md §3). Código de saída 10.
3. kb.py atualizar: índice, INDEX.md, casos_notion.md, troubleshooting.md.

A pasta docs/hardware/ é do usuário (cópia manual do firmware): nada aqui mexe nela.
"""

import os
import sys
import argparse
import subprocess

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

TOOLS = os.path.dirname(os.path.abspath(__file__))
ENV = dict(os.environ, PYTHONIOENCODING='utf-8')


def run(*args, timeout=1800):
    print(f'\n$ python {" ".join(args)}', flush=True)
    res = subprocess.run([sys.executable, os.path.join(TOOLS, args[0]), *args[1:]], env=ENV, timeout=timeout)
    return res.returncode


def main():
    p = argparse.ArgumentParser(prog='sincronizar', description='sincroniza docs/ com o servidor e o Notion')
    p.add_argument('--sem-snapshot', action='store_true', help='não baixa o banco de produção')
    p.add_argument('--sem-servidor', action='store_true')
    p.add_argument('--sem-notion', action='store_true')
    args = p.parse_args()
    status = {}

    contractChanged = False
    if not args.sem_servidor:
        status['servidor'] = run('servidor.py', 'resumo' if args.sem_snapshot else 'tudo')
        # contrato da API/banco × referência salva: != 0 = o servidor mudou ou falta algo que as IAs usam
        contractChanged = run('contrato.py', 'diferenca') != 0

    notionPending = False
    if not args.sem_notion:
        sys.path.insert(0, TOOLS)
        import notion_sync
        token, _ = notion_sync.findToken()
        if token:
            status['notion'] = run('notion_sync.py', 'sincronizar', '--arquivar')
        else:
            notionPending = True
            run('notion_sync.py', 'mcp-inicio')

    if not notionPending:
        status['kb'] = run('kb.py', 'atualizar')
    run('kb.py', 'novidades')

    print('\n=== resumo ===')
    for step, code in status.items():
        print(f'{step}: {"ok" if code == 0 else f"falhou (código {code})"}')
    if contractChanged:
        print('servidor: O CONTRATO MUDOU (rotas, campos, tabelas ou migrações) → siga docs/migracao_servidor.md\n'
              '          antes de usar Tester/Helper/Scanner em produção (diferença listada acima).')
    if notionPending:
        print('notion: SEM TOKEN → varredura pelo conector do Claude. Siga docs/sincronizar.md §3: para cada item de\n'
              '        `notion_sync.py mcp-proximos`, busque (notion-fetch / notion-query-data-sources), entregue\n'
              '        (mcp-pagina / mcp-banco) e repita até a fila esvaziar; feche com `mcp-fim --arquivar`.\n'
              '        Sem conector (Gemini): peça o token ao usuário (docs/sincronizar.md §4).')
        return 10
    return 0 if all(c == 0 for c in status.values()) else 1


if __name__ == '__main__':
    sys.exit(main())
