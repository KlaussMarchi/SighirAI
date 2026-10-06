# Sincronizar os documentos ("sincronizar os documentos" / "sincronize com o notion")

Vale para qualquer sessão: raiz do repositório ou as IAs Tester, Server e Helper, em Claude ou Gemini,
Windows ou Linux. Atualiza **toda a base `docs/`** a partir das duas fontes vivas.

- **Notion:** a árvore inteira da página **Sighir Enterprise** (páginas, subpáginas, bancos, chamados,
  tarefas, troubleshooting, anexos), mesmo que o Notion tenha sido reorganizado.
- **Servidor de produção:** resumo da frota (`servidor_resumo.md`) e snapshot do banco. Só leitura.

**Não mexe** em `docs/hardware/`: o firmware é copiado pelo usuário, à mão.

Caminhos: na raiz use `docs/...`; dentro de uma IA use `../docs/...`.
A frase "sincronize com o notion" roda o mesmo fluxo; pode pular o servidor com `--sem-servidor`.

## 1. Rodar

```
python docs/tools/sincronizar.py               # ou --sem-snapshot (não baixa o banco de 148 MB)
```

O comando faz três coisas:

1. **Servidor:**
   - `servidor.py tudo` gera `servidor_resumo.md`: frota por telemetria e empresa, última comunicação,
     calibração, firmware em campo × catálogo, anomalias abertas e a tabela de instalações.
   - Com a chave `pwdsighir.pem` (variável `SIGHIR_PEM`, `../Etilometro/` ao lado do repositório ou
     `~/.ssh/`), baixa também o `ServerAnalysis/files/db.sqlite3`. Sem a chave, pula.
2. **Notion:**
   - **Com token:** sincroniza pela API ali mesmo, só o que mudou, e **arquiva** o que saiu do Notion.
   - **Sem token:** prepara a varredura pelo conector (`mcp-inicio`) e termina com **código 10**. Nesse
     caso, faça a §3.
3. **`kb.py atualizar`:** refaz o índice, o `INDEX.md`, o `casos_notion.md` e o `troubleshooting.md`,
   depois lista as novidades.

## 2. Qual caminho do Notion

`python docs/tools/notion_sync.py status`:

| Situação | Caminho |
|---|---|
| `API: token em ...` | automático no passo 1 (qualquer agente) |
| sem token, Claude com o conector Notion (`notion-fetch`, `notion-query-data-sources`) | §3 |
| sem token e sem conector (ex.: Gemini) | §5, ou pedir o token ao usuário (§4) |

## 3. Varredura pelo conector do Claude (sem token)

O `sincronizar.py` já rodou `mcp-inicio`: a fila tem a raiz e os bancos de `tools/notion.json`. Repita
até a fila esvaziar:

```
python docs/tools/notion_sync.py mcp-proximos
```

- **Página** → `notion-fetch <id>` → `notion_sync.py mcp-pagina <arquivo> [<arquivo>...]`
  - O resultado grande a ferramenta já salva em arquivo: passe esse caminho.
  - O resultado pequeno: salve o JSON inteiro, **exatamente como veio**, em `scratch/page_<id>.json`.
    Salve vários e entregue todos de uma vez.
  - As subpáginas e bancos citados no conteúdo **entram sozinhos na fila**. Os que ficam dentro da
    seção Credenciais não entram.
- **Banco** → `notion-query-data-sources {"mode":"rows","data_source_url":"<fonte>","limit":100}` →
  salve em `scratch/rows_<id>.json` → `notion_sync.py mcp-banco <id> scratch/rows_<id>.json`
  - As linhas novas ou alteradas entram na fila como páginas.
  - Bancos "só tabela" (estoque, fornecedores; ver `so_tabela`) gravam só o CSV.
  - Se aparecer **has_more**: faça `notion-fetch` do banco, pegue uma view e consulte em
    `{"mode":"view","view_url":...,"page_size":100}` seguindo o `start_cursor`. Passe todos os
    arquivos no mesmo `mcp-banco`.
  - Banco sem fonte: `notion-fetch <id>` → `mcp-fonte <id> collection://…`.
