#ifndef LANGUAGES_H
#define LANGUAGES_H
extern const char *getLang();

typedef struct Language {
    const char *PT;
    const char *EN;
    const char *ES;

    Language(const char *pt, const char *en, const char *es)
        : PT(pt), EN(en), ES(es) {}

    const char *get() const {
        const char *currentLang = getLang();

        if(currentLang == nullptr)
            return PT;

        if(strcmp(currentLang, "EN") == 0)
            return EN;

        if(strcmp(currentLang, "ES") == 0)
            return ES;

        return PT;
    }
} Lang;

struct Languages {
    Lang startVehicle = Lang(
        "Ligue o Veículo",
        "Start Vehicle",
        "Encienda el Auto"
    );

    Lang alcoholDetected = Lang(
        "Álcool Detectado",
        "Alcohol Detected",
        "Alcohol Detectad"
    );

    Lang yes = Lang(
        "Sim",
        "Yes",
        "Si "
    );

    Lang totalBlows = Lang(
        "Total de Sopros: ",
        "Total Blows: ",
        "Soplos Totales:"
    );

    Lang configuringFor = Lang(
        "Configurando para ",
        "Configuring for ",
        "Configurando pa "
    );

    Lang unlockVehicle = Lang(
        "Desbloquear Veículo",
        "Unlock Vehicle ",
        "Desbloquear Auto"
    );

    Lang devFamily = Lang(
        "Família de Desenvolvimento",
        "Development Family",
        "Familia de Desarr."
    );

    Lang severeTemp = Lang(
        "Temperatura Grave",
        "Severe Temperat.",
        "Temperat. Severa"
    );

    Lang valetEnabled = Lang(
        "Modo Manobrista\r\nHabilitado",
        "Valet Mode\r\nEnabled",
        "Modo Valet\r\nActivado"
    );

    Lang firmwareUpdate = Lang(
        "Atualização de Firmware",
        "Firmware Updating",
        "Actualizacion Fir"
    );

    Lang checkConnection = Lang(
        "Verifique o encaixe",
        "Check Connection ",
        "Revise Conexiones"
    );

    Lang configError = Lang(
        "Erro ao Configurar",
        "Configuring Error",
        "Error al Configur"
    );

    Lang commNotFound = Lang(
        "Comunicação Não\r\nEncontrada",
        "Communication Not\r\nFound In Device",
        "Comunicacion No\r\nEncontrada Aqui"
    );

    Lang randomTest = Lang(
        "Teste Randômico",
        "Randomizer Test",
        "Prueba Aleatoria"
    );

    Lang tapToStart = Lang(
        "Toque para Iniciar",
        "Tap here to Start",
        "Toque para Iniciar"
    );

    Lang checkingComm = Lang(
        "Verificando Comunicação",
        "Checking Communic.",
        "Verificando Comun."
    );

    Lang checkingAlcohol = Lang(
        "Verificando Sensor\r\nde Álcool",
        "Checking Alcohol\r\nSensor Device",
        "Verificando Sensor\r\nde Alcohol OK"
    );

    Lang sensorChangeReminder = Lang(
        "Lembrete de Troca\r\nde Sensor",
        "Sensor Replacement\r\nReminder Notice",
        "Recordatorio para\r\nCambiar Sensor"
    );

    Lang sensorNoEeprom = Lang(
        "SENSOR\r\nSEM EEPROM",
        "SENSOR\r\nNO EEPROM",
        "SENSOR\r\nSIN EEPROM"
    );

    Lang invalidServerRes = Lang(
        "Resposta Inválida\r\ndo Servidor",
        "Invalid Response\r\nFrom The Server",
        "Respuesta Invalida\r\nDesde Servidor"
    );

    Lang startingIn = Lang(
        "iniciando em: ",
        "starting in: ",
        "iniciando en: "
    );

    Lang unauthorizedDriver = Lang(
        "MOTORISTA\r\nNÃO AUTORIZADO",
        "DRIVER IS\r\nUNAUTHORIZED",
        "CONDUCTOR\r\nNO AUTORIZADO"
    );

