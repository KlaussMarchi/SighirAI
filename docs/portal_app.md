# Portal web, app, portais parceiros e API

> Fontes: `Notion/main 2.pdf` (MUWP 0001-01, portal), `Notion/main 1.pdf` (MUAM 0001-01, app),
> `Notion/api-logs.pdf`, `Notion/guia-integracao-camera.pdf`, `Notion/Handover.pdf`, `server_reference.md`,
> leitura da API de produção (23/09/2026). **Credenciais de portais parceiros ficam só na `Handover.pdf`
> — não copie para outros arquivos.**

## 1. Portal Web Sighir (sighir.com → "Área do cliente")

Login por e-mail/senha (cada empresa vê só a sua frota; contas Sighir veem todas). Menus:

| Menu | O que tem | Uso no suporte |
|---|---|---|
| **Controle** | visão de veículos/sensores, filtros (empresa, placa, datas), **Última Sincronização**, Dispositivos Instalados/Em Estoque, **Sensores Vencidos** (Ver mais), **Alterar Estado de Bloqueio** (cadeado), Últimos Eventos de Alerta, gráficos de testes e resultados | ver se a frota está sincronizando; bloqueio/desbloqueio remoto |
| **Mapa** | última posição (GPS do rastreador) | localizar veículo para atendimento |
| **Software** | versão mais recente, notas, **Atualizar Firmware** (selecionar dispositivos → pedido de update), **Configurar Parâmetros** (remoto) | disparar OTA (o aparelho baixa quando tiver Wi-Fi) |
| **Monitoramento** | todos os eventos (placa, empresa, tipo, evento, horário), filtros e CSV | reconstruir o que aconteceu |
| **Relatórios** | Calibração (certificado PDF por sensor) e Instalação (relatórios do app) | fiscalização/auditoria; conferir instalação |
| **Documentação** | manuais, datasheet, vídeos | |

**Bloqueio/desbloqueio remoto**: o portal manda o comando para a **telemetria**, que entrega ao
etilômetro (`$ETBL01!`/`$ETBL02!` → `$ETEV01!`/`$ETEV02!`; no servidor aparecem também `$ETEV37!`/`$ETEV38!`
"Bloqueio/Desbloqueio Remoto"). Veículo fora de cobertura → o portal avisa que não entregou; repetir depois.
Na MiX o equivalente é o **Relay 1** no portal da MiX (§3).

## 2. App Sighir Monitor (Android/iOS)

- Perfis: **Motorista** ("Entrar como Motorista", sem senha: acompanha testes; desbloqueio manual),
  **Instalador** (Nova Instalação, relatórios), **Técnico/admin** (diagnóstico extra, Testes de Protocolo).
  Login = mesmas credenciais do portal.
- Quase tudo fala **direto com o etilômetro pelo Wi-Fi dele** (`SIGHIR - MICxxxx`, senha `12345678`,
  **sem internet**): configurações, monitoramento ao vivo, desbloqueio. Login e envio ao servidor precisam
  da internet normal — o app avisa quando trocar de rede. Ícone de Wi-Fi no canto indica se está falando
  com o aparelho. Alguns celulares recusam Wi-Fi sem internet: tente outro aparelho.
- Telas: **Configurações do Etilômetro** (Desbloqueio com Senha, Ajustes de parâmetros, Verificar logs
  anteriores, Atualizar etilômetro, Monitorar dados, **Validar Sensor**/troca de sensor), **Nova
  Instalação** (checklist com fotos → configuração por arquivo ou manual → placa → Wi-Fi da base →
  checklist operacional sem álcool → fotos → OS assinada → Submeter), **Monitoramento de Logs**
  (Aceitando Dados, Ler, Copiar, Limpar), **Gráfico** (analog, pressão, temperatura, umidade ao vivo),
  **Desbloquear Veículo** ("Gerar Senha": calcula a contrassenha do desafio mostrado na tela —
  emergência sem internet), **Testes de Protocolo** (manda comando cru e mostra a resposta — equipe técnica).
- Atualização de firmware pelo app: Configurações → Atualizar Firmware → conectar no Wi-Fi do aparelho →
  informar a rede com internet → "Conectado" → Atualizar Firmware → acompanhar na tela do DAD01.

## 3. Portais das telemetrias (resumo da Handover — logins na própria Handover)

- **MiX Telematics** (us.mixtelematics.com): *Rastreamento ao vivo* → placa → ⋮ → *Comandos do
  dispositivo móvel* → **Relay 1 "Ligado"** (desbloquear em pane do etilômetro) / **"Desligado e solto"**
  (voltar ao normal); *Monitorar → Fluxos* mostra "Concluído" (~6 min); *Monitorar → Histórico de
  rastreamento* com filtro "Etilometro"; *Medir → Relatórios → Relatório detalhado do evento* (pesquisar
  "etilo"). Motorista não identificado aparece como "No Driver". Suporte MiX: contato na Handover.
- **SystemSat** (plataforma dos módulos Suntech — tracking.systemsatx.com.br): pesquisar a unidade/placa;
  *Enviar Comando* (bloqueio/desbloqueio/consulta) e ver o status; *Rastreamento → Eventos* (filtrar
  eventos do etilômetro); *Debug* mostra os pacotes brutos (com apoio da SystemSat).
- **Movieit** (movplay.com.br, cliente p157 = Predileto): *Auditagem → Relatórios → Ocorrências
  (Analíticas)*, grupo "Etilometro Suntech". Integração de câmera/computador de bordo pela USB.
