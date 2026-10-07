# Troubleshooting de campo (checklists da equipe)

> **Gerado automaticamente** por `tools/kb.py atualizar` em 07/10/2026 09:33 a partir do Notion (Sighir Enterprise → Suporte → Troubleshooting, `Notion/Sighir Enterprise 24579b90eb738059bdcfd009e0df1825.md`).
> Não edite aqui: edite no Notion e sincronize ("sincronizar os documentos" → `sincronizar.md`).
> A versão por sintoma — causas, evidências no servidor e no firmware — está em `diagnostico.md`; os menus citados estão em `operacao_telas.md` §7 ("Configurações, página 2, Teste Serial" = CONFIG 2 → **Teste de Telemetria**).

## Problemas de Requisição de Teste

### MIX

1. Na tela de menu do Etilômetro, Verificar na tela de INFO → Telemetria MIX 2.0
2. Configurações, página 2, clicar em Teste Serial (com chave ligada) →Verificar “Estado Funciona”. Se falhar, a telemetria não está em comunicação com o etilômetro.
3. Verificar se o pen drive da MIX está plugado e com motorista identificado no portal
4. Ver no portal se os últimos logs aparecem e veriificar consistência, se a comunicação parou, encontrar o momento em que isso ocorreu pelos LOGS
5. Conferir se script do módulo MIX está correto pelo MIX Tech Tool e Rafael
6. Verificar com Rafael para enviar a configuração de “viagem iniciar só depois que identificar o motorista”
7. Verificar se o etilômetro está na versão mais atualizada
8. Trocar o conjunto e ver se o problema foi resolvido
9. Trocar o módulo e ver se o problema foi resolvido

### Suntech

1. Na tela de menu do Etilômetro, Verificar na tela de INFO → Telemetria Suntech
2. Configurações, página 2, clicar em Teste Serial (com chave ligada) →Verificar “Estado Funciona” mostrando o ID Suntech. Se falhar, a telemetria não está em comunicação com o etilômetro.
3. Ver no portal se os últimos logs aparecem e veriificar consistência, se a comunicação parou, encontrar o momento em que isso ocorreu pelos LOGS
4. Verificar se o etilômetro está na versão mais atualizada
5. No caso de comunicação funcional, verificar parte elétrica dos cabos de VCC, GND e IGNIÇÃO (mal contato, tensão que chega ao fio após girar a chave, etc)
6. Teste de fio rompido/mal contato
pode ser esse fio azul do cabo suntech que é conectado ao derivador, aí teria que apertar ele mais, tirar e colocar, caso aconteça de novo, pra deixar registrado
![WhatsApp_Image_2026-05-19_at_09.14.29.jpeg](Notion/WhatsApp_Image_2026-05-19_at_09.14.29.jpeg)
7. Trocar o conjunto e ver se o problema foi resolvido

## Problemas de Atualização

1. Verifique no MENU, Configurações (primeira página) se o etilômetro está com o ícone de WiFi habilitado (setinha verde ligada)
2. Verificar o icone de WiFi no canto superior direito da tela de menu do etilômetro, deve estar wifi sem estar riscado
3. Conferir se o etilômetro está habilitado para atualização (Klauss ou Jean)
4. Conferir na tela de INFO, se o campo “ssid da rede” e “senha da rede” estão corretos com um WiFi disponível no local com conexão com a internet
→ Se não estiver tem que configurar clicando em “ssid da rede” para alterar via teclado
  →  Em versões mais antigas deve-se configurar o ssid e senha pelo aplicativo Sighir, conectando-se ao wifi do etilômetro (Sighir - MIC1123…)
5. Configurações → Página 1 → “Reestabelecer Conexão” e verificar se dessa vez conecta no WiFi, se ainda sim não conectar, tente fazer isso mais duas vezes até desistência
6. Conferir se de fato aquela rede da qual o etilometro tenta se conectar está disponível, fazer um teste por exemplo tentando se conectar nela pelo celular
7. Verificar se o roteador é 2.4 GHz, se não for, vale a pena usar outro roteador ou rotear do celular, por hotspot móvel (e selecionar 2.4 GHz)
8. Configuração, página 2 e reinicio de emergencia, ver se volta
9. Se estiver conectado mas mesmo assim der erro, pedir vídeo do processo

## Problemas de Bloqueio

1. Verificar problemas de Requisição de Teste (acima)

### MIX

