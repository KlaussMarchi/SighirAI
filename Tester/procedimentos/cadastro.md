# Cadastro de dispositivos e operações no servidor

> Movido do manual antigo (GEMINI.md §6 e §13), sem cortes. Numeração original mantida.

## 6. Procedimento de Cadastro

> Pré-requisito: firmware `ok` (`procedimentos/firmware.md` §5). Se `below_min`/`old`, atualize antes.

1. **`esp_id` nativo**: o cadastro exige `esp_id` começando com `MIC`. Se vier
   `admin_sighir` (ou outro valor de config sobrescrita), é preciso **erase** para
   regenerar o ID nativo. A CLI faz isso automaticamente no `register` (e há o
   comando `erase` dedicado).
2. **Dados automáticos** (lidos do device): `esp_id` (`MIC...`), `sensor_id` (`ETL...`).
3. **Empresa — SEMPRE PERGUNTE, LISTANDO NO CHAT.** Nunca escolha a empresa sozinho e nunca assuma
   a última usada. Rode `register` sem `--company` para buscar as empresas (`/companies`) e
   **escreva a lista completa na resposta do chat** (não escondida num seletor de opções), e então
   pergunte qual ele quer — junto com os outros dados que faltam (ID do módulo, chip).
   Número de série: use `auto` salvo se ele pedir outro.
4. **ID do módulo de telemetria (`--modulo`, antigo `--suntech`) — não é só do Suntech.** O **Entrack
   também tem um ID de módulo**, cadastrado igual. Desde a migração do servidor (24/09/2026) o módulo mora
   em **`/telemetries`** (era `/suntechs`, hoje 404) **junto com o chip** (`--chip`, pode ser `N/A`), e o
   aparelho aponta para ele no campo `telemetry`. Um módulo só pode estar em **um** aparelho.
   Só use `--modulo none` quando **não houver módulo nenhum** (MiX).
   → **Pergunte SEMPRE ID do módulo e chip — em Suntech E em Entrack.** **MIX é a exceção — não pergunte
   chip.** Nada disso dá pra ler pela USB na bancada (o `AT+ID?` do Entrack só responde com o rastreador
   conectado), então **é sempre pergunta ao usuário, nunca suposição**. ID começando com `MIC`/`ETL` é do
   aparelho/sensor, não do módulo (erro real de 06/10/2026: módulo criado com o ESP ID) — a CLI recusa.
4b. **Já existe?** Antes de gravar, o `register` procura o aparelho (`MIC…`), o sensor (`ETL…`, em outro
   aparelho), o módulo (em outro aparelho) e a série. Achou → **não grava**, sai com código 4 e mostra onde
   está + opções, por exemplo:
   ```
   Este etilômetro MIC… JÁ ESTÁ CADASTRADO: MIC… — empresa EXPRESSO PREDILETO, série 00032, sensor ETL…,
   placa RJT5E02 (SUNTECH, instalado 2026-02-06), módulo 1700006560 (Suntech)
      opção 1: editar o cadastro existente: tools/sighir.py edit MIC… --company logika --desinstalar …
      opção 2: deixar como está (o cadastro já está certo)
      opção 3: apagar e cadastrar de novo (perde o histórico)
   ```
   Apresente ao usuário e **pergunte**. Módulo em outro aparelho: mover (`edit <antigo> --modulo none`),
   usar outro ou cadastrar sem módulo. Sensor em outro aparelho: corrigir o antigo, conferir o sensor ou
   `--forcar`. Consulta avulsa: `python tools/sighir.py onde <MIC|ETL|módulo|placa|série>`.
5. **Registro**: `POST /telemetries` (se houver módulo novo) → `POST /devices` com `company`, `series_num`,
   `id`, `sensor_id`, `need_update: true` e `telemetry`.

Exemplo (Suntech **ou** Entrack — mesmo campo):
```
python tools/sighir.py register --company logika --series auto --modulo 1700023879 --chip N/A
```
(rode sem `--company` para listar os valores de empresa disponíveis.)

Após cadastrar: **cole a etiqueta** com o número de série no aparelho.

### 6.1 Aparelho que voltou / troca de cliente (editar, não cadastrar de novo)

Ex.: o aparelho era da Predileto, voltou, vai ser testado e enviado para a Logika. O cadastro **já existe**:
edite só o que muda com `edit` (o histórico de logs e o número de série continuam).

1. Na bancada: `init` (firmware `ok`), testes do aparelho (`docs/testes.md` §3) e, se trocou o sensor,
   use `--sensor usb` (lê o `sensor_id` do aparelho conectado e confere se é o mesmo `esp_id`).
2. Pergunte ao usuário: empresa nova (liste os valores), ID do módulo novo e chip (Suntech/Entrack), se sai
   da placa antiga (normalmente sim).
