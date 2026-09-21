## ⚠️ Troubleshooting

### Problemas de Requisição de Teste

#### MIX
1. Na tela de menu do Etilômetro, verificar na tela de **INFO** → **Telemetria MIX 2.0**
2. **Configurações**, página 2, clicar em **Teste Serial** (com chave ligada) → verificar **“Estado Funciona”**. Se falhar, a telemetria não está em comunicação com o etilômetro.
3. Verificar se o pen drive da MIX está plugado e com motorista identificado no portal
4. Ver no portal se os últimos logs aparecem e verificar consistência; se a comunicação parou, encontrar o momento em que isso ocorreu pelos LOGS
5. Conferir se script do módulo MIX está correto pelo MIX Tech Tool e Rafael
6. Verificar com Rafael para enviar a configuração de **“viagem iniciar só depois que identificar o motorista”**
7. Verificar se o etilômetro está na versão mais atualizada
8. Trocar o conjunto e ver se o problema foi resolvido
9. Trocar o módulo e ver se o problema foi resolvido

#### Suntech
1. Na tela de menu do Etilômetro, verificar na tela de **INFO** → **Telemetria Suntech**
2. **Configurações**, página 2, clicar em **Teste Serial** (com chave ligada) → verificar **“Estado Funciona”** mostrando o **ID Suntech**. Se falhar, a telemetria não está em comunicação com o etilômetro.
3. Ver no portal se os últimos logs aparecem e verificar consistência; se a comunicação parou, encontrar o momento em que isso ocorreu pelos LOGS
4. Verificar se o etilômetro está na versão mais atualizada
5. No caso de comunicação funcional, verificar parte elétrica dos cabos de **VCC, GND e IGNIÇÃO** (mal contato, tensão que chega ao fio após girar a chave, etc.)
6. Teste de fio rompido/mal contato
   - Pode ser esse fio azul do cabo Suntech que é conectado ao derivador; aí teria que apertar ele mais, tirar e colocar. Caso aconteça de novo, deixar registrado.
7. Trocar o conjunto e ver se o problema foi resolvido

---

### Problemas de Atualização
1. Verifique no **MENU**, **Configurações** (primeira página) se o etilômetro está com o ícone de WiFi habilitado (setinha verde ligada)
2. Verificar o ícone de WiFi no canto superior direito da tela de menu do etilômetro (deve estar WiFi sem estar riscado)
3. Conferir se o etilômetro está habilitado para atualização (Klauss ou Jean)
4. Conferir na tela de **INFO** se o campo **“ssid da rede”** e **“senha da rede”** estão corretos com um WiFi disponível no local com conexão com a internet
   - Se não estiver: configurar clicando em **“ssid da rede”** para alterar via teclado
   - Em versões mais antigas: configurar SSID e senha pelo aplicativo Sighir, conectando-se ao WiFi do etilômetro (**Sighir - MIC1123…**)
5. **Configurações → Página 1 → “Reestabelecer Conexão”** e verificar se dessa vez conecta no WiFi; se ainda assim não conectar, tente mais duas vezes até desistir
6. Conferir se a rede na qual o etilômetro tenta se conectar está disponível (testar, por exemplo, conectando nela pelo celular)
7. Verificar se o roteador é **2.4 GHz**; se não for, usar outro roteador ou rotear do celular por hotspot (e selecionar 2.4 GHz)
8. Se estiver conectado mas mesmo assim der erro, pedir vídeo do processo

---

### Problemas de Bloqueio
1. Verificar problemas de **Requisição de Teste** (acima)

#### MIX
1. Verificar se o pen drive da MIX está plugado e com motorista identificado no portal
2. No portal da MIX, enviar para **Relay Driver 1** e **Relay Driver 2** os comandos **OFF AND RELEASED**, esperar os comandos chegarem e tentar novamente
3. Verificar com Rafael para enviar a configuração de **“viagem iniciar só depois que identificar o motorista”**
4. Verificar se o desbloqueio pelo portal funciona ou só acontece isso no funcionamento do etilômetro (reportar)
5. Conferir se script do módulo MIX está correto pelo MIX Tech Tool e Rafael
6. Verificar conexão elétrica do módulo (bypass inesperado, relé funcional)
7. Trocar o módulo MIX e tentar novamente
8. Conferir se o firmware do etilômetro está atualizado

#### Suntech
1. **Configurações**, página 2 e **“Autodiagnóstico”**: clicar em teste de relé e verificar se o relé atraca (e portanto, o veículo desbloqueia) repetidamente
2. Caso contrário, trocar placa embutida e verificar funcionamento
3. Caso contrário, trocar módulo Suntech e verificar funcionamento
4. Caso contrário, trocar kit
5. Se nada funcionar, verificar fiação elétrica e conexões com o relé:
   - **GND → VCC → Pino 30 do relé → pino 87a do relé**

---

### Problemas de Conexão Aplicativo–Etilômetro
1. Verifique no **MENU**, **Configurações** (primeira página) se o etilômetro está com o ícone de WiFi habilitado (setinha verde ligada)
2. **Configurações → Página 1 → “Reestabelecer Conexão”** e verificar se dessa vez conecta no WiFi; se ainda assim não conectar, tente mais duas vezes até desistir