1. Conferir se o firmware do etilômetro está atualizado
2. Verificar se o pen drive da MIX está plugado e com motorista identificado no portal
3. (bloqueio inesperado) Verificar se o tipo de veículo é carro ou caminhão e conferir com etilometro na tela de INFO
4. No portal da MIX, enviar para Relay Driver 1 e Relay Driver 2 os comandos de OFF AND RELEASED, esperar comandos chegarem e tentar novamente
5. Conferir se script do módulo MIX está correto pelo MIX Tech Tool e Rafael
6. Verificar com Rafael/Mauro para enviar a configuração de “viagem iniciar só depois que identificar o motorista”
7. Verificar com Rafael/Mauro para enviar a configuração do etilometro atuar no relé 2 ao inves de “immobilizer”
8. Verificar se o desbloqueio pelo portal funciona ou só acontece isso no funcionamento do etilometro (reportar)
9. Verificar conexão elétrica do módulo (bypass inesperado, relé funcional)
10. Trocar o módulo MIX e tentar novamente

### Suntech

1. Configurações, página 2 e “Autodiagnóstico”, Clicar em teste de relé e verificar se o relé atraca (e portanto, veículo desbloqueia) repetidamente
2. Verificar se o tipo do relé de fato bate com a tensão de alimentação (12 ou 24 Volts)
3. verificar fiação elétrica e conexões com o relé GND → VCC → Pino 30 do Relé → pino 87a do relé
4. Trocar o relé
5. Trocar placa embutida e verificar funcionamento
6. Trocar módulo suntech e verificar funcionamento
7. Trocar chicote sighir e testar
8. Último recurso trocar o kit completo

## Problemas de Conexão Aplicativo-Etilômetro

1. Verifique no MENU, Configurações (primeira página) se o etilômetro está com o ícone de WiFi habilitado (setinha verde ligada)
2. Configurações → Página 1 → “Reestabelecer Conexão” e verificar se dessa vez conecta no WiFi, se ainda sim não conectar, tente fazer isso mais duas vezes até desistência

## Reiniciamentos Inesperados

1. Tentar dar partida no caminhão direto (o etilometro desbloqueia o veículo por padrão)
2. Retirar o sensor de alcool do etilometro e esperar alguns minutos, ver se sai da tela de “reiniciamentos inesperados”
  1. Se sair da tela tentar encaixar novamente o sensor
  2. Se ao colocar o mesmo sensor novamente e o problema retornar, trocar o sensor que está defeituoso para um novo
3. Carga na bateria do caminhão (bateria carga → usar chupeta ou controlador de carga para a bateria)
4. Verificar mau contato no conjunto embutido, apertar e reforçar os fios
5. Trocar a embalagem exposta e verificar se solucionou (defeito no etilometro)
6. Trocar a embalagem embutida e verificar se solucionou (problema no kit)
OBS: Atualizar o etilometro para a versão ≥6.0.0, que mitiga este problema

## Problemas de Alcool

1. Verificar se etilômetro está devidamente atualizado
2. Verificar no campo ID, página 2, se data de calibração está devidamente preenchida (se não estiver, o sensor está sem calibração gerada)
3. Trocar o sensor (e reinicar o etilômetro) e ver se comportamento continua → problema no sensor
4. Colocar o mesmo sensor em um etilômetro diferente e ver se comportamento continua → problema no etilômetro e na versão
5. Conferir no aplicativo de calibração se a curva desse sensor faz sentido

## Problemas de Sopro

1. Verificar se o etilômetro está atualizado
2. Configurar facilidade de sopro (tela de info → página 2) por configuração remota ou pelo aplicativo do etilometro (CF:blowProb$0.5!) (0 é mais dificil, 1 é o mais facil)

## Problemas de Comunicação

### Suntech

1. Verificar se o etilômetro está na versão mais atualizada
2. Verificar mal contato nas ligações dos fios de comunicação com o aparelho suntech
3. Verificar e enviar padrão de piscar das duas luzes no módulo suntech, caso ele esteja devidamente energizado
4. Verificar se energização do conjunto está devidamente feita
5. Trocar o kit suntech e verificar se o problema persiste
6. Trocar o o kit do etilômetro e veificar se o problema persiste
7. Teste de fio rompido/mal contato
pode ser esse fio azul do cabo suntech que é conectado ao derivador, aí teria que apertar ele mais, tirar e colocar, caso aconteça de novo, pra deixar registrado
![image.png](Notion/image.png)

### Entrack

### Mix