- Fila vazia → `python docs/tools/notion_sync.py mcp-fim --arquivar`. Esse passo:
  - salva o estado;
  - move para `Notion/.antigos/<data>/` o que não veio do Notion (recuperável);
  - gera o `notion_mapa.md`;
  - roda o `kb.py atualizar`.

  Com a fila ainda cheia, ele **não arquiva nada**.

Limites do conector:
- **Não baixa PDFs:** um PDF novo no Notion aparece como "sem cópia local" (a API baixa).
- Os links de bookmark (vídeos) não vêm.
- Pessoas vêm como id: o nome sai de `tools/notion.json` → `pessoas`. Pessoa nova: acrescente lá.
- A mudança num chamado é detectada pelas propriedades da linha. Texto editado sem mudar propriedade:
  `mcp-banco ... --todas`.

## 4. Token da API (uma vez por máquina, feito pelo usuário)

1. Em notion.so/profile/integrations, crie uma **Nova integração** interna no workspace da Sighir, com
   **Ler conteúdo** (e ler usuários).
2. Copie o *Internal Integration Secret* (`ntn_...`).
3. No Notion: **Sighir Enterprise** → ••• → **Conexões** → adicione a integração.
4. `python docs/tools/notion_sync.py token ntn_...` (fica em `docs/.notion_token`, fora do git), ou a
   variável `NOTION_TOKEN`.

## 5. Sem token nem conector

Export manual: no Notion, ••• → Exportar → *Markdown & CSV* com subpáginas, substituindo `docs/Notion/`.
Depois, `python docs/tools/kb.py atualizar`.

## 6. Depois de sincronizar (sempre)

1. `python docs/tools/kb.py novidades`: leia o que é novo ou mudou.
2. **`troubleshooting.md` mudou:**
   - leve o passo novo para o sintoma correspondente do `diagnostico.md` (tabela "Checklist da equipe"
     em §0);
   - seção renomeada → ajuste o `CHECKLISTS` em `Helper/tools/helper.py` (o `test_helper.py` acusa).
3. **Chamado novo ou resolvido** (`casos_notion.md`): lição nova em `diagnostico.md`.
4. **Tarefas novas** (`notion_mapa.md` → Tarefas): mudança planejada no servidor, firmware ou instalação
   → registre em `server_reference.md` / doc do assunto e avise que a IA afetada pode precisar de ajuste.
5. **`servidor_resumo.md`:**
   - firmware novo no catálogo → confira `firmware_reference.md` e peça ao usuário a pasta
     `hardware/Main` nova, se ainda não veio;
   - telemetria ou empresa nova → `telemetrias.md`;
   - números da frota: cite o resumo, não copie para os docs curados.
6. Registre a revisão: `kb.py revisado "<arquivo>" --descricao ... --quando ...`.
7. Resuma ao usuário:
   - Notion: novos, alterados e arquivados;
   - o que mudou no troubleshooting e nos chamados;
   - servidor: frota, anomalias e firmware;
   - o que você levou para os docs curados e o que precisa de resposta dele.

## Regras

- **Nunca** copie senhas ou logins do Notion (seção Credenciais, `Handover.pdf`) para docs, chamados ou
  respostas. O sincronizador já omite a seção.
- Gerados (não edite; corrija na fonte e sincronize): `Notion/`, `casos_notion.md`, `troubleshooting.md`,
  `notion_mapa.md`, `servidor_resumo.md` e o bloco automático do `INDEX.md`.
- Sincronizar só **lê** o Notion e o servidor. Escrever em qualquer um dos dois só com pedido explícito.
- Testes, sem rede: `python docs/tools/test_notion_sync.py`.