    Lang factorySettings = Lang(
        "Configurações de Fábrica",
        "Factory Settings",
        "Ajustes de Fabr."
    );

    Lang turnOnIgnition = Lang(
        "Ligue o Pós Chave",
        "Turn On Ignition",
        "Encienda Ignicion"
    );

    Lang connectingNetwork = Lang(
        "Conectando à Rede",
        "Connecting to Net",
        "Conectando a Red "
    );

    Lang defectiveSensor = Lang(
        "Sensor Defeituoso",
        "Defective Sensor",
        "Sensor Defectuoso"
    );

    Lang temperature = Lang(
        "temperatura: ",
        "temperature: ",
        "temperatura: "
    );

    Lang recalibratingSensor = Lang(
        "Recalibrando Sensor",
        "Recalibrating Sens",
        "Recalibrando Sens"
    );

    Lang typeWord = Lang(
        "Digite",
        "Type  ",
        "Escrib"
    );

    Lang sensorNoComm = Lang(
        "Sensor Sem\r\nComunicação",
        "Sensor Without\r\nCommunication",
        "Sensor Sin\r\nComunicacion"
    );

    Lang checkingTemp = Lang(
        "Verificando Sensor\r\nde Temperatura",
        "Checking Temperat.\r\nSensor Device",
        "Verificando Sensor\r\nde Temperatura"
    );

    Lang emergencyPostpone = Lang(
        "Adiamento de Emergência",
        "Emergency Postpone",
        "Aplazo Emergencia"
    );

    Lang restartingCaps = Lang(
        "REINCIANDO",
        "RESTARTING",
        "REINICIANDO"
    );

    Lang testStarted = Lang(
        "Teste Iniciado",
        "Test Started",
        "Prueba Iniciada"
    );

    Lang no = Lang(
        "Não",
        "No ",
        "No "
    );

    Lang sensorExpired = Lang(
        "Sensor Vencido\r\nTroque o Sensor",
        "Sensor Expired\r\nReplace Sensor",
        "Sensor Vencido\r\nCambie Sensor"
    );

    Lang maneuverTime = Lang(
        "Tempo de Manobra",
        "Maneuvering Time",
        "Tiempo Maniobras"
    );

    Lang maintenanceReq = Lang(
        "Manutenção necessária",
        "Maintenance Required",
        "Mantenimiento Req"
    );

    Lang noConfigNeeded = Lang(
        "sem necessidade de configuração",
        "no configuration\r\nis required here",
        "sin necesidad de\r\nconfiguraciones"
    );

    Lang clickToStart = Lang(
        "Clique para Iniciar",
        "Click To Start ",
        "Click Para Iniciar"
    );

    Lang postponingTest = Lang(
        "ADIANDO TESTE",
        "POSTPONING TEST",
        "APLAZANDO PRUEBA"
    );

    Lang disableValet = Lang(
        "Desativar Manobrista",
        "Disable Valet Mode",
        "Desactivar Valet "
    );

    Lang analyzing = Lang(
        "Analisando",
        "Analyzing",
        "Analizando"
    );

    Lang connected = Lang(
        "Conectado",
        "Connected",
        "Conectado"
    );

    Lang waitGreenScreen = Lang(
        "Aguarde a Tela Verde\r\nPara Liberação",
        "Wait Green Screen\r\nFor Authorization",
        "Aguarde Pantalla\r\nVerde para Paso"
    );

    Lang highTemp = Lang(
        "Temperatura Alta",
        "High Temperature",
        "Temperatura Alta"
    );

    Lang completed = Lang(
        "Concluído",
        "Completed",
        "Concluido"
    );

    Lang remoteConfig = Lang(
        "Configuração Remota",
        "Remote Configurat",
        "Configuracion Rem"
    );

