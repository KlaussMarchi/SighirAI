# Referência do Servidor — `etilometro-server-v2` (Django)

> Fonte: leitura completa do repositório `etilometro-server-v2` (acesso **único**, fora desta máquina).
> Consolidado aqui porque as IAs **não têm acesso permanente** ao código do servidor.
> Este é o mapa canônico do schema, da API e dos procedimentos de banco (instalar/editar/deletar).
> Campos e filtros verificados na API de produção em 23/09/2026: `portal_app.md` §4.
> Nos exemplos, "a CLI" é a do Tester (`Tester/tools/sighir.py`, `Tester/utils/api.py`).
>
> **Reestruturação em produção desde 24/09/2026** (Notion → Tarefas → Servidor, "CHALLENGE — Consertar
> servidor"; migrações `0030`–`0033`, a última em 06/10/2026). Conferido no snapshot e na API em
> 07/10/2026 — o §2 já descreve o modelo novo:
> - A instalação passou para o **`Device`** (`plate_id` → `Vehicle`, `telemetry_company`, `installer`,
>   `installation_date`, `installation_data`, `is_operating`, `camera_service`, `nickname`). A rota
>   continua `etilometers/` (não virou `installed/`), agora com `id` = ESP ID. A tabela `Etilometro`
>   ficou **legada e congelada em 18/09/2026** (143 linhas; ainda existe no banco).
> - `suntechs` → **`telemetries`** (rota `telemetries/`; `suntechs/` dá 404); o `chip` foi para lá.
> - `Log` ganhou `device_id` (preenchido em todo o histórico); `Anomaly.vehicle` virou FK inteira para
>   `Vehicle.id` (a API continua lendo e escrevendo pela placa).
> - Ainda **não** feito: `deleted` continua nas tabelas; `vehicle_type` 2 (maleta) não existe no
>   `Vehicle` (a maleta aparece como `installation_data.suitcase = 1`); `series_num` automático e o
>   seletor MIX/Suntech/Entrack em `telemetries.model` não verificados (`model` hoje é `''` ou `Dummy`).
> - Serviços satélites (sessões `screen` no servidor): `api` (gunicorn), `mix` (integração MiX:
>   `telemetries/mix`, consulta a MiX a cada minuto e grava em `/logs` achando o aparelho por
>   `devices/?plate=`) e `suntech` (`telemetries/telemetry-panel`: Suntech/Entrack). **O `mix` ficou parado de
>   24/09 15h39 a 07/10/2026** (sem logs MiX nesse intervalo); religado. Depois de qualquer migração, confira
>   os três (`docs/migracao_servidor.md`).
>
> **Planejado** (Notion → Tarefas → Servidor, não iniciado em 07/10/2026): `companies` ganha `email`
> (nulo por padrão) e `alerts` (lista de eventos, ex. `["ETAT01", "ETEV30"]`): log com evento da lista →
> e-mail de relatório para a empresa. "Em hipótese alguma mudar rota do ESP32".

---

## 1. Infra e Execução

- **App**: Django + Django REST Framework (DRF). Settings module: **`server.settings`** (rodar de dentro de `etilometro-server-v2/server/`).
- **Banco**: **SQLite** em `server/db.sqlite3` — **fica na instância AWS de produção** (`srvsighir`, 52.91.100.216), **não há cópia local** neste ambiente.
- **API**: base **`/api/v2/`** (porta 8000 → `https://sighir.com:8000/api/v2`), autenticação **JWT** (`POST /api/v2/token/`). É a mesma API que a CLI `tools/sighir.py` já usa para `register`.
- **Apps**: `apps.Etilometros` (modelos do domínio), `apps.Users`, `apps.sync` (versionamento de sync), `api` (REST), `apps.files`.

### Como executar operações de banco (dois caminhos)

**A) Via API REST (preferido quando o servidor está acessível pela rede)** — validado, não exige Django local:
```
POST https://sighir.com:8000/api/v2/etilometers/   (JWT no header Authorization: Bearer <token>)
```
Reutilize a camada de auth da CLI (`utils/api.py` já tem credenciais + token).

