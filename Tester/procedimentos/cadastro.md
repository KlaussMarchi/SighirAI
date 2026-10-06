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
4. **ID do módulo de telemetria — o campo `--suntech` NÃO é só do Suntech.** O **Entrack também tem
   um ID de módulo, e ele é registrado no mesmo campo/endpoint**, exatamente igual (`POST /suntechs`
   + `--suntech <id>`). O `chip` (`--chip`) é um campo **separado** do ID e pode ser `N/A`.
   Só use `--suntech none` quando **não houver módulo nenhum**.
   → **Pergunte SEMPRE ID do módulo e chip — em Suntech E em Entrack.** O chip não é exclusivo do
   Suntech: no Entrack pergunte igual, se vai entrar um número ou se fica `N/A`. **MIX é a exceção —
   não pergunte chip.** Nada disso dá pra ler pela USB na bancada (o `AT+ID?` do Entrack só responde
   com o rastreador conectado), então **é sempre pergunta ao usuário, nunca suposição**.
5. **Registro**: `POST /devices` com `need_update: true`.

Exemplo (Suntech **ou** Entrack — mesmo campo):
```
python tools/sighir.py register --company logika --series auto --suntech 1700023879 --chip N/A
```
(rode sem `--company` para listar os valores de empresa disponíveis.)

Após cadastrar: **cole a etiqueta** com o número de série no aparelho.

---

## 13. Integração com Servidor Django (`etilometro-server-v2`)

Servidor Django em repositório `etilometro-server-v2` (fora desta máquina) (acesso **não-permanente**).
**Mapa completo do schema, API e procedimentos: `../docs/server_reference.md` — leia-o antes de qualquer operação de banco.**

**Tabelas (em `apps/Etilometros/models.py`):** `Device` (hardware, PK=ESP ID), `Etilometro` (instalação device↔veículo, PK=UUID), `Company` (empresas; `type=transportation`|`telemetry`), `Suntech` (módulo). Todas têm soft-delete (`deleted`).

**Instalar um etilômetro** = criar uma linha em `Etilometro`. Obrigatórios (pergunte se faltarem): `device` (ESP ID, deve existir em `Device`), `vehicle_plate`, `telemetry` (Company `type=telemetry`, busque o CNPJ pelo `label`), `vehicle_type` (0=Caminhão, 1=Carro).
1. **Valide** que o `Device` existe e **deduplique** (já há `Etilometro` ativo p/ esse device/placa?).
2. **Confirme os dados** com o usuário (grava em **produção**).
3. Crie com **`python tools/sighir.py install <esp_id> --placa ABC1D23 --telemetria mix2|mix|suntech|entrack [--tipo carro] [--instalador Nome] [--yes]`**: o comando faz os passos 1–2 (device existe? placa/aparelho já instalados?), resolve o CNPJ da telemetria, mostra o payload e só grava com `--yes`, conferindo depois. Sem a CLI: `POST /api/v2/etilometers/` (JWT) com `device`, `vehicle_plate`, `telemetry` (CNPJ), `vehicle_type`.
4. A tabela `Vehicle` (usada pelas anomalias) **não tem rota na API**: placa nova precisa ser cadastrada como veículo pelo painel/admin, senão o Scanner recebe 400 ao criar alerta para ela.

**Regras críticas de banco** (detalhe em `../docs/server_reference.md`):
- **Use `obj.save()`/`.create()` por instância — NUNCA `QuerySet.update()`**: `.update()` não dispara os signals que sincronizam os clientes (`SyncState.bump`).
- **Deletar = DELETE de verdade.** ⚠️ **`deleted=True` não apaga nada** — nenhum queryset do servidor filtra
  por `deleted` (é só um query param opcional do `IncrementalMixin`); o registro continua visível.
  Use `DELETE /api/v2/<recurso>/<pk>/` (204; confirme com um GET → 404). **Consulte o registro antes** e
  **confirme** ("Tem certeza que deseja deletar o veículo X?"). Cascata: apagar um `Device` leva o `Suntech` junto.
  Device: `python tools/sighir.py server-delete <esp_id>` (mostra o registro; só apaga com `--yes`). Outros recursos: `delete_req()` de `utils/api.py` num script em `scratch/`.