    Lang ensureInternet = Lang(
        "certifique-se de estar\r\nconectado à internet",
        "please ensure you\r\nare online now ",
        "asegurese de estar\r\nconectado a red "
    );

    Lang vehicleLocked = Lang(
        "Veículo Bloqueado",
        "Vehicle Locked ",
        "Vehiculo Bloqueado"
    );

    Lang suntechConfigured = Lang(
        "Suntech Configurado",
        "Suntech Configured",
        "Suntech Configurado"
    );

    Lang vehicleOn = Lang(
        "Veículo Ligado",
        "Vehicle Turned On",
        "Vehiculo Encendido"
    );

    Lang vehicleOff = Lang(
        "Veículo Desligado",
        "Vehicle Turned Off",
        "Vehiculo Apagado"
    );

    Lang noServerRes = Lang(
        "sem resposta do servidor",
        "no server respons",
        "sin respuesta serv"
    );

    Lang suntechStarted = Lang(
        "Telemetria Suntech\r\nIniciada",
        "Suntech Telemetry\r\nStarted Now ",
        "Telemetria Suntech\r\nIniciada Ya "
    );

    Lang attentionSensorChange = Lang(
        "ATENÇÃO\r\nTroca de Sensor",
        "ATTENTION\r\nSensor Replace",
        "ATENCION\r\nCambiar Sensor"
    );

    Lang functionalState = Lang(
        "Estado Funcional",
        "Functional State",
        "Estado Funcional"
    );

    Lang updateFailed = Lang(
        "Falha no Update",
        "Update Failed  ",
        "Falla de Update"
    );

    Lang valetDisabled = Lang(
        "Modo Manobrista\r\nDesabilitado",
        "Valet Mode\r\nDisabled ",
        "Modo Valet\r\nDeshabilitado"
    );

    Lang notConnected = Lang(
        "Não Conectado",
        "Not Connected",
        "No Conectado "
    );

    Lang mix2Started = Lang(
        "Telemetria MIX 2.0\r\nIniciada",
        "MIX 2.0 Telemetry\r\nStarted Now ",
        "Telemetria MIX 2.0\r\nIniciada Ya "
    );

    Lang parkVehicle = Lang(
        "Estacione o veiculo",
        "Park the vehicle ",
        "Estacione el auto"
    );

    Lang invalidValue = Lang(
        "Valor Inválido",
        "Invalid Values",
        "Valor Invalido"
    );

    Lang checkingPressure = Lang(
        "Verificando Sensor\r\nde Pressão",
        "Checking Pressure\r\nSensor Device",
        "Verificando Sensor\r\nde Presion OK"
    );

    Lang configuringChannel = Lang(
        "Configurando Canal",
        "Configuring Chann",
        "Configurando Canal"
    );

    Lang entrackConfigured = Lang(
        "Entrack Configurado",
        "Entrack Configured",
        "Entrack Configurado"
    );

    Lang verified = Lang(
        "Verificado",
        "Verified  ",
        "Verificado"
    );

    Lang testFailed = Lang(
        "Falha no Teste",
        "Test is Failed",
        "Falla de Prueba"
    );

    Lang sensorConnected = Lang(
        "Sensor Conectado",
        "Sensor Connected",
        "Sensor Conectado"
    );

    Lang sensorBadContact = Lang(
        "SENSOR\r\nCOM MAU CONTATO",
        "SENSOR\r\nBAD CONNECTION",
        "SENSOR\r\nMAL CONTACTO "
    );

    Lang sensorExpiringAlert = Lang(
        "Alerta de Sensor\r\nVencimento Próximo",
        "Sensor Alert Msg\r\nNear Expiration",
        "Alerta de Sensor\r\nVencimiento Cerca"
    );

    Lang calibratingPressure = Lang(
        "Calibrando\r\nSensor de Pressão",
        "Calibrating The\r\nPressure Sensor",
        "Calibrando El \r\nSensor de Presion"
    );

    Lang invalidKeys = Lang(
        "chaves inválidas",
        "invalid api keys",
        "llaves invalidas"
    );