- **Entrack**: configuração do módulo pelo software **AOVX** (porta COM → servidor/chip → SET; comandos AT).

## 4. API do servidor (`https://sighir.com:8000/api/v2/`)

Autenticação: `POST /token/` `{"username","password"}` → `access` (dura ~5 min) + `refresh`
(`POST /token/refresh/`). Header `Authorization: Bearer <access>`. Paginação `?limit=` (máx. 2000) e
`?page=`; siga o campo `next`. **Nunca use `limit=all`/`limit=0`** — o limite de segurança não funciona e
serializa a tabela inteira (derruba o servidor, SQLite num t2.large).

| Rota | Conteúdo útil | Filtros que funcionam |
|---|---|---|
| `etilometers/` | instalação (desde 24/09/2026 é o próprio `Device` com placa; 148 em 07/10/2026): `vehicle`, `esp_id`, `sensor_id`, `telemetry` (CNPJ) + `telemetry_label`, `company`, `vehicle_type`, `installation_date`, `installer`, `installation_data`, `software_version`, `need_update`, `device_need_update`, `is_operating`, `camera_service`, `nickname`, `id` (= ESP ID; era UUID) | `vehicle_plate=` |
| `devices/<MIC…>/` | hardware + instalação: `series_num`, `sensor_id`, `company`, `plate`, `vehicle_type`, `telemetry` (módulo) , `telemetry_company` + `telemetry_company_label`, `installer`, `installation_date`, `installation_data`, `is_operating`, `need_update`, `software_version`, `default_settings` (sem `chip`/`suntech` desde 24/09/2026) | detalhe por id |
| `sensors/<ETL…>/` | `timestamp` (data da calibração corrente), `solution`, `analog`, `mgl`, `current_calibration` | `id=` |
| `calibrations/` | pontos de calibração (`sensor_id`, `analog`, `mgl`, `num`, `solution`) | (filtro por sensor não funciona) |
| `telemetries/<id>/` (era `suntechs/`, 404 desde 24/09/2026) | módulo rastreador: `is_connected`, `is_ignition_on`, `is_relay_on`, `has_to_block`, `has_to_unblock`, `last_stt`, `ip`, `port`, `chip`, `lat`/`lon`, `model`, `vehicle` — **as flags podem estar defasadas** (ex.: RJK1D03 com `is_connected=False` enviando logs em 23/09/2026): confirme pelos logs recentes. O id do módulo está em `devices/<MIC>/.telemetry` (nulo na MiX) | detalhe por id, `id=` (`?vehicle=` é ignorado; `?device=` devolve vazio) |
| `logs/` | `event`, `etilometer` (ESP ID), `vehicle`, `company_label`, `vehicle_type`, `timestamp` (chegada no servidor, UTC), `created_at` (relógio do aparelho/rastreador), `lat`/`lon` | `vehicle=` (várias por vírgula), `event=` (substring, vírgula), `start=`/`end=` (`YYYY-MM-DD HH:MM:SS`), `telemetry=` |
| `logs/dash-data/`, `logs/alert-events/`, `logs/video/?event=&plate=&tmstp=` | agregados, alertas, link de vídeo (câmera integrada) | idem |
| `anomalies/` | alertas do Scanner: `vehicle`, `company`, `category`, `desc`, `solved` | `vehicle=`, `solved=` |
| `firmwares/` | catálogo de versões (`version`, `release_date`, `desc`) — pode estar atrás do binário do `/update` | |
| `companies/` | transportadoras **e** telemetrias (`type`, `label`, `value`) | (o `?type=` não filtra — filtre no cliente) |

Armadilhas do servidor (detalhe em `server_reference.md`):
- `Device.software_version` só muda por **check-update via Wi-Fi**: `1.0.0` = nunca reportou; pode estar
  defasado. A versão real está na tela ID do aparelho (ou `Tester … firmware`).
- `deleted=True` **não apaga nada** (nenhuma listagem filtra). Remover = `DELETE` de verdade.
- Escritas pela ORM têm de usar `.save()` (signals de sincronização); nunca `QuerySet.update()`.
- Até 24/09/2026 logs de etilômetro inativo/órfão não apareciam (join com `is_active=True`); hoje a API devolve
  todos, e log sem aparelho vinculado vem com `vehicle` vazio.
- Logs MiX vêm do serviço `mix` do servidor (parado de 24/09 a 07/10/2026, sem logs MiX no intervalo): ver `server_reference.md`.
- `logs/` não expõe `id`; `timestamp` é a hora de chegada, não a do evento. Na MiX os eventos chegam em lote.
- `anomalies/` não filtra por empresa e não entra no sync dos clientes.

## 5. Integração de câmeras (resumo)

Parceiros de videomonitoramento recebem ocorrências publicadas pelo servidor (mínimo: `ETEV01`
desbloqueado, `ETEV02` bloqueado, `ETEV16` "etilômetro assoprado") com janela de vídeo ±1 min; o
servidor recupera o link do vídeo por consulta (placa normalizada, rótulo, horário — **fuso horário** é a
causa nº 1 de vídeo não encontrado). Cliente consome em `GET /api/v2/logs/video/`. `Etilometro.camera_service`
indica o provedor (ex.: `movieit`; hoje no `Device`). No aparelho, `camera` (s) é só a espera na tela "Aguardando Câmera".
