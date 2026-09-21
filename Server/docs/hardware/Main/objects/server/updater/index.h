#ifndef UPDATER_H
#define UPDATER_H
#include "../../../device/lang/index.h"
#include <Update.h>
#include <SPI.h>
#include "../../../utils/time/index.h"
#include "../../../utils/text/index.h"
#include "../../../globals/functions.h"


template <typename Parent> class Updater{
  private:
    Parent* device;
    int percent;

  public:
    bool needed;

    Updater(Parent* dev):
        device(dev){}
    
    void start(){
        if(!device->server.connected())
            device->server.connect(true);

        config();
        download();
        handleCheck(true);
    }

    void handleCheck(bool force=false){ 
        static Listener timer = Listener(15000);
        static unsigned long lastUpdate = Time::get();
        static bool first_time = false;

        if(first_time)
            force = true;

        if(!force && timer.ready())
            return;
        
        if(!force && Time::get() - lastUpdate < 30*60*1000)
            return;

        if(!device->server.connected())
            return;

        Text<64> response = device->server.get(
            "api/v2/devices/check-update/?id=" + device->id.toString()    + 
            "&sensor_id=" + device->sensors.alcohol.storage.id.toString() +
            "&firmware="  + String(device->firmware)
        );

        lastUpdate = Time::get();
        first_time = false;

        if(!response.contains("true"))
            return;

        if(device->in_setup || device->display.interface.menu.active)
            requestUpdate();

        needed = true;
    }

    void requestUpdate(){
        auto& display = device->display;
        needed = (bool) display.interface.inputs.boolean(lang.newVersionAvail.get(), lang.askUpdate.get());

        if(!needed && display.interface.menu.active)
            return display.turnOFF();
        
        if(needed)
            return start();  
    }

    bool config(){
        device->display.interface.alert(lang.remoteConfig.get(), lang.ensureInternet.get(), MSG_WHITE, 2000);
        Text<512> request = "{\"esp_id\": \"" + device->id.toString() + "\"}";

        const String response = device->server.post("checkSettings/", request.toString(), 10000);
        Serial.println("update response: " + response);
        Json<512> settings;

        if(response == "-1"){
            device->display.interface.alert(lang.configError.get(), lang.noServerRes.get());
            return false;
        }

        if(!settings.parse(response.c_str())){
            device->display.interface.alert(lang.configError.get(), response.c_str());
            return false;
        }

        if(!settings.data.containsKey("status") || !settings.data.containsKey("data")){
            device->display.interface.alert(lang.configError.get(), lang.invalidKeys.get());
            return false;
        }

        if(settings.data["data"].as<String>().indexOf("doesnt") != -1){
            device->display.interface.alert(lang.verified.get(), lang.noConfigNeeded.get(), MSG_WHITE);
            return false;
        }

        if(settings.data["status"].as<String>() != "success"){
            device->display.interface.alert(lang.configError.get(), settings.data["data"].as<String>());
            return false;
        }

        if(settings.data["data"].as<String>() == "None"){
            device->display.interface.alert(lang.verified.get(), lang.noConfigNeeded.get(), MSG_WHITE);
            return false;
        }

        request = settings.data["data"].as<String>();
        settings.parse(request.get());

        for(JsonPair data: settings.data.as<JsonObject>())
            device->settings.params.data[data.key()] = data.value().as<String>();

        device->settings.save();
        device->display.interface.alert(lang.deviceConfigured.get(), "", MSG_WHITE);
        device->telemetry.event("$ETEV07!");
        return true;
    }

    void download(){
        auto& display = device->display;
        display.interface.msg(MSG_WHITE, lang.firmwareUpdate.get());
        display.interface.centeredText(device->id.toString(), TFT_BLACK, display.height*0.65);  
        device->await(2000);
        percent = 0;
        
        if(!device->server.connected())
            return;
        
        device->await(500);
        String data = "{\"esp_id\":\"" + device->id.toString() + "\"}";
        Serial.println(data);
        
        HTTPClient http;
        http.begin(device->server.URL.toString() + "update/");
        http.addHeader("Content-Type", "application/json");
        device->await(700);

        int httpCode = http.POST(data);
        bool success = false;

        if(httpCode != 200){
            http.end();
            display.interface.msg(MSG_RED, lang.invalidServerRes.get());
            return display.sound.badBeep();
        }   
        
        WiFiClient *client   = http.getStreamPtr();
        size_t contentLength = http.getSize();
        bool canBegin = Update.begin(contentLength);

        if(canBegin){
            display.interface.msg(MSG_WHITE, lang.updatingDevice.get());
            display.interface.centeredText(lang.progress0.get(), TFT_BLACK, display.height*0.70);     

            Update.onProgress([this](size_t progress, size_t total){
                auto& display = device->display;
                int newPercent = (progress * 100) / total;    

                if(newPercent - percent < 5)
                    return;

                percent = newPercent;
                display.lcd.fillRect(0, display.height*0.7, display.width, display.height, TFT_WHITE);
                display.interface.centeredText(lang.progressPrefix.get() + String(percent) + "%", TFT_BLACK, display.height*0.7);
            });

            if(Update.writeStream(*client) != contentLength)
                success = false;

            if(Update.end()){
                if(Update.isFinished())
                    success = true;
                else
                    success = false;
            }
            else{
                success = false;
            }
        }
        else {
            success = false;
        }

        if(success){
            display.interface.msg(MSG_GREEN, lang.completed.get());
            display.interface.centeredText(lang.restartingDevice.get(), TFT_WHITE, display.height*0.70);     
            device->telemetry.event("$ETEV10!");
            display.sound.goodBeep();
            ESP.restart();
        }
        
        display.interface.msg(MSG_RED, lang.updateFailed.get());
        display.sound.badBeep();
        http.end();
    }

    void local(){
        const unsigned long startTime = Time::get();
        static const int CHUNK_SIZE   = (1.4)*2048;
        
        Serial.println("Iniciando Update Local");
        device->telemetry.serial.send("_STARTING_UPDATE_", true);
        finished(true);

        if(!Update.begin(UPDATE_SIZE_UNKNOWN)){
            Serial.println("deu ruim update size");
            return;
        }

        while(!device->telemetry.serial.uart->available()){
            if(Time::get() - startTime < 35000)
                continue;

            Serial.println("Erro ao atualizar");
            return;
        }

        char chunk[CHUNK_SIZE];
        bool start = false;
        int index  = 0;

        while(!finished(false)){
            if(!device->telemetry.serial.uart->available())
                continue;
            
            char newChar = device->telemetry.serial.uart->read();
            
            if(!start){ // ESPERA O CHAR DE INICIALIZAÇÃO
                if(newChar != '$')
                    continue;
                
                start = true;
                index = 0;
            }

            if(newChar != '!'){ // PREENCHE O VETOR COM UPDATE
                chunk[index] = newChar;
                index++;
                continue;
            }

            const int length = index;
            uint8_t decoded[CHUNK_SIZE];
            size_t size = base64Decode(chunk, decoded, length);

            size_t written = Update.write(decoded, size);
            device->telemetry.serial.send("written", true);

            if(size == 0 || written != size){
                Serial.println("Erro ao escrever | size: " + String(size));
                return;
            }

            start = false;
            index = 0;
        }

        if(Update.end(true)){
            Serial.println("concluido! reiniciando");
            ESP.restart();
        }
        
        Serial.println("Erro ao atualizar");
    }

    bool finished(bool reset){
        static unsigned long lastUpdate;

        if(device->telemetry.serial.uart->available() || reset)
            lastUpdate = Time::get();

        return (Time::get() - lastUpdate > 10000);
    }
};

#endif