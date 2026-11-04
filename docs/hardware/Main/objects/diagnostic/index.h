#ifndef DIAGNOSTIC_H
#define DIAGNOSTIC_H
#include "../../device/lang/index.h"
#include "../../utils/time/index.h"
#include "../../utils/json/index.h"
#include "../../utils/listener/index.h"


// AUTODIAGNÓSTICO DO MENU E DOS COMANDOS TST_* DA SERIAL
template <typename Parent> class Diagnostic{
  private:
    Parent* device;

  public:
    static const int OBSERVE_TIME     = 10000;   // ms, ABAIXO DOS 15 S QUE O SIGHIRTESTER ESPERA PELO TST_TEMP/TST_SENS
    static const int SERIAL_TIME      = 10000;   // ms QUE O TESTE SERIAL ESPERA POR COMANDO, SEMPRE ATÉ O FIM DA BARRA
    static const int DHT_INTERVAL     = 2100;    // ms, O DHT22 SÓ MEDE DE NOVO DEPOIS DE 2 S
    static const int SENSOR_INTERVAL  = 500;     // ms ENTRE LEITURAS DO ÁLCOOL E DA PRESSÃO
    static const int HX711_WAIT       = 300;     // ms, O HX711 MEDE A 10 HZ
    static const int EEPROM_WAIT      = 1500;    // ms PARA A EEPROM DO CARTUCHO RESPONDER NO I2C
    static const int RESULT_TIME      = 1000;    // ms DO CARTÃO DO RESULTADO DEPOIS DO BIPE
    static const int RESULTS_TIME     = 6000;    // ms DA TABELA DO FIM
    static const int BLOW_TIMES       = 3;       // SOPROS POR ETAPA NO PROTOCOLO DA SIGHIR
    static const int HINT_TIME        = 8000;    // ms DA INSTRUÇÃO DA ETAPA; UM TOQUE COMEÇA ANTES
    static const int SHOW_TIME        = 1000;    // ms DO RESULTADO DE CADA SOPRO, DEPOIS DO BIPE
    static const int RETRY_TIMEOUT    = 10000;   // ms SEM TOQUE NO "TENTAR NOVAMENTE?" VALE NÃO
    static const int ASK_TIMEOUT      = 20000;   // ms SEM TOQUE NAS PERGUNTAS DO RELÉ VALE NÃO
    static const int WARNING_TIME     = 2500;    // ms DO AVISO ANTES DE BLOQUEAR O VEÍCULO
    static const int STAGES           = 7;       // ETAPAS DO DIAGNÓSTICO COMPLETO
    static const int CARD_PADDING     = 18;      // px DE CADA LADO DO TEXTO NOS CARTÕES
    static const int IGNORED          = 2;       // RESULTADO FORA DA CONTA (0 FALHOU, 1 PASSOU): RELÉ PULADO OU NO MIX

    Diagnostic(Parent* dev):
        device(dev){}

    // LISTA DOS TESTES NA ORDEM DO PROCEDIMENTO, QUE VOLTA DEPOIS DE CADA UM; SAIR OU NENHUM TOQUE (2 MIN) ENCERRA E O MENU APAGA A TELA
    void start(){
        const char* labels[] = {
            lang.fullDiagnostic.get(),
            lang.serialStr.get(),
            lang.temperatureStr.get(),
            lang.alcoholStr.get(),
            lang.memoryStr.get(),
            lang.pressureStr.get(),
            lang.blowStr.get(),
            lang.relayStr.get(),
            lang.exitStr.get()
        };

        const int exit = sizeof(labels)/sizeof(labels[0]) - 1;

        while(true){
            const int option = device->display.interface.inputs.choices(lang.componentTest.get(), lang.selfDiagnostic.get(), labels, exit);

            if(option == exit)
                return;

            if(option == 0)
                evaluate();

            if(option == 1)
                serial();

            if(option == 2)
                temperature();

            if(option == 3)
                alcohol();

            if(option == 4)
                eeprom();

            if(option == 5)
                pressure();

            if(option == 6)
                blow();

            if(option == 7)
                relay();
        }
    }

    // O PROCEDIMENTO DE QUALIDADE DO TESTER NA TELA: SERIAL, SENSORES, MEMÓRIA, UM SOPRO DE CADA TIPO E O RELÉ; SEGUE DEPOIS DE UMA FALHA E SEM PRESSÃO NÃO PEDE SOPRO
    void evaluate(){
        const char* keys[]    = {"serial", "temperature", "alcohol", "eeprom", "pressure", "blow", "relay"};
        const char* names[]   = {lang.failStr.get(), lang.ok.get(), lang.ignoredStr.get()};
        const String labels[] = {lang.serialStr.get(), lang.temperatureStr.get(), lang.alcoholStr.get(), lang.memoryStr.get(), lang.pressureStr.get(), lang.blowStr.get(), lang.relayStr.get()};
        int results[]         = {serial(1), temperature(2), alcohol(3), eeprom(4), pressure(5), false, false};
        String status[STAGES];
        int passed = 0;

        for(byte kind=BLOW_NONE; kind<=BLOW_DONE && results[4]; kind++)
            passed += step(kind, -1, 1, 6);

        results[5] = (passed == BLOW_DONE + 1);   // UM CERTO DE CADA TIPO
        results[6] = relay(7);

        for(int i=0; i<STAGES; i++)
            status[i] = names[results[i]];

        showResults(lang.fullDiagnostic.get(), labels, status, results);
        send("full", keys, results);
        device->await(RESULTS_TIME);
    }

    // PROTOCOLO DE SOPRO DA SIGHIR (MENU E TST_BLOW): 3 SEM SOPRO E, EM CADA FORÇA, 3 INCOMPLETOS E 3 COMPLETOS
    void blow(){
        const byte kinds[]   = {BLOW_NONE, BLOW_CUT, BLOW_CUT, BLOW_CUT, BLOW_DONE, BLOW_DONE, BLOW_DONE};
        const int forces[]   = {-1, 0, 1, 2, 0, 1, 2};   // FRACO, MÉDIO E FORTE; -1 = SEM FORÇA
        const char* keys[]   = {"pressure", "blow"};
        const int N          = sizeof(kinds);
        const bool connected = device->sensors.pressure.check(HX711_WAIT);
        int ok[]             = {connected, connected};
        String labels[N], status[N];
        int results[N];

        if(!connected){   // SEM O HX711 O DETECTOR NÃO VÊ SOPRO E O "SEM SOPRO" PASSARIA
            header(lang.blowTest.get(), "HX711", 0);
            result(false, "$ERROR!", lang.readFailed.get());
            return send("blow", keys, ok);
        }

        for(int i=0; i<N; i++){
            const int passed = step(kinds[i], forces[i], BLOW_TIMES);
            labels[i]  = name(kinds[i], forces[i], " ", true);
            status[i]  = String(passed) + "/" + String(BLOW_TIMES);
            results[i] = (passed == BLOW_TIMES);
            ok[1]      = ok[1] && results[i];
        }

        showResults(lang.blowTest.get(), labels, status, results);
        send("blow", keys, ok);
        device->await(RESULTS_TIME);
    }

    // UMA ETAPA: A INSTRUÇÃO COM A BARRA ATÉ O PRIMEIRO SOPRO E times SOPROS; COM ERRO O OPERADOR PODE REFAZER, E VALE A ÚLTIMA VEZ
    int step(const byte kind, const int force, const int times, const int stage=0){
        const char* hints[] = {lang.dontBlowHint.get(), lang.shortBlowHint.get(), lang.longBlowHint.get()};
        auto& display       = device->display;
        auto& pressure      = device->sensors.pressure;
        const String title  = name(kind, force, " ");
        String hint         = hints[kind];
        int passed          = 0;

        if(kind == BLOW_NONE)
            hint += " " + String(pressure.BREATH_TIMEOUT/1000) + " s";

        header(title, String(lang.blowSmoothing.get()) + " " + String(pressure.blowProb, 2) + " s", stage);
        bar(0);
        reading("", hint, TFT_WHITE);
        display.touch.reset();

        const unsigned long startTime = Time::get();

        while(progress(startTime, HINT_TIME) && !display.touch.click())
            device->sensors.warm();

        for(int n=1; n<=times; n++)
            passed += (breath(kind, force, n, times, stage) == kind);

        if(passed < times && display.interface.inputs.boolean(lang.tryAgain.get(), nullptr, RETRY_TIMEOUT))
            return step(kind, force, times, stage);

        return passed;
    }

    // UM SOPRO PELA DETECÇÃO DO TESTE REAL: A TELA DELE, O RESULTADO COM PICO E DURAÇÃO E UMA LINHA NA SERIAL PARA O TESTER
    byte breath(const byte kind, const int force, const int n, const int times, const int stage){
        static const char* keys[]   = {"none", "cut", "full"};   // BLOW_NONE, BLOW_CUT E BLOW_DONE NA SERIAL
        static const char* forces[] = {"weak", "medium", "strong"};   // FRACO, MÉDIO E FORTE NA SERIAL
        auto& display     = device->display;
        auto& pressure    = device->sensors.pressure;
        auto& test        = device->test;
        const String what = (kind == BLOW_NONE) ? String(pressure.BREATH_TIMEOUT/1000) + " s" : name(kind, force, " ");
        const String turn = String(n) + "/" + String(times);

        display.brightness.update(50);
        pressure.tare(true);

        if(kind == BLOW_NONE)
            display.interface.msg(MSG_BLACK, lang.dontBlow.get());

        if(kind != BLOW_NONE)
            test.screens.blow();   // "ASSOPRE" E O BIPE DO TESTE REAL

        display.interface.font.setSmall();
        display.interface.centeredText(what + "\r\n" + turn, TFT_WHITE, display.height*0.66, 2, false);

        const byte result = test.breathe();
        String values     = String(lang.peakStr.get()) + " " + String(pressure.blower.peak, 1);
        Json<256> line;

        display.brightness.reset();
        line.data["blow"]      = keys[kind];
        line.data["force"]     = (force < 0) ? "" : forces[force];
        line.data["attempt"]   = n;
        line.data["of"]        = times;
        line.data["result"]    = keys[result];
        line.data["peak"]      = pressure.blower.peak;
        line.data["ms"]        = test.blowTime;
        line.data["blow_prob"] = pressure.blowProb;
        device->telemetry.serial.send(line.toString());   // FORA DO /logs.txt, COMO O /get-data

        if(result != BLOW_NONE)
            values += "   " + String(test.blowTime/1000.0, 1) + " s";

        header(name(kind, force, " "), turn, stage);
        card(result == kind, name(result, -1, ""), values);
        result == kind ? display.sound.okBeep() : display.sound.badBeep();
        device->await(SHOW_TIME);
        return result;
    }

    // O MÓDULO OU O TESTER TÊM SERIAL_TIME PARA MANDAR QUALQUER COMANDO: A BARRA VAI SEMPRE ATÉ O FIM E VALE O QUE CHEGOU NOS ÚLTIMOS 15 S; O MIX SÓ FALA COM O PÓS-CHAVE LIGADO
    bool serial(const int stage=0){
        auto& telemetry     = device->telemetry;
        const bool off      = (telemetry.type == MIX_TEL || telemetry.type == MIX_TEL_NEW) && !device->vehicle.ignition.on;
        unsigned long shown = telemetry.working() ? 0 : telemetry.serial.lastAckTime;   // O COMANDO DE ANTES DO TESTE JÁ APARECE NA PRIMEIRA VOLTA

        header(lang.serialComm.get(), String(lang.telemetryStr.get()) + " " + telemetry.toText(), stage);
        bar(0);
        reading(lang.lastCommand.get(), off ? lang.turnOnIgnition.get() : lang.waitingCommand.get(), off ? TFT_ORANGE : LIGHT_GREY);
        telemetry.event("$ETKA!");

        const unsigned long startTime = Time::get();

        while(progress(startTime, SERIAL_TIME)){
            telemetry.handle();

            if(telemetry.serial.lastAckTime == shown || !telemetry.working())
                continue;

            shown = telemetry.serial.lastAckTime;
            reading(String(lang.lastCommand.get()) + " - " + lang.portStr.get() + " " + String(telemetry.serial.port), wrap(telemetry.last_cmd.toString()), TFT_WHITE);
        }

        const bool ok = telemetry.working();
        telemetry.serial.reset();

        if(!ok)
            telemetry.event("$ETEV06!");

        return result(ok, ok ? "serialworking" : "ERROR", ok ? wrap(telemetry.last_cmd.toString()) : String(lang.noCommand.get()));
    }

    bool temperature(const int stage=0){
        auto& dht = device->sensors.dht;
        String value;

        auto read = [&](String& text){
            const float temperature = dht.temperature.get();
            const float humidity    = dht.humidity.get();
            text = String(temperature, 1) + " ºC   " + String(humidity, 0) + " %";
            return dht.temperature.isWorking(temperature) && dht.humidity.isWorking(humidity);
        };

        header(lang.temperatureSensor.get(), "DHT22", stage);
        const bool ok = observe(value, DHT_INTERVAL, read);
        return result(ok, ok ? "tempworking" : "ERROR", ok ? value : String(lang.readFailed.get()));
    }

    bool alcohol(const int stage=0){
        auto& sensor = device->sensors.alcohol;
        String value;

        auto read = [&](String& text){
            const int analog = sensor.get();
            text = String(analog);
            return analog > 0;   // -1: SENSOR FORA DO I2C, ADS SEM RESPOSTA OU LEITURA ABAIXO DE 1000
        };

        const bool connected = !sensor.failed();   // EM DEBUG OU FORA DO I2C A TELA DE FALHA DO SENSOR APARECE ANTES
        header(lang.alcoholSensor.get(), "ADS1115", stage);
        const bool ok = connected && observe(value, SENSOR_INTERVAL, read);
        return result(ok, ok ? "$ETEV20!" : "$ETEV24!", ok ? value : String(lang.readFailed.get()));
    }

    // A EEPROM DO CARTUCHO RESPONDE NO I2C E GUARDA O ID ETL E OS 4 COEFICIENTES DA CALIBRAÇÃO
    bool eeprom(const int stage=0){
        auto& sensor  = device->sensors.alcohol;
        auto& storage = sensor.storage;

        header(lang.sensorMemory.get(), "EEPROM", stage);
        bar(0);
        reading(lang.sensorId.get(), "I2C 0x" + String(storage.eeprom_addr, HEX), LIGHT_GREY);

        if(!sensor.eeprom.check(storage.eeprom_addr, EEPROM_WAIT))
            return result(false, "$ETEV24!", lang.sensorNoEeprom.get());

        bar(30);
        storage.update();   // 170 BYTES A 10 MS CADA
        bar(100);

        const String date   = storage.calibration_date.toString();
        const bool valid    = (storage.id.find("ETL") == 0 && storage.id.length() >= 18);   // ETL + 16 DÍGITOS; O LEGADO TEM 15
        const bool ok       = valid && storage.has_coefs;
        const String when   = (date.length() >= 10) ? "\n" + String(lang.calibratedOn.get()) + " " + date.substring(8, 10) + "/" + date.substring(5, 7) + "/" + date.substring(0, 4) : "";
        const String detail = !valid             ? String(lang.invalidSensorId.get()) :
                              !storage.has_coefs ? storage.id.toString() + "\n" + lang.noCoefs.get() : storage.id.toString() + when;

        return result(ok, ok ? "eepromworking" : "$ETEV24!", detail);
    }

    bool pressure(const int stage=0){
        auto& sensor = device->sensors.pressure;
        String value;

        auto read = [&](String& text){
            const bool ready = sensor.check(HX711_WAIT);
            text = String(sensor.get(), 2);
            return ready;
        };

        header(lang.pressureSensor.get(), "HX711", stage);
        const bool ok = observe(value, SENSOR_INTERVAL, read);
        return result(ok, ok ? "pressworking" : "$ERROR!", ok ? value : String(lang.readFailed.get()));
    }

    // BLOQUEIA, DESBLOQUEIA E BLOQUEIA PELO RASTREADOR E O OPERADOR CONFIRMA SE O RELÉ COMUTOU; NO MIX QUEM COMUTA É O MÓDULO E O RESULTADO FICA IGNORADO
    int relay(const int stage=0){
        auto& inputs          = device->display.interface.inputs;
        auto& vehicle         = device->vehicle;
        const byte type       = device->telemetry.type;
        const bool mix        = (type == MIX_TEL || type == MIX_TEL_NEW);
        const String subtitle = String(lang.telemetryStr.get()) + " " + device->telemetry.toText();

        header(lang.relayTest.get(), subtitle, stage);
        reading("", lang.warningBlockTravel.get(), TFT_ORANGE);
        device->await(WARNING_TIME);

        const bool asked = inputs.boolean(lang.askContinue.get(), nullptr, ASK_TIMEOUT);

        if(asked){
            vehicle.block();
            vehicle.unblock();
            vehicle.block();
        }

        const int state = (!asked || mix) ? IGNORED : inputs.boolean(lang.relaySwitched.get(), nullptr, ASK_TIMEOUT);
        header(lang.relayTest.get(), subtitle, stage);
        return result(state, nullptr, (asked && mix) ? lang.relayByModule.get() : "");
    }

    // O CARTÃO DO RESULTADO, O EVENTO PARA A SERIAL (O TESTER ESPERA POR ELE) E O BIPE
    int result(const int state, const char* event, const String& detail){
        const char* texts[] = {lang.testFailed.get(), lang.functionalState.get(), lang.ignoredStr.get()};
        card(state, texts[state], detail);

        if(event != nullptr)
            device->telemetry.event(event);

        if(state != IGNORED)
            state ? device->display.sound.okBeep() : device->display.sound.badBeep();

        device->await(RESULT_TIME);
        return state;
    }

    // LÊ O SENSOR DURANTE OBSERVE_TIME COM A BARRA E O VALOR AO VIVO: UMA LEITURA RUIM É SOLUÇO, A SEGUNDA REPROVA NA HORA
    template <typename Read> bool observe(String& value, const unsigned long interval, Read read){
        const unsigned long startTime = Time::get();
        unsigned long lastRead = 0;
        int bad = 0;

        bar(0);

        while(progress(startTime, OBSERVE_TIME)){
            device->await(50);

            if(Time::get() - lastRead < interval)
                continue;

            lastRead      = Time::get();
            const bool ok = read(value);

            if(!ok && ++bad > 1)
                return false;

            reading(lang.currentReading.get(), ok ? value : String(lang.readFailed.get()), ok ? TFT_WHITE : TFT_RED);
        }

        return true;
    }

    // A BARRA PELO TEMPO DECORRIDO, REDESENHADA A CADA 100 MS; DEVOLVE FALSE DEPOIS DE MOSTRAR OS 100%
    bool progress(const unsigned long startTime, const unsigned long total){
        static Listener timer = Listener(100);
        const unsigned long elapsed = Time::get() - startTime;

        if(timer.ready() || elapsed >= total)
            bar(min(elapsed, total)*100/total);

        return elapsed < total;
    }

    // O COMANDO EM ATÉ DUAS LINHAS DA LARGURA DO CARTÃO, NA FONTE PEQUENA; O QUE SOBRA VIRA "..."
    String wrap(const String& text){
        auto& interface = device->display.interface;
        const int width = device->display.width*0.84 - 2*CARD_PADDING;
        int n = text.length();

        interface.font.setSmall();

        while(n > 0 && device->display.lcd.textWidth(text.substring(0, n)) > width)
            n--;

        return (n == text.length()) ? text : text.substring(0, n) + "\n" + interface.menu.fit(text.substring(n), width);
    }

    // CABEÇALHO DAS TELAS DE TESTE: A ETIQUETA AZUL (A ETAPA NO DIAGNÓSTICO COMPLETO), O COMPONENTE E O QUE ESTÁ SENDO FEITO
    void header(const String& title, const String& subtitle, const int stage){
        auto& display    = device->display;
        const String tag = (stage > 0) ? String(lang.fullDiagnostic.get()) + "   " + String(stage) + "/" + String(STAGES) : String(lang.componentTest.get());

        display.lcd.fillScreen(BG_COLOR);
        display.interface.pill(tag, display.height*0.04, BLUE);
        display.interface.font.setStyle(&Roboto_Bold12pt8b, TFT_WHITE);
        display.interface.centeredText(title, TFT_WHITE, display.height*0.135, 1, false);
        display.interface.font.setSmall();
        display.interface.centeredText(subtitle, LIGHT_GREY, display.height*0.205, 1, false);
    }

    void bar(const int percent){
        auto& display    = device->display;
        const int x      = display.width*0.1;
        const int y      = display.height*0.32;
        const int width  = display.width*0.8;
        const int height = 14;
        const int filled = width*percent/100;

        if(percent == 0)
            display.lcd.fillRoundRect(x, y, width, height, height/2, DARK_GREY);

        display.lcd.fillRoundRect(x, y, filled, height, min(height, filled)/2, BLUE);
        display.interface.font.setSmall();
        display.interface.label(String(percent) + "%", x, y + height + 6, width, 24, LIGHT_GREY, BG_COLOR);
    }

    // CARTÃO CINZA DA LEITURA AO VIVO OU DA INSTRUÇÃO, NA MAIOR FONTE EM QUE AS LINHAS CABEM
    void reading(const String& caption, const String& text, const int color){
        auto& display    = device->display;
        const int x      = display.width*0.08;
        const int y      = display.height*0.45;
        const int width  = display.width*0.84;
        const int height = display.height*0.32;
        const int cut    = text.indexOf('\n');
        const String lines[] = {(cut < 0) ? text : text.substring(0, cut), (cut < 0) ? "" : text.substring(cut + 1)};
        const int count  = (cut < 0) ? 1 : 2;

        display.lcd.fillRoundRect(x, y, width, height, 14, DARK_GREY);
        display.interface.font.setSmall();
        display.interface.centeredText(caption, LIGHT_GREY, y + height*0.12, 1, false);
        display.interface.font.setLargest(lines, width - 2*CARD_PADDING, height/3);
        display.interface.centeredText(text, color, y + height*0.55 - count*display.lcd.fontHeight()/2, 1, false);
    }

    // CARTÃO DO RESULTADO NO LUGAR DA BARRA E DA LEITURA: VERDE PASSOU, VERMELHO FALHOU, CINZA IGNORADO
    void card(const int state, const String& text, const String& detail){
        const int colors[] = {SOFT_RED, YELLOW, TFT_DARKGREY};
        auto& display      = device->display;
        auto& lcd          = display.lcd;
        const int x        = display.width*0.08;
        const int y        = display.height*0.30;
        const int width    = display.width*0.84;
        const int height   = display.height*0.52;
        const int radius   = height*0.15;
        const int centerY  = y + height*0.27;

        lcd.fillRect(0, y, display.width, display.height - y, BG_COLOR);
        lcd.fillRoundRect(x, y, width, height, 18, colors[state]);
        lcd.fillCircle(display.width/2, centerY, radius, TFT_WHITE);
        mark(state, display.width/2, centerY, radius, colors[state]);
        display.interface.font.setStyle(&Roboto_Bold12pt8b, TFT_WHITE);
        display.interface.centeredText(text, TFT_WHITE, y + height*0.56, 1, false);
        display.interface.font.setSmall();
        display.interface.centeredText(detail, TFT_WHITE, y + height*0.72, 1, false);
    }

    // O SINAL DENTRO DO CÍRCULO: VISTO, X OU TRAÇO
    void mark(const int state, const int x, const int y, const int r, const int color){
        const int t = r/4;

        if(state == 1){
            stroke(x - r*0.45, y + r*0.02, x - r*0.12, y + r*0.36, t, color);
            return stroke(x - r*0.12, y + r*0.36, x + r*0.48, y - r*0.34, t, color);
        }

        if(state == 0){
            stroke(x - r*0.38, y - r*0.38, x + r*0.38, y + r*0.38, t, color);
            return stroke(x - r*0.38, y + r*0.38, x + r*0.38, y - r*0.38, t, color);
        }

        stroke(x - r*0.45, y, x + r*0.45, y, t, color);
    }

    // TRAÇO GROSSO EM DOIS TRIÂNGULOS E PONTAS REDONDAS: SEM MISO O PAINEL NÃO LÊ PIXEL, ENTÃO NADA DE LINHA SUAVIZADA
    void stroke(const int x0, const int y0, const int x1, const int y1, const int t, const int color){
        auto& lcd       = device->display.lcd;
        const float len = hypot(x1 - x0, y1 - y0);
        const int dx    = (y1 - y0)/len*t/2;
        const int dy    = (x0 - x1)/len*t/2;

        lcd.fillTriangle(x0 + dx, y0 + dy, x1 + dx, y1 + dy, x1 - dx, y1 - dy, color);
        lcd.fillTriangle(x0 + dx, y0 + dy, x1 - dx, y1 - dy, x0 - dx, y0 - dy, color);
        lcd.fillCircle(x0, y0, t/2, color);
        lcd.fillCircle(x1, y1, t/2, color);
    }

    // A TABELA DO FIM: O RESUMO (OS IGNORADOS FICAM FORA DA CONTA) E UMA LINHA POR TESTE COM O RESULTADO NA COR DELE
    template <int N> void showResults(const char* title, const String (&labels)[N], const String (&status)[N], const int (&results)[N]){
        const int colors[] = {SOFT_RED, YELLOW, TFT_DARKGREY};
        auto& display      = device->display;
        auto& lcd          = display.lcd;
        const int x        = display.width*0.05;
        const int width    = display.width*0.90;
        const int margin   = display.width*0.05;
        const int startY   = display.height*0.18;
        const int step     = (display.height*0.985 - startY)/N;
        const int height   = step*0.84;
        int passed = 0, counted = 0, badge = 0;

        for(int i=0; i<N; i++){
            passed  += (results[i] == 1);
            counted += (results[i] != IGNORED);
        }

        const bool ok        = (passed == counted);
        const String summary = String(ok ? lang.approvedStr.get() : lang.reprovedStr.get()) + "   " + String(passed) + "/" + String(counted);

        display.brightness.update();
        lcd.fillScreen(BG_COLOR);
        display.interface.font.setStyle(&Roboto_Bold12pt8b, TFT_WHITE);
        display.interface.centeredText(title, TFT_WHITE, display.height*0.025, 1, false);
        display.interface.pill(summary, display.height*0.09, ok ? YELLOW : SOFT_RED);
        lcd.setFont(&Roboto_Bold10pt8b);

        for(int i=0; i<N; i++)
            badge = max(badge, (int) lcd.textWidth(status[i]) + margin);

        for(int i=0; i<N; i++){
            const int y = startY + i*step;

            lcd.fillRoundRect(x, y, width, height, 10, DARK_GREY);
            lcd.fillRoundRect(x, y, 8, height, 4, colors[results[i]]);
            lcd.fillRoundRect(x + width - margin/2 - badge, y + height*0.18, badge, height*0.64, height*0.32, colors[results[i]]);
            lcd.setTextColor(TFT_WHITE);
            lcd.setCursor(x + width - margin/2 - (badge + lcd.textWidth(status[i]))/2, y + (height - lcd.fontHeight())/2);
            lcd.print(status[i]);
        }

        display.interface.font.setLargest(labels, width - badge - 2*margin, height);
        lcd.setTextColor(TFT_WHITE);

        for(int i=0; i<N; i++){
            lcd.setCursor(x + margin + 4, startY + i*step + (height - lcd.fontHeight())/2);
            lcd.print(labels[i]);
        }
    }

    // NOME DA ETAPA: O TIPO DO SOPRO E A FORÇA (-1 = SEM FORÇA); brief É O DA TABELA, ONDE O NOME INTEIRO NÃO CABE
    String name(const byte kind, const int force, const char* separator, const bool brief=false){
        const char* kinds[]  = {lang.noBlow.get(), brief ? lang.incompleteStr.get() : lang.incompleteBlow.get(), brief ? lang.completeStr.get() : lang.completeBlow.get()};
        const char* forces[] = {lang.weakStr.get(), lang.mediumStr.get(), lang.strongStr.get()};
        return (force < 0) ? String(kinds[kind]) : String(kinds[kind]) + separator + forces[force];
    }

    // FIM DO DIAGNÓSTICO NA SERIAL PARA O TESTER: {"diagnostic": name, <teste>: passou}, COM null PARA O IGNORADO
    template <int N> void send(const char* name, const char* (&keys)[N], const int (&results)[N]){
        Json<256> line;
        line.data["diagnostic"] = name;

        for(int i=0; i<N; i++)
            line.data[keys[i]] = (results[i] == 1);

        for(int i=0; i<N; i++)
            if(results[i] == IGNORED)
                line.data[keys[i]] = nullptr;

        device->telemetry.serial.send(line.toString());
    }
};


#endif
