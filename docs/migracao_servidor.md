# Quando o servidor muda (migração das IAs)

O servidor de produção (`etilometro-server-v2`, Django, `https://sighir.com:8000/api/v2`) muda com frequência
e o código dele **não está nesta máquina**. Este é o roteiro para descobrir o que mudou, adaptar Tester,
Server (Scanner) e Helper e provar que tudo funciona.

**Gatilhos** (siga sem perguntar): "o servidor mudou", "mudaram as tabelas", "migração", "atualizaram a API",
erro 404/400 novo em qualquer IA, ou o aviso **"O CONTRATO MUDOU"** no fim do `sincronizar.py`.

Além da API e do banco, o servidor tem **serviços satélites** em sessões `screen` (`api` = gunicorn,
`mix` = integração MiX, `suntech` = `telemetry-panel` Suntech/Entrack). Se um parar, a API continua de pé e
os logs daquela telemetria simplesmente somem — foi o que aconteceu com a MiX em 24/09/2026.

Regra de ouro: **descobrir e testar só lendo**. Escrever em produção só no fim, com o ok do usuário.

## 1. Descobrir o que mudou (5 min)

```bash
python docs/tools/servidor.py snapshot        # banco novo (precisa de ../Etilometro/pwdsighir.pem)
python docs/tools/contrato.py diferenca       # API + banco agora × docs/servidor_contrato.json
```

O `diferenca` lista, contra a última referência salva:
- rotas da API novas/sumidas (raiz do router + `companies/`);
- campos de **leitura** (chaves de uma linha) e de **escrita** (`OPTIONS`: tipo, obrigatório, só leitura,
  tamanho, escolhas) novos, sumidos ou alterados;
- tabelas/colunas do banco e **migrações novas** (`django_migrations`, pelo snapshot);
- para cada coisa sumida/alterada, **onde o repositório usa** (`arquivo:linha`);
- e roda o `verificar`: o que cada IA lê e grava (tabela `USO` do `contrato.py`) ainda existe?

`python docs/tools/contrato.py uso` imprime a tabela rota/campo → quem usa.

## 2. Entender a mudança (medir, não supor)

- **Nomes de migração contam a história** (`0031_rename_suntech_telemetry…`). Leia as colunas novas no snapshot
  e conte com SQL: `python -c "import sqlite3; c=sqlite3.connect('file:docs/ServerAnalysis/files/db.sqlite3?mode=ro', uri=True); …"`.
- Dados migrados: compare tabelas de backup (`_bkp_*`) com a tabela nova (vínculos que não voltaram).
- Efeito nos logs: logs por telemetria antes × depois da hora da migração (`applied` em `django_migrations`).
  Foi assim que se achou a MiX muda desde 24/09/2026.
- **Como a API valida um campo, sem gravar**: `POST` com payload inválido de propósito (ex.: `"id": ""`, ou
  `device` inexistente) → o DRF responde 400 com o erro de cada campo e não grava nada. Mostra se um campo
  é texto livre (ex.: `plate` aceita placa nova), chave estrangeira (`Invalid pk`), escolha ou obrigatório.
  Confira sempre que a resposta foi ≥ 400; nunca mande payload que possa passar.
- Instalações feitas pelos apps depois da migração (no snapshot) mostram o caminho que o próprio servidor usa.

## 3. Onde mexer

| Peça | Arquivos | Teste offline |
|---|---|---|
| Tester: cadastro e instalação | `Tester/tools/sighir.py` (`register`, `install`, `edit`, `ensureModule`, `server-device`, `server-delete`), `Tester/objects/Server/index.py` (menu antigo), `Tester/utils/api.py` (só se mudar auth/URL) | `Tester/tools/test_cli.py` |
| Server: scanner | `Server/scanner/scan.py` (`update`: frota e logs; `getRow`; `getSensors`: SQL do snapshot; `send`: anomalies), `Server/scanner/api.py` (trava: só `anomalies/`) | `Server/scanner/test_scan.py` |
| Helper | `Helper/tools/helper.py` (`veiculo`, `device`, `lista`, `moduleOf`, `patch`), `Helper/tools/api.py` (`WRITABLE`) | `Helper/tools/test_helper.py` |
| Ferramentas da base | `docs/tools/servidor.py` (resumo da frota), `docs/tools/contrato.py` (`USO`) | `docs/tools/test_contrato.py` |
| Documentos | `docs/server_reference.md` (§2 esquema, §4 instalar, §6 rotas), `docs/portal_app.md` §4, `docs/telemetrias.md`, `Tester/procedimentos/cadastro.md` §6/§13, `AGENTS.md` das 3 IAs (≤ 12 mil caracteres), `Server/README.md` | — |

