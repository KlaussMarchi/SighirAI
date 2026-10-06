# O sistema Sighir em uma página

> Base comum das três IAs. Fontes: firmware v6.4.8 (`hardware/Main/`, `hardware/FIRMWARE_ETILOMETRO.md`),
> PPTC 0001-01 (`Notion/main.pdf`), manuais de instalação e do portal/app (`Notion/`), API de produção.
> Detalhe de cada assunto nos documentos citados em cada seção.

## 1. O produto

**Etilômetro veicular DAD01** (bafômetro de ignição): impede a partida do veículo até o motorista soprar
e o teste dar negativo. É formado por:

| Peça | O que é | Onde fica |
|---|---|---|
| **Placa exposta** | o "etilômetro" que o motorista vê: ESP32 (placa WT32-SC01, tela touch 3,5"), sensor de álcool, sensor de pressão (sopro), DHT22 (temperatura/umidade), buzzer | no painel, ao alcance do motorista |
| **Placa embutida** | caixa preta escondida no painel: reguladores de tensão, conector RS232 (DB9) para a telemetria, conector 6 vias (alimentação/sinais) | atrás do painel, fixa em superfície plana |
| **Cabo espiral** | 8 vias, liga exposta ↔ embutida | por dentro do painel |
| **Cabo de força / chicote** | 6 vias: VCC, GND, pós-chave, entrada 1/ALT, relé | bateria do veículo (12/24 V), fusível no VCC |
| **Cabo RS232** | DB9 (embutida) ↔ módulo de telemetria (microfit) | |
| **Módulo de telemetria (rastreador)** | MiX, Suntech (ST8300) ou Entrack — **quem de fato bloqueia** o veículo e manda os eventos para a nuvem | painel |
| **Relé de bloqueio** | corta o sinal de ignição/partida quando comandado | no chicote |
| **Sensor de álcool** | semicondutor com EEPROM própria (ID `ETL…`, coeficientes de calibração, contador de sopros); trocável | dentro da exposta (acesso pela tampa traseira) |

Especificação: alimentação 10,5–40 V (12/24 V), operação 0–50 °C, RS232 a **115200 bps**, Wi-Fi 2,4 GHz,
Bluetooth Classic 4.2, precisão ~0,03 mg/L. Vida do sensor: **2500 sopros** (firmware) e calibração válida
por **1 ano** (PPTC 0001-02 §6.1). Documentos antigos citam "5000 sopros ou 2 anos" — o firmware atual usa 2500.

## 2. Identidades

| Identificador | Formato | Onde aparece |
|---|---|---|
| `esp_id` | `MIC` + 12 dígitos + 4 dígitos de verificação (19 chars), gerado no 1º boot | tela ID, Wi-Fi `SIGHIR - MICxxxx`, servidor (`Device.id`) |
| `sensor_id` | `ETL` + 16 dígitos (19 chars), gravado na EEPROM do sensor | tela ID, evento `$ETEV09<id>!`, servidor (`Sensor.id`) |
| Nº de série | 5 dígitos (`00010`) — etiqueta colada no aparelho | `Device.series_num` |
| ID do módulo | ID Suntech/Entrack (ex.: `1700023879`) | `Suntech.id`, tela ID pág. 2 |
| Placa | placa do veículo | `Etilometro.vehicle_plate` (a "instalação") |

`admin_sighir` no lugar do `esp_id` = configuração sobrescrita (fluxo de atualização por Wi-Fi); o
cadastro exige o ID nativo `MIC…` (o Tester faz `erase` para regenerar).

## 3. Como a informação circula

```
motorista ──sopro──▶ placa exposta (ESP32) ──espiral──▶ placa embutida ──RS232 115200──▶ rastreador
                                                                                        │ (MiX / Suntech / Entrack)
                                        eventos $ETEVnn!  ◀── ignição / comandos ───────┘
                                                                                        ▼
                                                     nuvem da telemetria ──integração──▶ servidor Sighir
                                                                                        (Django, sighir.com:8000/api/v2)
                                                                                        ▼
                                                              Portal Web (sighir.com) · App Sighir Monitor · IAs
```

- O etilômetro **não tem internet em operação**: todo evento sai pela serial para o rastreador, que
  repassa. Wi-Fi só é usado em bancada/instalação/atualização (`wifi = false` de fábrica).
- A **ignição chega pelo rastreador** (comando serial na MiX, pacote `STT` na Suntech, `+QACC` na Entrack).
  Sem rastreador comunicando, o aparelho **não sabe que o veículo ligou** → não pede teste.
- O **bloqueio é executado pelo rastreador** (relé dele): o etilômetro manda a ordem
  (`$ETBL010000!`/`$ETBL020000!`, `CMD;<id>;04;0x` na Suntech, `AT+GPIOVALUE` na Entrack). O relé
  interno da exposta (GPIO 2) fica em LOW nos dois casos — não é ele que bloqueia.
- Cada telemetria repassa **só parte** dos eventos (a MiX nunca repassou resultado de teste) — ver
  `telemetrias.md` §5.

## 4. O ciclo normal de uso

1. **Ignição liga** com o veículo bloqueado → teste solicitado (tela "Teste Iniciado").
2. 5 s para **adiamento de emergência** (toque) → senão logos → **aguardando câmera** → **calibrando
   sensor** (estabilização do zero) → "Clique para Iniciar" → **"Assopre"** (3 s contínuos, ≥ 1,8 s) →
   **"Analisando"** (~23 s) → resultado em mg/L.
3. **Negativo** → tela verde "Veículo Desbloqueado", viagem começa; **testes randômicos** podem ser
   pedidos durante a viagem.
4. **Positivo** → tela vermelha "Álcool Detectado", veículo bloqueado, opções: contrassenha /
   realizar outro teste / desligar display.
5. **Ignição desliga** → **tempo de manobra** (`maneuver_time`, padrão 5 min): religar dentro do prazo não
   exige teste; esgotou → "Tempo Esgotado" + bloqueio.

Telas, sons e menus: `operacao_telas.md`. Eventos em cada etapa: `firmware_reference.md` §3 e PPTC §2.4.

## 5. Quem usa o quê

| Perfil | Usa | Pode fazer |
|---|---|---|
| Motorista | tela do etilômetro, app (modo motorista) | testar, adiar, pedir contrassenha ao supervisor |
| Gestor de frota (cliente) | Portal Web sighir.com | ver eventos, bloquear/desbloquear remoto, relatórios, certificados de calibração |
| Instalador | App Sighir Monitor (perfil instalador), manuais de instalação | instalar, configurar pelo Wi-Fi do aparelho, checklist com fotos |
| Técnico / suporte N1-N2 | app (perfil técnico), portal, portais das telemetrias, Tester | diagnóstico, troca de conjunto/sensor, atualização |
| Calibrador / metrologia | software desktop de calibração, bancada de gás | curva `a·b^(cx+d)`, certificado, gravação na EEPROM |
| Engenharia | firmware, servidor, IAs | correções, integrações, análise de logs |

## 6. As três IAs deste repositório

| Pasta | Papel | Fala com |
|---|---|---|
| `Tester/` | bancada: conecta no etilômetro pelo USB, testa, configura, atualiza firmware, cadastra no servidor | serial USB + API |
| `Server/` | auditoria da frota: varre os logs e mantém a tabela `anomalies` | API (escreve só em `anomalies`) |
| `Helper/` | suporte técnico: diagnostica problemas de campo (portal, elétrica, firmware, telemetria) | base `docs/` + API |

Todas leem esta pasta `docs/`. Mapa completo: `INDEX.md`. Busca: `python docs/tools/kb.py busca <termos>`.

## 7. Glossário rápido

- **Pós-chave**: sinal que fica energizado com a chave no 1º estágio (ignição). Fio verde no chicote.
- **Tempo de manobra**: tolerância após desligar para religar sem teste (`maneuver_time`).
- **Adiamento**: o motorista adia o teste (até `max_postpone` vezes, `postpone_time` min liberado).
- **Teste randômico**: teste pedido durante a viagem (`enable_random`, `number_of_tests`, `rand_*`).
- **Modo manobrista (valet)**: uso administrativo, partida sem teste (botão no menu se `valet` habilitado).
- **Contrassenha**: liberação após positivo — a tela mostra um desafio e o supervisor informa a resposta
  (o app Sighir Monitor gera). Procedimento administrativo, não é para o motorista.
- **Tempo de câmera**: espera a câmera do veículo ficar pronta antes do teste (`camera`, s).
- **Purga / aquecimento necessário**: após um positivo o sensor precisa de 2–5 min para limpar.
- **Conjunto**: exposta + embutida + espiral (o que se troca em campo para isolar defeito).
