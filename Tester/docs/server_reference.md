# Referência do Servidor — `etilometro-server-v2` (Django)

> Fonte: leitura completa de `/home/klauss/Projects/etilometro-server-v2` (acesso **único**).
> Consolidado aqui porque o Sighir Tester AI **não tem acesso permanente** ao repositório do servidor.
> Este é o mapa canônico do schema, da API e dos procedimentos de banco (instalar/editar/deletar).

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
from apps.Etilometros.models import Device, Etilometro, Company, Suntech
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

### `Device`  (hardware físico — o ESP)
| Campo | Tipo | Notas |
|---|---|---|
| `id` | Char(30) **PK** | **ESP ID** (ex.: `MIC...`) |
| `company` | FK→Company **(obrigatório)** | dono/transportadora (`company_id`) |
| `sensor_id` | Char(30) | cartucho `ETL...` |
| `series_num` | Char(30) | nº de série (etiqueta) |
| `suntech` | FK→Suntech (nullable) | vínculo com módulo Suntech |
| `need_update` | Bool (default **True**) | dispara OTA |
| `chip` | Char | chip do rastreador |
| `software_version` | Char (default `1.0.0`) | |
| `location`, `update_settings`, `default_settings` | | |
> `Device.save()` no CREATE com `suntech` preenchido vincula `suntech.device = self` automaticamente.

### `Etilometro`  (instalação: device ↔ veículo) — **alvo de "instalar etilômetro"**
| Campo | Tipo | Notas |
|---|---|---|
| `id` | UUID **PK** | auto |
| `device` | FK→Device (nullable) | `device_id` = ESP ID |
| `telemetry` | FK→Company (nullable) | `telemetry_id` = CNPJ de uma Company **type=`telemetry`** |
| `vehicle_plate` | Char(20) | **sem unique** → deduplicar manualmente |
| `vehicle_type` | Int | **0=Caminhão, 1=Carro** |
| `installer` | Char | **string livre** (nome do instalador), não é FK |
| `installation_date` | DateTime (default now) | |
| `camera_service` | Char | `None` ou `movieit` |
| `is_operating` / `is_active` | Bool (default True) | |
| `nickname` | Char | |
| `need_update` | Bool (default True) | |

### `Suntech`  (módulo rastreador)
| Campo | Tipo | Notas |
|---|---|---|
| `id` | Char(40) **PK** | ID Suntech |
| `device` | FK→Device (nullable) | |
| `model`, `ip`, `port`, `last_stt` | | |
| flags | Bool | `has_to_block`, `has_to_unblock`, `is_connected`, `is_ignition_on`, `is_relay_on` |

### Outros: `Sensor` (PK id, `current_calibration`), `Solution`, `Calibration` (analog/mgl/timestamp), `Log` (event/etilometer/timestamp), `Firmware` (version/release_date), `SensorReplaceLog`.

---

## 3. Sincronização (CRÍTICO p/ escrever no banco corretamente)

`server/signals.py` conecta **`post_save` e `post_delete`** de **todos** os modelos a `SyncState.bump(<recurso>)` + `bump("global")`. Os clientes (painéis/telemetria) puxam mudanças pela versão do `SyncState`.

**Regras que decorrem disso:**
1. **Use sempre `obj.save()` por instância** (ou `Model.objects.create(...)`). Isso dispara o signal → bump → os clientes recebem a mudança.
2. **NUNCA use `QuerySet.update(...)`** para mudanças que precisam propagar: `.update()` **não dispara signals** → **sem bump** → clientes ficam dessincronizados. Itere e use `.save()`.
3. **Deletar = DELETE de verdade (hard delete).** ⚠️ **`deleted=True` NÃO apaga nada** — verificado no
   código (`docs/server/server`): nenhum ViewSet sobrescreve `destroy`/`perform_destroy`, os querysets são
   `.all()` **sem filtro de `deleted`**, e o campo só existe como *query param opcional*
   (`?deleted=true/false`) no `IncrementalMixin` (`apps/sync/views.py:19-25`). Marcar `deleted=True`
   deixa o registro **visível em tudo**. Para remover de fato: `DELETE /api/v2/<recurso>/<pk>/`
   (ModelViewSet padrão) ou `obj.delete()` no ORM — ambos disparam `post_delete` → bump.