Ao mudar o que uma IA lê ou grava, **atualize o `USO` do `contrato.py`** — é ele que o `verificar` cobra.
Escreva o teste offline com o formato novo (API falsa) antes de rodar contra a produção.

## 4. Provar que funciona

```bash
python docs/tools/testar.py --completo        # offline + produção em só leitura + check seco do Scanner
python docs/tools/testar.py --bancada         # se mexeu no Tester e há aparelho na USB
```

Depois, o roteiro de gravação de `docs/testes.md` §3 (com o ok do usuário), começando pelo que a migração
tocou. Gravação que nunca foi exercitada no modelo novo fica marcada como **não verificada** nos docs até
a primeira vez dar certo.

## 5. Fechar

1. Docs atualizados (tabela do §3) e o histórico abaixo.
2. `python docs/tools/contrato.py capturar` — o servidor de agora vira a referência (`docs/servidor_contrato.json`, versionado).
3. Resumo ao usuário: o que mudou no servidor, o que foi adaptado em cada IA, testes (n/n), o que ficou
   pendente ou é problema do próprio servidor.

## Histórico

### 24/09 a 06/10/2026 — migrações `0030`–`0033` ("CHALLENGE — consertar servidor")

**Servidor:** a instalação passou para o `Device` (`plate` → `Vehicle`, `telemetry_company` = CNPJ,
`telemetry` = módulo, `installer`, `installation_date`, `installation_data`, `is_operating`); `suntechs` →
`telemetries` (com o `chip`; `/suntechs` dá 404); `Log.device_id` em todo o histórico (a API passou a devolver
todos os logs); `Anomaly.vehicle` → `Vehicle.id`; `Etilometro` congelada em 18/09/2026; `/etilometers` virou
visão dos devices instalados (`id` = ESP ID). `Device.telemetry` é único (1 módulo por aparelho).

**Adaptado (07/10/2026):**
- Tester: `register` cria o módulo em `/telemetries` (com o chip) e grava `telemetry` no device (`--modulo`,
  alias `--suntech`); `install` = `PATCH /devices/<MIC>` com `plate`, `vehicle_type`, `telemetry_company`,
  módulo, instalador, `--maleta`/`--observacao`; recusa ID de aparelho como módulo e módulo de outra placa;
  `server-delete` e menu antigo (`objects/Server/index.py`) no modelo novo. Testes: `tools/test_cli.py`.
- Server: SQL de reserva do snapshot lê `Device`+`Vehicle`; aviso de logs sem placa medido a cada execução.
- Helper: módulo via `devices/<MIC>.telemetry` → `telemetries/<id>`; `WRITABLE` com os campos de instalação
  no device e o chip em `telemetries`; `etilometers/` só leitura.

**Pendências (todas fechadas em 07/10/2026):**
- **MiX sem logs de 24/09 15h39 a 07/10 13h21 (UTC).** Causa: o serviço de integração MiX
  (`/home/ubuntu/v2/telemetries/mix`, sessão `screen` `mix`) foi parado com Ctrl+C às 15h39 de 24/09, dois minutos
  depois da migração 0030; o código dele foi adaptado ao modelo novo às 18h17 (busca o aparelho por
  `devices/?plate=`), mas o serviço nunca foi religado. Religado em 07/10 13h21 UTC (`python3 main.py` na mesma
  sessão); logs MiX voltaram em minutos. A correlação "só chega log de quem tem módulo vinculado" era
  coincidência: Suntech/Entrack entram por outro serviço (`telemetry-panel`). Os eventos MiX do intervalo não
  foram recuperados (o serviço recomeça do "agora").
- Vínculos do backup que "sumiram": não é perda — os módulos foram remanejados (1700009988 → TTB8B76 e
  1700023896 → JAX7B99, Ricker, ativos). EMP009 e SSA7F80 (Predileto) ficaram sem módulo (último log 03/11/2025
  e 18/08/2026).
- Módulo com o ESP ID (`MIC2757626176655517`): já tinha sido apagado; o aparelho 00369 (Transmaquina) está com o
  módulo 1700023885, em estoque, saída marcada para 08/10.
- **Gravação do Tester verificada em produção** com um aparelho de estoque da Sighir na placa `BANCADA`:
  `install`, `edit --desinstalar`, `edit --modulo` (cria o módulo em `/telemetries` com chip) e `--modulo none`
  — tudo conferido e devolvido ao estado original; o módulo de teste foi apagado.

**Lição:** depois de uma migração, confira se os **serviços satélites** voltaram — `screen -ls` no servidor
(`api`, `mix`, `suntech`/`telemetry-panel`) e logs chegando por telemetria (`testar.py --api` faz as duas
coisas).