    Lang updatingDevice = Lang(
        "Atualizando Dispositivo",
        "Updating Devices ",
        "Actualizando Dispos"
    );

    Lang checkingSerial = Lang(
        "Verificando Serial",
        "Checking Serials",
        "Verificando Serial"
    );

    Lang blow = Lang(
        "Assopre",
        "Blow   ",
        "Sople  "
    );

    Lang changingChannel = Lang(
        "Mudando Canal",
        "Changing Channels",
        "Cambiando Canal  "
    );

    Lang enableValet = Lang(
        "Ativar Manobrista",
        "Enable Valet Mode",
        "Activar Manobrist"
    );

    Lang entrackStarted = Lang(
        "Telemetria Entrack\r\nIniciada",
        "Entrack Telemetry\r\nStarted Now ",
        "Telemetria Entrack\r\nIniciada Ya "
    );

    Lang progress0 = Lang(
        "Progresso: 0%",
        "Progress: 0% ",
        "Progreso: 0% "
    );

    Lang clickScreenTo = Lang(
        "clique na tela para",
        "click on screen to",
        "click pantalla para"
    );

    Lang noBlow = Lang(
        "Sem Sopro",
        "No Blow  ",
        "Sin Soplo"
    );

    Lang restarting = Lang(
        "Reiniciando",
        "Restarting ",
        "Reiniciando"
    );

    Lang attention = Lang(
        "ATENÇÃO",
        "ATTENTION",
        "ATENCION "
    );

    Lang turningOffDisplay = Lang(
        "Desligando Display",
        "Turning Off Display",
        "Apagando Pantalla  "
    );

    Lang mix1Started = Lang(
        "Telemetria MIX 1.0\r\nIniciada",
        "MIX 1.0 Telemetry\r\nStarted Now ",
        "Telemetria MIX 1.0\r\nIniciada Ya "
    );

    Lang testPostponed = Lang(
        "Teste Adiado",
        "Test Postponed",
        "Prueba Aplazada"
    );

    Lang ok = Lang(
        "OK",
        "OK",
        "OK"
    );

    Lang sensorAlmostExpired = Lang(
        "Sensor Quase Vencido\r\nTroque o Sensor",
        "Sensor Near Expir.\r\nReplace Sensor ",
        "Sensor Casi Vencid\r\nCambie Sensor "
    );

    Lang timeOut = Lang(
        "Tempo Esgotado",
        "Timeout Occurred",
        "Tiempo Agotado  "
    );

    Lang lastAlcoholTest = Lang(
        "Último Teste com Álcool\r\nAguarde ",
        "Last Test Alcohol\r\nPlease wait for ",
        "Ultima Prueba Alco\r\nAguarde Ahora "
    );

    Lang calibrationFrozen = Lang(
        "Calibração Congelada",
        "Calibration Frozen",
        "Calibracion Congel"
    );

    Lang testingRelay = Lang(
        "Testando Comutação\r\ndo Relé",
        "Testing the Relay\r\nSwitching Mode ",
        "Probando Cambio  \r\nDe Rele Ahora  "
    );

    Lang incorrectPassword = Lang(
        "Senha Incorreta",
        "Wrong Passwords",
        "Clave Incorrect"
    );

    Lang deviceConfigured = Lang(
        "Dispositivo Configurado",
        "Device Configured",
        "Dispos. Configura"
    );

    Lang unexpectedRestarts = Lang(
        "Reiniciamentos Inesperados",
        "Unexpected Restarts",
        "Reinicio Inesperado"
    );

    Lang remainingTime = Lang(
        "Tempo Restante: ",
        "Remaining Time: ",
        "Tiempo Restante: "
    );

    Lang vehicleUnlocked2 = Lang(
        "Veículo Desbloqueado",
        "Vehicle Unlocked  ",
        "Vehiculo Desbloq. "
    );

    Lang restartingDevice = Lang(
        "Reiniciando Dispositivo",
        "Restarting Device",
        "Reiniciando Equipo"
    );