**B) Via script Django ORM (quando rodando NA instância do servidor, onde o `db.sqlite3` e o Django existem)**:
```python
import os, django, sys
sys.path.insert(0, '/caminho/para/etilometro-server-v2/server')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
django.setup()
from apps.Etilometros.models import Device, Company, Telemetry, Vehicle   # Etilometro/Suntech: nomes antigos
# ... operações ...
```
ou `python manage.py shell -c "..."` de dentro de `server/`.
> ⚠️ Requer Django instalado **e** acesso ao `db.sqlite3` real. Neste ambiente local **não há
> Django nem o banco** — operações ORM só funcionam na instância AWS (via SSH com `pwdsighir.pem`)
> ou num ambiente espelhado. Para sessões locais, **prefira o caminho A (API)**.

---

## 2. Schema (tabelas em `apps/Etilometros/models.py`)

Todos herdam de **`BaseSyncModel`** → adicionam: `srv_created_at` (auto), `updated_at` (auto), **`deleted`** (BooleanField, *soft delete*).

### `Company`  (empresas: clientes E telemetrias)
| Campo | Tipo | Notas |
|---|---|---|
| `id` | Char(14) **PK** | **CNPJ** |
| `label` | Char(30) | Nome exibido (ex.: "Suntech", "Logika") |
| `type` | Char | **`transportation`** (cliente) ou **`telemetry`** (telemetria) |
| `value` | Char(30) | |
| `data` | JSON | dados específicos |
| `locations` | JSON (list) | locais/filiais |

### `Device`  (hardware físico — o ESP — **e a instalação**, desde 24/09/2026)
| Campo | Tipo | Notas |
|---|---|---|
| `id` | Char(30) **PK** | **ESP ID** (ex.: `MIC...`) |
| `company` | FK→Company **(obrigatório)** | dono/transportadora (`company_id`) |
| `sensor_id` | Char(30) | cartucho `ETL...` |
| `series_num` | Char(30) | nº de série (etiqueta) |
| `plate` | FK→Vehicle (nullable) | `plate_id` (inteiro); preenchido = **instalado** (148 em 07/10/2026; placa única por aparelho) |
| `telemetry_company` | FK→Company (nullable) | CNPJ de uma Company **type=`telemetry`** (2 instalados apontam para transportadora) |
| `telemetry` | FK→Telemetry (nullable) | módulo rastreador; **nulo na MiX** (ver o aviso no topo) |
| `installer` | Char | **string livre** (nome do instalador), não é FK |
| `installation_date` | DateTime | |
| `installation_data` | JSON | livre: `observation`, e na maleta `suitcase: 1` + parâmetros (`max_postpone`, `maneuver_time`…) |
| `camera_service` | Char | `None` ou `movieit` |
| `is_operating` | Bool (default True) | |
| `nickname` | Char | |
| `need_update` | Bool (default **True**) | dispara OTA |
| `software_version` | Char (default `1.0.0`) | ver §4.2 |
| `location`, `update_settings`, `default_settings`, `timestamp` | | |
> A coluna `chip` ainda existe no banco, mas a API de `devices/` não a expõe mais: o chip está em `telemetries/`.

### `Vehicle`  (placa)
`id` (inteiro), `plate`, `type` (0 = caminhão, 1 = carro; 149 linhas, só 0 e 1), `company`. **Sem rota na API.**
`Device.plate` e `Anomaly.vehicle` apontam para ele.

### `Telemetry`  (módulo rastreador; ex-`Suntech`, rota `telemetries/`)
| Campo | Tipo | Notas |
|---|---|---|
| `id` | Char(40) **PK** | ID do módulo (Suntech `1700…`, Entrack `69…`) |
| `vehicle` (API) | | placa do aparelho vinculado (só leitura; o filtro `?vehicle=` é ignorado) |
| `model`, `ip`, `port`, `last_stt`, `chip`, `lat`, `lon` | | |
| flags | Bool | `has_to_block`, `has_to_unblock`, `is_connected`, `is_ignition_on`, `is_relay_on` |

### `Etilometro`  (legado — **congelado em 18/09/2026**, não use)
Instalação antiga (UUID, `vehicle_plate`, `device`, `telemetry` = CNPJ, `is_active`…). Continua no banco
(143 linhas) só como histórico; logs anteriores à migração têm `etilometro_id`, e o `device_id` foi
preenchido a partir dele.

