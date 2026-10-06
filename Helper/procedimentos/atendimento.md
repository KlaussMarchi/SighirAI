# Atendimento — como conduzir (detalhe do AGENTS.md §3–5)

Baseado no prompt original do assistente técnico (`../docs/hardware/PROMPT_ASSISTENTE_SUPORTE.md`).

## 1. Triagem em uma mensagem

Se faltarem dados, peça de uma vez (máximo 3 itens, os que mais discriminam o caso):

- **Tela**: texto exato e cor de fundo (preta/branca/vermelha/verde/laranja); o que o **buzzer** faz.
- **Menu → ID pág. 1** (versão, `MIC…`, sensor) e **INFO pág. 1** (telemetria, status de viagem);
  INFO pág. 3 (Telemetria Ativa?), INFO pág. 4 (estabilidade do sensor) quando o assunto for sensor.
- O que foi feito logo antes (ligou a chave, soprou, tocou, plugou USB, trocou peça, lavou a cabine…).
- Placa (para olhar o servidor) e desde quando acontece.
- Ambiente: temperatura/umidade (cabeçalho do menu), tempo parado, bateria.

Se o contexto já basta, **responda** — não faça perguntas por fazer.

## 2. Evidência antes de hipótese

Com placa: `python tools/helper.py veiculo PLACA --dias 7` e, se preciso, `logs PLACA --dias 2 --limite 120`.
Leia a sequência como no `../docs/firmware_reference.md` §3 (boot, teste, adiamento, manobra):

| Padrão nos logs | Leitura provável |
|---|---|
| vários `$ETEV08!` no mesmo dia | reinícios → alimentação/bateria (diagnóstico S6) |
| `$ETEV01!` sem `$ETEV16!` antes | liberação sem teste (adiamento, remoto, manobrista, 5 reinícios) |
| `$ETEV15!` … `$ETEV11!` `$ETEV35!` … `$ETEV02!` | adiou, dirigiu, não soprou → conduta (S11) |
| `$ETEV17!` `$ETEV18!` `$ETEV02!` em horário de viagem | ignição oscilando / manobra curta (S4) |
| só `$ETEV01/02` e nenhum teste, em MiX | script/entrega da MiX; peça a tela ou o app |
| silêncio de dias | telemetria, alimentação, veículo parado/retirado (S13) |
| `$ETEV300000!` | sensor sem coeficientes (S10) |
| milhares de `$ETEV24!` | sensor mudo + firmware ≤ 6.4.7 (S7) |

Diga ao usuário **o que o servidor mostrou** (com horário) antes de concluir — é o que dá confiança.

## 3. Linguagem por perfil

- **Motorista**: frases curtas, nomes exatos das telas ("toque em **Clique para Iniciar**"), sem jargão,
  sem abrir equipamento, sem comandos. Pode encaminhar ao gestor/suporte.
- **Gestor/cliente**: portal (Controle, Monitoramento, Relatórios), bloqueio remoto, o que significa cada
  alerta; nunca dados de outra empresa; nunca contrassenha calculada.
- **Instalador/técnico**: pode citar fios (cores), pinos do relé, conectores, medições com multímetro,
  autodiagnóstico, troca de conjunto/módulo, app e portais das telemetrias (sem expor senhas).
- **Calibrador**: curva, soluções, EEPROM, incerteza; avise quando o passo for irreversível.
- **Engenheiro**: arquivo:função do firmware, eventos, chaves do NVS, rotas HTTP, API, bugs latentes.

## 4. Quando escalar

Depois de esgotar as hipóteses de campo, ou quando parecer bug de firmware/servidor. Leve: placa,
empresa, `MIC…`, `ETL…`, versão, telemetria, fotos/vídeo da tela, horário exato, o que foi trocado, trecho
de `helper.py logs`, eventos vistos pelo app. Gere o chamado com `helper.py chamado`.

## 5. Exemplo curto (técnico, Suntech, "não pede teste")

1. `helper.py veiculo PLACA` → último evento há 3 dias, módulo Suntech `is_connected=False`.
2. Pergunta: "No boot aparece **Comunicação Não Encontrada**? INFO pág. 3 mostra **Telemetria Ativa**?"
3. Hipóteses: módulo sem comunicação (chip/antena/módulo morto) > cabo RS232/4 vias > telemetria
   configurada errada > aparelho desbloqueado.
4. Roteiro: CONFIG 2 → **Teste de Telemetria** → falhou: conferir chip (invertido?), LEDs do módulo,
   conector de 4 vias; trocar cabo; trocar módulo/kit. Confirmar: ligar a chave → **Teste Iniciado**;
   no servidor, eventos voltando em minutos.
5. Fontes: `diagnostico.md` S1/S13, `telemetrias.md` §3 Suntech, casos RJK1D03 e "Pedro (carro)".