    Lang configParams = Lang(
        "Configurando Parâmetros",
        "Configuring Paramts",
        "Configurando Paramt"
    );

    Lang vehicularBreath = Lang(
        "Etilômetro Veicular",
        "Vehicular Breathalyzer",
        "Alcoholim Vehicular"
    );

    Lang vehicleUnlocked = Lang(
        "Veículo Desloqueado",
        "Vehicle Unlocked",
        "Vehiculo Desbloq."
    );

    Lang firmwareVersion = Lang(
        "Versão de Firmware",
        "Firmware Version",
        "Version Firmware"
    );

    Lang serialNumber = Lang(
        "Número Serial",
        "Serial Number",
        "Numero de Serial"
    );

    Lang sensorId = Lang(
        "ID do Sensor",
        "Sensor ID",
        "ID del Sensor"
    );

    Lang networkSsid = Lang(
        "SSID da Rede",
        "Network SSID",
        "SSID de la Red"
    );

    Lang networkPassword = Lang(
        "Senha da Rede",
        "Network Password",
        "Clave de la Red"
    );

    Lang travelTime = Lang(
        "Tempo em Viagem",
        "Time Traveling",
        "Tiempo en Viaje"
    );

    Lang timeOfTravel = Lang(
        "Tempo de Viagem",
        "Time of Travel",
        "Tiempo de Viaje"
    );

    Lang telemetryId = Lang(
        "ID de Telemetria",
        "Telemetry ID",
        "ID Telemetria"
    );

    Lang calibrationDate = Lang(
        "Data de Calibração",
        "Calibration Date",
        "Fecha Calibracion"
    );

    Lang macAddress = Lang(
        "Mac Address",
        "MAC Address",
        "Direccion MAC"
    );

    Lang vehicleType = Lang(
        "Tipo de Veículo",
        "Vehicle Type",
        "Tipo de Vehiculo"
    );

    Lang companyStr = Lang(
        "Empresa",
        "Company",
        "Empresa"
    );

    Lang travelStatus = Lang(
        "Status de Viagem",
        "Travel Status",
        "Estado del Viaje"
    );

    Lang lastReading = Lang(
        "Última Leitura",
        "Last Reading",
        "Ultima Lectura"
    );

    Lang upTime = Lang(
        "Tempo Ligado",
        "Uptime",
        "Tiempo Activo"
    );

    Lang routerSsid = Lang(
        "SSID do Roteador",
        "Router SSID",
        "SSID del Router"
    );

    Lang cameraTime = Lang(
        "Tempo de Câmera",
        "Camera Time",
        "Tiempo de Camara"
    );

    Lang maxPostpones = Lang(
        "Máximo de Adiamentos",
        "Max Postpones",
        "Maximos Aplazos"
    );

    Lang randomMode = Lang(
        "Modo Randômico",
        "Random Mode",
        "Modo Aleatorio"
    );

    Lang valetModeStr = Lang(
        "Modo Manobrista",
        "Valet Mode",
        "Modo Valet"
    );

    Lang numberOfBlows = Lang(
        "Número de Sopros",
        "Number of Blows",
        "Numero de Soplos"
    );

    Lang blowSmoothing = Lang(
        "Suavização do Sopro",
        "Blow Smoothing",
        "Suavizado Soplo"
    );

    Lang testsPerTravel = Lang(
        "Testes por Viagem",
        "Tests per Travel",
        "Pruebas por Viaje"
    );

    Lang heaterPin = Lang(
        "Pino de Aquecimento",
        "Heater Pin",
        "Pin Calentador"
    );

    Lang sensorCalibration = Lang(
        "Calibração do Sensor",
        "Sensor Calibration",
        "Calibracion Sensor"
    );

    Lang sensorStability = Lang(
        "Estabilidade do Sensor",
        "Sensor Stability",
        "Estabilidad Sensor"
    );