### Outros: `Sensor` (PK id, `current_calibration`), `Solution`, `Calibration` (analog/mgl/timestamp), `Log` (event, `device_id`, `etilometro_id` legado, timestamp, `created_at` do aparelho, `lat`/`lon`), `Anomaly` (`vehicle_id`, `category`, `desc`, `solved`), `Firmware` (version/release_date), `SensorReplaceLog` (sem rota).

---

## 3. Sincronização (CRÍTICO p/ escrever no banco corretamente)

`server/signals.py` conecta **`post_save` e `post_delete`** de **todos** os modelos a `SyncState.bump(<recurso>)` + `bump("global")`. Os clientes (painéis/telemetria) puxam mudanças pela versão do `SyncState`.

**Regras que decorrem disso:**
1. **Use sempre `obj.save()` por instância** (ou `Model.objects.create(...)`). Isso dispara o signal → bump → os clientes recebem a mudança.
2. **NUNCA use `QuerySet.update(...)`** para mudanças que precisam propagar: `.update()` **não dispara signals** → **sem bump** → clientes ficam dessincronizados. Itere e use `.save()`.
3. **Deletar = DELETE de verdade (hard delete).** ⚠️ **`deleted=True` NÃO apaga nada** — verificado no
   código do servidor (cópia lida em 2026, fora deste repositório): nenhum ViewSet sobrescreve `destroy`/`perform_destroy`, os querysets são
   `.all()` **sem filtro de `deleted`**, e o campo só existe como *query param opcional*
   (`?deleted=true/false`) no `IncrementalMixin` (`apps/sync/views.py:19-25`). Marcar `deleted=True`
   deixa o registro **visível em tudo**. Para remover de fato: `DELETE /api/v2/<recurso>/<pk>/`
   (ModelViewSet padrão) ou `obj.delete()` no ORM — ambos disparam `post_delete` → bump.

---

## 4. Procedimentos: **cadastrar** e **instalar** um etilômetro (modelo de 24/09/2026)

### 4.0 Cadastrar o aparelho (bancada)
1. Módulo Suntech/Entrack (se houver): `GET telemetries/<id>/`; não existe → `POST telemetries/`
   `{"id": "<ID do módulo>", "chip": "<chip>"}` (o chip mora aqui, não no device). ID começando com `MIC`/`ETL`
   não é módulo. `Device.telemetry` é **único**: um módulo só pode estar em um aparelho.
2. `POST devices/` `{"id": "MIC…", "company": "<CNPJ da transportadora>", "series_num": "00123",
   "sensor_id": "ETL…", "need_update": true, "telemetry": "<ID do módulo>"}` (`id` e `company` obrigatórios;
   `timestamp` é só leitura; `chip`/`suntech` não existem mais no device — a API ignora sem avisar).
3. CLI: `Tester/tools/sighir.py register --company <value> --modulo <ID|none> --chip <N|N/A>`.

### 4.1 Instalar (associar o aparelho a uma placa)
**Instalar = `PATCH devices/<MIC>/`** com a placa. O campo `plate` é texto: o servidor cria o `Vehicle` se a
placa não existe e associa (validação conferida em 07/10/2026 com payload inválido de propósito; os apps do
servidor criaram `Vehicle` assim em 30/09 e 06/10/2026). `etilometers/` continua aceitando o `POST` antigo
(`device` + `vehicle_plate`), mas é uma visão dos devices — use `devices/`.

**Pergunte o que faltar:** placa; ESP ID (precisa existir — senão cadastre antes); telemetria (Company
`type=telemetry` → CNPJ pelo `value`: MIX 0, Suntech 2, MIX 2.0 5, Entrack 6); tipo (0 caminhão, 1 carro);
em Suntech/Entrack, o ID do módulo e o chip. Opcionais: `installer`, `nickname`, `camera_service`,
`installation_data` (`observation`; maleta = `suitcase: 1`).

```json
PATCH devices/MIC…/
{ "plate": "ABC1D23", "vehicle_type": 0, "telemetry_company": "<CNPJ da telemetria>",
  "telemetry": "<ID do módulo, se Suntech/Entrack>", "is_operating": true,
  "installation_date": "2026-10-07T12:00:00+00:00", "installer": "Fulano",
  "installation_data": {"observation": "…"} }
```