3. Prévia: `python tools/sighir.py edit <esp_id> --company logika --desinstalar --modulo <ID> --chip <N>`
   → mostra o cadastro de hoje e só as alterações (antes → depois). Nada é gravado.
4. Confirme com o usuário e repita com `--yes`: cria/atualiza o módulo em `/telemetries`, faz o `PATCH
   /devices/<esp_id>` e confere cada campo.
5. Na instalação no cliente novo: `install <esp_id> --placa ... --telemetria ...`.

| Opção | Efeito no servidor |
|---|---|
| `--company X` | `company` (transportadora dona). Com o aparelho ainda numa placa, exige `--desinstalar` (ou `--forcar`) |
| `--desinstalar` | tira da placa: `plate`, `telemetry_company`, `installation_date` = nulos; `installer`, `nickname` vazios; `installation_data` = `{}` |
| `--modulo ID` / `--modulo none` | troca / desvincula o módulo (`telemetry`); módulo novo é criado em `/telemetries` |
| `--chip N` | chip do módulo (novo ou o atual) em `/telemetries` |
| `--sensor ETL…` / `--sensor usb` | `sensor_id` (troca de sensor) |
| `--series N` | `series_num` (recusa número já usado por outro aparelho) |
| `--rearmar` | `need_update = true` |

Ao tirar da placa, veja se há alerta aberto da placa antiga (`python ../Helper/tools/helper.py anomalias PLACA`).

---

## 13. Integração com Servidor Django (`etilometro-server-v2`)

Servidor Django em repositório `etilometro-server-v2` (fora desta máquina) (acesso **não-permanente**).
**Mapa completo do schema, API e procedimentos: `../docs/server_reference.md` — leia-o antes de qualquer operação de banco.**

**Tabelas (modelo desde a migração de 24/09/2026; esquema completo em `../docs/server_reference.md` §2):**
`Device` (aparelho **e** instalação, PK = ESP ID: `plate` → `Vehicle`, `telemetry_company` = CNPJ da telemetria,
`telemetry` = módulo, `installer`, `installation_date`, `installation_data`, `is_operating`), `Vehicle` (placa;
**sem rota** — o servidor cria/associa pela `plate` do device), `Telemetry` (módulo Suntech/Entrack + `chip`,
rota `/telemetries`), `Company` (`type=transportation`|`telemetry`). `Etilometro` é legado (congelado em
18/09/2026); `/etilometers` continua como **leitura** das instalações (`id` = ESP ID).

**Instalar um etilômetro** = associar o aparelho a uma placa: `PATCH /devices/<esp_id>` com `plate`,
`vehicle_type` (0 = caminhão, 1 = carro), `telemetry_company` (CNPJ da Company `type=telemetry`) e, em
Suntech/Entrack, `telemetry` (ID do módulo). Pergunte o que faltar.
1. **Valide** que o `Device` existe e **deduplique**: a placa já está em outro aparelho? o aparelho já está em
   outra placa? (é troca → confirme e use `--forcar`).
2. **Confirme os dados** com o usuário (grava em **produção**).
3. Grave com **`python tools/sighir.py install <esp_id> --placa ABC1D23 --telemetria mix2|mix|suntech|entrack
   [--modulo ID --chip N] [--tipo carro] [--maleta] [--observacao "..."] [--instalador Nome] [--yes]`**: faz
   1–2, resolve o CNPJ, cria/atualiza o módulo em `/telemetries`, mostra o payload, só grava com `--yes` e
   confere depois (`devices/<esp>` e `etilometers/`). Reinstalar na mesma placa mantém a data original.
4. Maleta de demonstração: `--maleta` (`installation_data.suitcase = 1`, como o app de instalação grava).

**Regras críticas de banco** (detalhe em `../docs/server_reference.md`):
- **Use `obj.save()`/`.create()` por instância — NUNCA `QuerySet.update()`**: `.update()` não dispara os signals que sincronizam os clientes (`SyncState.bump`).
- **Deletar = DELETE de verdade.** ⚠️ **`deleted=True` não apaga nada** — nenhum queryset do servidor filtra
  por `deleted` (é só um query param opcional do `IncrementalMixin`); o registro continua visível.
  Use `DELETE /api/v2/<recurso>/<pk>/` (204; confirme com um GET → 404). **Consulte o registro antes** e
  **confirme** ("Tem certeza que deseja deletar o veículo X?"). Apagar um `Device` não apaga o módulo nem a placa, mas os logs apontam para ele (`log.device`) e podem ir junto.
  Device: `python tools/sighir.py server-delete <esp_id>` (mostra o registro; só apaga com `--yes`). Outros recursos: `delete_req()` de `utils/api.py` num script em `scratch/`.