    Lang beepVolume = Lang(
        "Volume do Beep",
        "Beep Volume",
        "Volumen de Beep"
    );

    Lang displayBrightness = Lang(
        "Brilho do Display",
        "Brightness",
        "Brillo de Pantalla"
    );

    Lang exitCaps = Lang(
        "SAIR",
        "EXIT",
        "SALIR"
    );

    Lang wifiStr = Lang(
        "WiFi",
        "WiFi",
        "WiFi"
    );

    Lang reconnect = Lang(
        "Reestabelecer Conexão",
        "Re-establish Conn",
        "Restablecer Conex."
    );

    Lang selfDiagnostic = Lang(
        "Autodiagnóstico",
        "Self-Diagnostic",
        "Autodiagnostico"
    );

    Lang alcoholTest = Lang(
        "Teste Alcoólico",
        "Alcohol Test",
        "Prueba Alcohol"
    );

    Lang telemetryTest = Lang(
        "Teste de Telemetria",
        "Telemetry Test",
        "Prueba Telemetria"
    );

    Lang emergencyRestart = Lang(
        "Reinicio de Emergência",
        "Emergency Restart",
        "Reinicio Emergenc."
    );

    Lang simpleVerification = Lang(
        "Verificação Simples",
        "Simple Check",
        "Verificacion Simpl"
    );

    Lang testTelemetry = Lang(
        "Testar Telemetria",
        "Test Telemetry",
        "Probar Telemetria"
    );

    Lang clickToVerify = Lang(
        "Clique para Verificar",
        "Click to Verify",
        "Clic para Verific."
    );

    Lang pageStr = Lang(
        "Página ",
        "Page ",
        "Pagina "
    );

    Lang lastTest = Lang(
        "Último Teste: ",
        "Last Test: ",
        "Ultima Prueba: "
    );

    Lang inmetro1 = Lang(
        "Portaria INMETRO Nº369",
        "INMETRO Ordinance",
        "Decreto INMETRO "
    );

    Lang foreng = Lang(
        " por ",
        " of ",
        " de "
    );

    Lang inmetro2 = Lang(
        "Este dispositivo não se\n",
        "This device does not\n",
        "Este aparato no\n"
    );

    Lang inmetro3 = Lang(
        "enquadra no âmbito probatório\n",
        "fit into evidentiary\n",
        "es probatorio\n"
    );

    Lang inmetro4 = Lang(
        "de fiscalização ou qualquer\n",
        "law enforcement or\n",
        "legal ni de\n"
    );

    Lang inmetro5 = Lang(
        "outro tipo de punição legal\n\n",
        "any legal punishment\n\n",
        "cualquier punicion\n\n"
    );

    Lang startingInStr = Lang(
        "Iniciando em: ",
        "Starting in: ",
        "Iniciando en: "
    );

    Lang componentsTest = Lang(
        "Teste de Componentes",
        "Components Test",
        "Prueba Componentes"
    );

    Lang relayTest = Lang(
        "Teste de Relé",
        "Relay Test",
        "Prueba de Rele"
    );

    Lang blowTest = Lang(
        "Teste de Sopro",
        "Blow Test",
        "Prueba de Soplo"
    );

    Lang performAnotherTest = Lang(
        "Realizar Outro Teste",
        "Perform Another Test",
        "Realizar Otra Prueba"
    );

    Lang turnOffDisplayStr = Lang(
        "Desligar Display",
        "Turn Off Display",
        "Apagar Pantalla"
    );

    Lang startTest = Lang(
        "Iniciar Teste",
        "Start Test",
        "Iniciar Prueba"
    );

    Lang notStarted = Lang(
        "Não Iniciado",
        "Not Started",
        "No Iniciado"
    );

    Lang waitingCamera = Lang(
        "Aguardando Câmera",
        "Waiting Camera",
        "Esperando Camara"
    );

    Lang postponesSuffix = Lang(
        " Adiamentos",
        " Postpones",
        " Aplazamientos"
    );

