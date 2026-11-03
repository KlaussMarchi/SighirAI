#ifndef DIAGNOSTIC_H
#define DIAGNOSTIC_H
#include "../../device/lang/index.h"
#include "../../utils/time/index.h"


// AUTODIAGNÓSTICO DO MENU E DOS COMANDOS TST_* DA SERIAL
template <typename Parent> class Diagnostic{
  private:
    Parent* device;

  public:
    static const int OBSERVE_TIME     = 10000;   // ms, ABAIXO DOS 15 S QUE O SIGHIRTESTER ESPERA PELO TST_TEMP/TST_SENS
    static const int DHT_INTERVAL     = 2100;    // ms, O DHT22 SÓ MEDE DE NOVO DEPOIS DE 2 S
    static const int SENSOR_INTERVAL  = 500;     // ms ENTRE LEITURAS DO ÁLCOOL E DA PRESSÃO
    static const int HX711_WAIT       = 300;     // ms, O HX711 MEDE A 10 HZ
    static const int RETRY_TIMEOUT    = 5000;    // ms SEM TOQUE NO "TENTAR NOVAMENTE?" VALE NÃO
    static const int RESULTS_TIME     = 5000;    // ms DA TABELA NA TELA

    Diagnostic(Parent* dev):
        device(dev){}

    // SAIR OU NENHUM TOQUE (2 MIN) NÃO RODA NADA: O MENU APAGA A TELA
    void start(){
        const int option = device->display.interface.inputs.trichoices(lang.fullDiagnostic.get(), lang.relayTest.get(), lang.exitStr.get(), 2);

        if(option == 0)
            return evaluate();

        if(option == 1)
            return relay();
    }

    // TODOS OS TESTES EM SEQUÊNCIA, MESMO QUANDO UM FALHA, E NO FINAL A TABELA DO QUE PASSOU
    void evaluate(){
        const char* labels[] = {lang.pressureStr.get(), lang.blowStr.get(), lang.temperatureStr.get(), lang.alcoholStr.get()};
        const bool connected = pressure();
        const bool results[] = {connected, connected && blow(), temperature(), alcohol()};   // SEM O SENSOR DE PRESSÃO NÃO ADIANTA PEDIR O SOPRO

        showResults(labels, results);
        device->await(RESULTS_TIME);
    }

    bool serial(){
        auto& display = device->display;
        
        display.interface.msg(MSG_BLACK, lang.checkingSerial.get());
        display.interface.label("port: " + String(device->telemetry.serial.port), display.width*.1, display.height*.85, display.width*.8, 30, TFT_RED, TFT_BLACK, false);
        device->await(2500);

        if(!device->vehicle.ignition.on && (device->telemetry.type == MIX_TEL || device->telemetry.type == MIX_TEL_NEW)){
            device->display.interface.centeredText(lang.turnOnIgnition.get(), TFT_BLUE, device->display.height*0.75);
            device->await(2500);
        }
        
        unsigned long startTime = Time::get();
        device->telemetry.event("$ETKA!");
        
        while(Time::get() - startTime < 15000){
            device->telemetry.handle();

            if(!device->telemetry.working())
                continue;
            
            display.interface.msg(MSG_BLACK, device->telemetry.last_cmd.getFirst(15));
            display.interface.label("port: " + String(device->telemetry.serial.port), display.width*.1, display.height*.85, display.width*.8, 30, TFT_RED, TFT_BLACK, false);
            device->await(3000);

            device->telemetry.serial.reset();
            return check("serialworking");
        }

        device->telemetry.event("$ETEV06!");
        return fail("ERROR");
    }

    bool blow(){
        const byte result = device->test.blow();
        device->display.brightness.reset();

        if(result == BLOW_DONE)
            return check("pressworking");

        device->display.interface.msg(MSG_RED, lang.noBlow.get());
        device->display.sound.badBeep();

        if(result == BLOW_CUT)
            device->telemetry.event("$NOBLOW!");

        if(device->display.interface.inputs.boolean(lang.tryAgain.get(), nullptr, RETRY_TIMEOUT))
            return blow();

        return fail("$ERROR!");
    }

    bool pressure(){
        auto& sensor = device->sensors.pressure;

        auto read = [&](String& value){
            const bool ready = sensor.check(HX711_WAIT);
            value = String(sensor.get(), 2);
            return ready;
        };

        return observe(lang.testingPressure.get(), SENSOR_INTERVAL, read) ? check("pressworking") : fail("$ERROR!");
    }

    bool alcohol(){
        auto& sensor = device->sensors.alcohol;

        if(sensor.failed())
            return fail("$ETEV24!");

        auto read = [&](String& value){
            const int analog = sensor.get();
            value = String(analog);
            return analog > 0;   // -1: SENSOR FORA DO I2C, ADS SEM RESPOSTA OU LEITURA ABAIXO DE 1000
        };

        return observe(lang.testingAlcohol.get(), SENSOR_INTERVAL, read) ? check("$ETEV20!") : fail("$ETEV24!");
    }

    bool temperature(){
        auto& dht = device->sensors.dht;

        auto read = [&](String& value){
            const float temperature = dht.temperature.get();
            const float humidity    = dht.humidity.get();
            value = String(temperature, 1) + " ºC   " + String(humidity, 0) + " %";
            return dht.temperature.isWorking(temperature) && dht.humidity.isWorking(humidity);
        };

        return observe(lang.testingTemp.get(), DHT_INTERVAL, read) ? check("tempworking") : fail("ERROR");
    }

    void relay(){
        device->display.interface.msg(MSG_BLACK, lang.testingRelay.get());
        device->await(2500);

        if(!device->display.interface.inputs.boolean(lang.askContinue.get(), lang.warningBlockTravel.get()))
            return;

        device->vehicle.block();
        device->vehicle.unblock();
        device->vehicle.block();
    }

    bool fail(const char* event){
        device->display.interface.msg(MSG_RED, lang.testFailed.get());
        device->telemetry.event(event);
        device->display.sound.badBeep();
        return false;
    }

    bool check(const char* event){
        device->display.interface.msg(MSG_GREEN, lang.functionalState.get());
        device->telemetry.event(event);
        device->display.sound.goodBeep();
        return true;
    }

    // LÊ O SENSOR DURANTE OBSERVE_TIME COM A BARRA E O VALOR NA TELA: UMA LEITURA RUIM É SOLUÇO, A SEGUNDA REPROVA NA HORA
    template <typename Read> bool observe(const char* title, const unsigned long interval, Read read){
        auto& display = device->display;
        auto& lcd     = display.lcd;
        const unsigned long startTime = Time::get();
        unsigned long lastRead = 0;
        int bad = 0;

        display.interface.loading.start("", "", OBSERVE_TIME);
        display.interface.font.reset();

        const int lines  = strchr(title, '\n') ? 2 : 1;
        const int titleY = (display.height - 2*lcd.fontHeight())/2 - (lines - 1)*lcd.fontHeight();   // A ÚLTIMA LINHA FICA ONDE O MSG PÕE UMA LINHA SÓ, ACIMA DA BARRA

        display.interface.centeredText(title, TFT_WHITE, titleY, 1, false);
        display.interface.font.setSmall();

        while(Time::get() - startTime < OBSERVE_TIME){
            device->await(50);
            display.interface.loading.step();

            if(Time::get() - lastRead < interval)
                continue;

            String value;
            lastRead = Time::get();
            const bool ok = read(value);

            if(!ok && ++bad > 1)
                return false;

            const String text = ok ? value : String(lang.readFailed.get());
            const int color   = ok ? TFT_WHITE : TFT_RED;
            display.interface.label(text, display.width*0.1, display.height*0.72, display.width*0.8, 40, color, TFT_BLACK);
        }

        return true;
    }

    // UMA FAIXA POR TESTE, AZUL SE PASSOU E VERMELHA SE FALHOU, DIVIDINDO A ALTURA ABAIXO DO TÍTULO
    template <int N> void showResults(const char* (&labels)[N], const bool (&results)[N]){
        auto& display = device->display;
        auto& lcd     = display.lcd;

        const int x      = display.width*0.05;
        const int width  = display.width*0.90;
        const int margin = display.width*0.06;
        const int startY = display.height*0.20;
        const int step   = (display.height*0.95 - startY)/N;
        const int height = step*0.80;

        lcd.fillScreen(TFT_BLACK);
        display.interface.font.reset();
        display.interface.centeredText(lang.selfDiagnostic.get(), TFT_WHITE, display.height*0.07, 2, false);
        display.interface.font.setStyle(&Roboto_Bold12pt8b, TFT_WHITE);

        for(int i=0; i<N; i++){
            const char* status = results[i] ? lang.ok.get() : lang.failStr.get();
            const int y        = startY + i*step;
            const int textY    = y + (height - lcd.fontHeight())/2;

            lcd.fillRoundRect(x, y, width, height, 8, results[i] ? BLUE : TFT_RED);
            lcd.setCursor(x + margin, textY);
            lcd.print(labels[i]);
            lcd.setCursor(x + width - margin - lcd.textWidth(status), textY);
            lcd.print(status);
        }
    }
};


#endif