---

## 4. Procedimento: **Instalar um Etilômetro**

Significa **criar uma linha em `Etilometro`** ligando um `Device` (ESP ID) a uma placa de veículo.

**Parâmetros obrigatórios (perguntar ao usuário se faltarem):**
1. `vehicle_plate` — placa do veículo.
2. `device` — ESP ID (precisa existir em `Device`; se não existir, cadastrar antes via `tools/sighir.py register`).
3. `telemetry` — empresa de telemetria (Company `type=telemetry`); busque o CNPJ pelo `label`.
4. `vehicle_type` — 0 (Caminhão) ou 1 (Carro).
Opcionais úteis: `installer` (nome), `camera_service`, `nickname`.

**Passo a passo (sempre validar antes de criar):**
1. Confirme que o **Device existe**. Se não, pare e oriente cadastrar o device primeiro.
2. Resolva a **telemetria** (`Company.objects.filter(type='telemetry', label__icontains=<nome>)`) → pegue o CNPJ.
3. **Deduplicação**: verifique se já há `Etilometro` ativo (`deleted=False`) para esse `device` ou `vehicle_plate`. Se houver, **avise e pergunte** se é troca/edição em vez de criar duplicado.
4. **Confirme os dados com o usuário** (operação grava em produção).
5. Crie.

### Caminho A — API (recomendado, validado)
`POST /api/v2/etilometers/` (JWT). Serializer exige no CREATE: **`device`** (PK = ESP ID) e **`vehicle_plate`**.
```json
{ "device": "MIC...", "vehicle_plate": "ABC1D23", "telemetry": "<CNPJ>",
  "vehicle_type": 0, "installer": "Fulano", "camera_service": "None" }
```

### Caminho B — ORM (na instância do servidor)
```python
dev = Device.objects.filter(id=esp_id).first()
assert dev, 'Device inexistente — cadastre primeiro'
tel = Company.objects.filter(type='telemetry', label__icontains=tel_name).first()
if Etilometro.objects.filter(device=dev, deleted=False).exists():
    ...  # avisar: ja existe instalacao p/ esse device
etl = Etilometro.objects.create(
    device=dev, telemetry=tel, vehicle_plate=plate,
    vehicle_type=vtype, installer=installer)
# save() do create() ja disparou post_save -> SyncState bump (propaga aos clientes)
```

---

### 4.1 `software_version` mente (e o catálogo `/firmwares` também)
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
  FKs em cascata caem junto: apagar um `Device` leva embora o `Suntech` vinculado (visto na prática).
- ⚠️ **`utils/api.py` do tester não tem `delete_req`** (só GET/POST/PATCH). Para deletar, monte o
  `requests.delete()` num script de `scratch/` reaproveitando `API` + `handle_access_token()` da `utils.api`.
- Operações que gravam em **produção** exigem confirmação dos dados antes de executar.

---

## 6. Referência rápida de rotas da API (`/api/v2/`)

- **Router DRF** (CRUD): `devices`, `etilometers`, `suntechs`, `sensors`, `solutions`, `firmwares`, `calibrations`, `logs`.
- **Views**: `companies/`, `users/`, `settings/<company>`, `sync-status/`, `token/` + `token/refresh/`, `login/`, `upload-images/`, `camera-services/`.
- **Legacy (device)**: `/update/`, `/check/`, `/validateSensor/`, `/checkSettings/`.
> Atenção ao plural da rota: **`etilometers`** (CRUD de instalações), **`devices`** (hardware), **`companies/`** (empresas/telemetrias).