**Antes de gravar:** a placa já está em outro aparelho (`etilometers/`, `vehicle`)? o aparelho já está em
outra placa (`devices/<MIC>.plate`)? → é **troca**: confirme com o usuário. Reinstalar na mesma placa não
muda a data de instalação. **Depois:** confira `devices/<MIC>/` (`plate`, `telemetry_company`, `telemetry`) e
`etilometers/` (a placa aparece com o `esp_id`).

**Editar / desinstalar / trocar de cliente** (aparelho que voltou): `PATCH devices/<MIC>/` só com o que muda
(`company`, `telemetry`, `sensor_id`, `series_num`…). Tirar da placa = `plate`, `telemetry_company` e
`installation_date` nulos (a API aceita `null` nesses campos — validação de 07/10/2026). CLI:
`Tester/tools/sighir.py edit <MIC> [--company X] [--desinstalar] [--modulo ID|none] [--chip N] … [--yes]`.

CLI: `Tester/tools/sighir.py install <MIC> --placa <P> --telemetria mix2|mix|suntech|entrack [--modulo ID
--chip N] [--tipo carro] [--maleta] [--observacao "…"] [--instalador N] [--forcar] [--yes]` (sem `--yes`
só mostra). Ajuste fino depois: `Helper/tools/helper.py patch devices <MIC> campo=valor [--sim]`.

> Gravação verificada em produção em 07/10/2026 (install → edit --desinstalar → edit --modulo, devolvido ao
> estado original). Suntech/Entrack: vincule o módulo (`telemetry`) — é por ele que o `telemetry-panel` acha o aparelho.

---

### 4.2 `software_version` mente (e o catálogo `/firmwares` também)
- **`Device.software_version` NÃO é atualizado pelo flash.** O device só reporta a versão dele no
  `GET api/v2/devices/check-update/?firmware=...`, que acontece **por WiFi** — com `wifi=false` (default de
  fábrica) o campo **congela**. Verificado: aparelho em `v6.4.4`, servidor dizendo `6.4.3`.
  → Depois de um `flash`, **leia a versão real no device** (`sighir.py firmware`) e, se for usar o campo do
  servidor, acerte-o: `PATCH /devices/<esp_id>` `{"software_version": "6.4.4"}`.
- **O catálogo `/firmwares` pode estar atrás do binário servido pelo `/update`** (visto: catálogo até
  `v6.4.2`, `/update` entregando `v6.4.4`). Não use `/firmwares` para decidir a versão que o device vai receber.

---

## 5. Editar / Deletar (com segurança)

- **Consultar sempre antes** de editar/deletar (mostre o registro atual ao usuário).
- **Editar**: carregue a instância, altere os campos, `obj.save()` (nunca `.update()`).
- **Deletar**: **pergunte e confirme** ("Tem certeza que deseja deletar o veículo X?") e então **delete de
  verdade**: `DELETE /api/v2/<recurso>/<pk>/` (204 = removido; confira com um GET → deve dar 404) ou
  `obj.delete()` no ORM. **Não use `deleted=True` achando que apagou** — não apaga (§3.3).
  FKs em cascata caem junto: apagar um `Device` levava embora o `Suntech` vinculado (visto na prática, antes de 24/09/2026).
- ⚠️ **`utils/api.py` do tester não tem `delete_req`** (só GET/POST/PATCH). Para deletar, monte o
  `requests.delete()` num script de `scratch/` reaproveitando `API` + `handle_access_token()` da `utils.api`.
- Operações que gravam em **produção** exigem confirmação dos dados antes de executar.

---

## 6. Referência rápida de rotas da API (`/api/v2/`)

- **Router DRF** (CRUD; raiz da API em 07/10/2026): `devices`, `etilometers`, `telemetries` (ex-`suntechs`, que dá 404), `sensors`, `solutions`, `firmwares`, `calibrations`, `logs`, `anomalies`, `user-connections`.
- **Views**: `companies/`, `users/`, `settings/<company>`, `sync-status/`, `token/` + `token/refresh/`, `login/`, `upload-images/`, `camera-services/`.
- **Legacy (device)**: `/update/`, `/check/`, `/validateSensor/`, `/checkSettings/`.
> Atenção ao plural da rota: **`etilometers`** (CRUD de instalações), **`devices`** (hardware), **`companies/`** (empresas/telemetrias).