    Lang testsSuffix = Lang(
        " testes",
        " tests",
        " pruebas"
    );

    Lang warningBlockTravel = Lang(
        "AVISO: (Reinicialização) Bloqueio\r\nem viagem",
        "WARNING: (Restart) Block\r\nduring travel",
        "AVISO: (Reinicio) Bloqueo\r\nen viaje"
    );

    Lang truck = Lang(
        "Caminhão",
        "Truck",
        "Camion"
    );

    Lang wifiConfig = Lang(
        "Configuração WiFi",
        "WiFi Configuration",
        "Configuracion WiFi"
    );

    Lang wifiChannelConfig = Lang(
        "Configuração de Canal WiFi",
        "WiFi Channel Config",
        "Config. de Canal WiFi"
    );

    Lang askConfigWifi = Lang(
        "Deseja Configurar o WiFi?",
        "Configure WiFi?",
        "Configurar WiFi?"
    );

    Lang askContinue = Lang(
        "Deseja Mesmo Continuar?",
        "Really Continue?",
        "Desea Continuar?"
    );

    Lang networkName = Lang(
        "Nome da Rede",
        "Network Name",
        "Nombre de Red"
    );

    Lang telemetryPrefix = Lang(
        "Telemetria ",
        "Telemetry ",
        "Telemetria "
    );

    Lang stable = Lang(
        "estável",
        "stable",
        "estable"
    );

    Lang stabilizing = Lang(
        "estabilizando",
        "stabilizing",
        "estabilizando"
    );

    Lang carStr = Lang(
        "Carro",
        "Car",
        "Coche"
    );

    Lang enabledStr = Lang(
        "Habilitado",
        "Enabled",
        "Habilitado"
    );

    Lang disabledStr = Lang(
        "Desabilitado",
        "Disabled",
        "Deshabilitado"
    );

    Lang activeMStr = Lang(
        "Ativo",
        "Active",
        "Activo"
    );

    Lang activeFStr = Lang(
        "Ativa",
        "Active",
        "Activa"
    );

    Lang inactiveFStr = Lang(
        "Desativada",
        "Inactive",
        "Inactiva"
    );

    Lang onStr = Lang(
        "Ligado",
        "On",
        "Encendido"
    );

    Lang offStr = Lang(
        "Desligado",
        "Off",
        "Apagado"
    );

    Lang versionStr = Lang(
        "Versão ",
        "Version ",
        "Version "
    );

    Lang newVersionAvail = Lang(
        "Nova Versão Disponível",
        "New Version Available",
        "Nueva Version Disponible"
    );

    Lang askUpdate = Lang(
        "Deseja Atualizar?",
        "Update Now?",
        "Desea Actualizar?"
    );

    Lang heatingRequired = Lang(
        "Aquecimento Necessário",
        "Heating Required",
        "Calentamiento Necesario"
    );

    Lang calibratingSensor = Lang(
        "Calibrando Sensor",
        "Calibrating Sensor",
        "Calibrando Sensor"
    );

    Lang postponeLimitExceeded = Lang(
        "Limite de Adiamentos\r\nExcedido",
        "Postpone Limit\r\nExceeded",
        "Limite de Aplazamientos\r\nExcedido"
    );

    Lang touchToPostpone = Lang(
        "Toque Para Adiar",
        "Touch To Postpone",
        "Toque Para Aplazar"
    );

    Lang tryAgain = Lang(
        "Tentar Novamente?",
        "Try Again?",
        "Intentar de Nuevo?"
    );

    Lang progressPrefix = Lang(
        "progresso: ",
        "progress: ",
        "progreso: "
    );

    Lang blockedStr = Lang(
        "Bloqueado",
        "Blocked",
        "Bloqueado"
    );

    Lang unblockedStr = Lang(
        "Desbloqueado",
        "Unblocked",
        "Desbloqueado"
    );

    Lang drivingStr = Lang(
        "Dirigindo",
        "Driving",
        "Conduciendo"
    );
};

inline Languages lang;
#endif
