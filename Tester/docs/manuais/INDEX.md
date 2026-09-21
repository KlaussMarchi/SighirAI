# Índice dos Manuais (PDFs) — quando consultar cada um

> Resumo extraído dos PDFs desta pasta. Use este índice para responder dúvidas de
> instalação/calibração/homologação **sem reabrir o PDF**; abra o PDF (via `pdftotext`
> ou leitura direta) só para detalhes finos/figuras. Especificações comuns a todos:
> alimentação **12–40 V** (bateria 12/24 V), op. **0–50 °C**, **RS232** (placa embutida ↔ telemetria),
> Bluetooth Classic v4.2, WiFi 2.4 GHz, precisão na casa de **0,03 mg/L**.

| PDF | Assunto | Consulte quando… |
|---|---|---|
| `Procedimento_de_Instalação_Suntech.pdf` | Instalação física c/ telemetria **Suntech** | dúvida de cabeamento/relé/validação Suntech |
| `Procedimento_de_Instalação_MIX.pdf` | Instalação física c/ **MIX Telematics** | idem MIX (pen-drive de ativação, entrada S1) |
| `Procedimento_de_Instalação_Entrack.pdf` | Instalação física c/ **Entrack** | idem Entrack (ignição por acelerômetro) |
| `Procedimento_de_Calibraýýo___Sighir.pdf` | Calibração de sensor de álcool (laboratório) | dúvida sobre curva/coeficientes/validade do sensor |
| `Sighir_Anatel.pdf` | Manual técnico p/ **homologação ANATEL** | compliance/documentação regulatória (referência) |
| `Relatorio_Sensores.xlsx` | Planilha de relatório de sensores | dados/histórico de sensores |

---

## Fluxo de instalação (comum a Suntech / MIX / Entrack)

Conjunto entregue ao instalador: **placa exposta** (etilômetro) + **placa embutida** + **cabo RS232** (DB9) + **conector 6 vias** (alimentação) + **módulo de telemetria + chicote** (c/ relé).

1. Se houver proteção antiviolação (ex.: **t4s**), pedir ao gestor para desativar temporariamente e abrir o painel.
2. **Desligar a chave geral** do veículo.
3. Conectar o **RS232** entre o **módulo de telemetria** e a **placa embutida** (DB9 c/ 2 parafusos).
4. Ligar a **alimentação** (conector 6 vias) → bateria 12/24 V (VCC vermelho, GND marrom).
5. Conectar **placa exposta ↔ embutida** pelo **cabo espiral (conector 8 vias)**.
6. Religar a chave geral e **confirmar que o display acende**.

### Diferenças por telemetria
- **Suntech**: RS232 conector **4 vias** no módulo Suntech; relé no chicote Suntech ligado ao **sinal de ignição** (cortar o fio de ignição, pontas nos terminais do relé). Validade do sensor: **5000 sopros / 2 anos**.
- **MIX**: RS232 conector **6 vias** na entrada **S1** do módulo MIX; **fio vermelho=VCC** no + da bateria, **marrom=GND** no −; exige **pen-drive azul de ativação** plugado no painel; ativação via **script da MIX** (instalador contata funcionário da MIX); veículo precisa do **pen-drive de identificação** para ligar. O módulo MIX já deve ter bloqueio funcional.
- **Entrack**: RS232 conector **4 vias** no módulo Entrack; relé no chicote ligado à ignição (igual Suntech). No firmware, a ignição é detectada por **acelerômetro** (`+QACC:high/low`).

### Validação do funcionamento (todas as telemetrias)
1. Girar a chave para o 1º estágio (pós-chave). 2. O etilômetro deve **solicitar o teste** ao motorista.
3. Realizar o teste → tela **verde "veículo liberado"** → veículo desbloqueado. 4. Ligar e desligar → aparece **"tempo de manobra"**.
5. Decorrido o tempo → tela **vermelha "veículo bloqueado"**. 6. Confirmar bloqueio efetivo e nova solicitação de teste.

> Mapeamento com o firmware: "solicitar teste" = `test.start` (ignição ON c/ veículo bloqueado);
> "veículo liberado" = `$ETEV29!`→`$ETEV01!`; "veículo bloqueado" = `$ETEV02!`. Veja `docs/firmware_reference.md`.
> **O etilômetro não bloqueia o veículo diretamente** — só envia o comando à telemetria, que aciona o relé.
> Se o relé **não atraca** num teste alcoólico → problema nas **ligações do relé** (ver `docs/troubleshooting.md`).

## Calibração (resumo)
Feita em **laboratório**, com o sensor **já soldado no conjunto final** (incorpora parasitas de hardware/aerodinâmica).
Cilindros de gás certificados (ex.: **0,00 / 0,15 / 0,30 mg/L**). Ciclo por patamar: **purga** (referência 0 mg/L) →
**injeção** controlada → **acomodação + registro** de janela de leituras → **indexação** (ID do sensor + timestamp).
Modelagem: filtro estatístico de anomalias + **regressão por mínimos quadrados** → curva `analyze(x)=a·b^(c·x+d)`
(coeficientes `c1..c4`/`zero` gravados na EEPROM do cartucho). Limiar de detecção de álcool: **mgl > 0,020**.
