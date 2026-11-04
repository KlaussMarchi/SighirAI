#ifndef SERVER_ROUTES_H
#define SERVER_ROUTES_H
#include "../../../device/lang/index.h"
#include "../../../globals/functions.h"
#include <Arduino.h>


template <typename Parent> class ServerRoutes{
  private:
    Parent* device;
    bool registered = false;

  public:
    ServerRoutes(Parent* dev):
        device(dev){}

    void setup(){
        // enable() roda de novo a cada volta do sleeper/troca de canal; cada on() aloca um handler
        if(registered)
            return;

        registered = true;

        device->server.network.on("/CHECK", HTTP_GET, [this](){
            this->onCheck(); 
        });

        device->server.network.on("/TEST", HTTP_GET, [this](){ 
            this->onTest();
        });
        
        device->server.network.on("/NPTEST", HTTP_GET, [this](){
            this->npTest();
        });

        device->server.network.on("/ALCTEST", HTTP_GET, [this](){
            this->alcTest();
        });

        device->server.network.on("/WIFI", HTTP_GET, [this](){
            this->onWifi();
        });

        device->server.network.on("/SENSOR", HTTP_GET, [this](){
            this->onSensor();
        });

        device->server.network.on("/CF_SENSOR", HTTP_POST, [this](){
            this->onConfigSensor();
        });

        device->server.network.on("/validateData", HTTP_GET, [this](){
            this->onValidateData();
        });

        device->server.network.on("/RESET", HTTP_GET, [this](){
            device->server.send(lang.ok.get()); delay(1000); device->reset();
        });

        device->server.network.on("/ERASE_SETTINGS", HTTP_GET, [this](){
            device->server.send(lang.ok.get()); delay(1000); device->settings.erase();
        });

        device->server.network.on("/STATUS", HTTP_GET, [this](){ 
            this->status();
        });

        device->server.network.on("/INFO", HTTP_GET, [this](){ 
            this->onLogs();
        });

        device->server.network.on("/CLEAN", HTTP_GET, [this](){ 
            this->cleanLogs();
        });
        
        device->server.network.on("/ALL_CONFIGS", HTTP_GET, [this](){ 
            this->getAll(); 
        });

        device->server.network.on("/SEND_ALC", HTTP_GET, [this](){ 
            this->sendAlcohol(); 
        });

        device->server.network.on("/update", HTTP_GET, [this](){ 
            this->onUpdate();
        });

        device->server.network.on("/WIFI_SETUP", HTTP_POST, [this](){ 
            this->onWifiSetup(); 
        });

        device->server.network.on("/CONFIG", HTTP_POST, [this](){ 
            this->onCommand(); 
        });
        
        device->server.network.on("/SET_ALL_CONFIGS", HTTP_POST, [this](){ 
            this->setAll(); 
        });
    }
    
    void onUpdate(){
        device->server.send(lang.ok.get());
        device->server.updater.start();
        device->display.turnOFF();
    }

    void sendAlcohol(){
        device->server.send(device->test.model.getInfo().get());
    }

    void onLogs(){
        Json<1024> info;
        info.data["company"] = device->company.name;
        info.data["vehicle_plate"] = "None";
        info.data["esp_id"]    = device->id.get();
        info.data["sensor_id"] = device->sensors.alcohol.storage.id.get();
        info.data["event"] = device->logs.get();
        device->server.send(info.toString().c_str());
    }

    void cleanLogs(){
        device->logs.erase();
        device->server.send(lang.ok.get());
    }

    void onWifiSetup(){
        if(!device->server.network.hasArg("plain"))
            return device->server.send("error");

        String request = device->server.network.arg("plain");
        Text<33> ssid   = request.substring(request.indexOf("$")+1, request.indexOf(":"));
        Text<65> passwd = request.substring(request.indexOf(":")+1, request.lastIndexOf("!"));   // senha pode ter "!"

        device->settings.params.set("ssid", ssid.get());
        device->settings.params.set("passwd", passwd.get());
        device->settings.save();

        device->server.send(lang.ok.get());
        device->server.connect(true);
    }

    void onCheck(){
        device->server.send(device->info().c_str());
    }

    void onCommand(){
        if(!device->server.network.hasArg("plain"))
            return device->server.send("Bad Request");
        
        String request = device->server.network.arg("plain");
        //Serial.println("Eita porra: " + request);
        
        device->telemetry.serial.command.set(request);
        device->telemetry.serial.available = true;
        device->telemetry.handleProtocol();

        const int length     = device->telemetry.response.length();
        const char* response = (length > 0) ? device->telemetry.response.get() : lang.ok.get(); 
        device->server.send(response);

        device->telemetry.handleOperation();
        device->telemetry.serial.reset();
    }

    void setAll(){
        if(!device->server.network.hasArg("plain"))
            return device->server.send("error");
        
        String request = device->server.network.arg("plain");
        StaticJsonDocument<2048> newSettings;

        if(!stringToJson(request, newSettings))
            return device->server.send("error");

        for(JsonPair keyValue : newSettings.as<JsonObject>()){
            String key   = keyValue.key().c_str();
            String value = keyValue.value().as<String>();
            device->settings.params.data[key] = value;
        }

        device->settings.save();
        device->vehicle.valet.refresh();
        device->sensors.pressure.setBlowProb(device->settings.template get<float>("blowProb"));
        device->server.send(lang.ok.get());
    }

    void onTest(){
        device->server.send(lang.ok.get());
        device->test.start();
    }

    void npTest(){
        bool aux = device->sensors.pressure.debug;
        device->sensors.pressure.debug = true;
        device->server.send(lang.ok.get());
        device->test.start();
        device->sensors.pressure.debug = aux;
    }

    void alcTest(){
        bool aux = device->test.alcohol_debug;
        device->test.alcohol_debug = true;
        device->server.send(lang.ok.get());
        device->test.start();
        device->test.alcohol_debug = aux;
    }

    void onWifi(){
        Text<20> response = "$" + String(WiFi.status() == WL_CONNECTED) + "!";
        device->server.send(response.get());
    }

    void onSensor(){
        device->sensors.alcohol.storage.update();
        auto response = device->sensors.alcohol.storage.id;
        device->server.send(response.get());
    }

    // "$<ID ETL><JSON>;!" da tela Gerar ID do app. Erro volta com 400: o app só olha o response.ok
    void onConfigSensor(){
        if(!device->server.network.hasArg("plain"))
            return device->server.send("sem dados", 400);

        const char* error = device->sensors.alcohol.storage.configure(device->server.network.arg("plain"));

        if(error != nullptr)
            return device->server.send(error, 400);

        device->server.send(lang.ok.get());
    }

    // Validar Sensor do app. "stored" é o esp_id desde a primeira versão: o app e o servidor contam com isso
    void onValidateData(){
        auto& storage = device->sensors.alcohol.storage;
        storage.update();

        String deadline = storage.calibration_date.toString();
        deadline.replace(' ', 'T');   // o new Date() do app lê "AAAA-MM-DDTHH:MM:SS" em qualquer celular

        Json<256> info;
        info.data["current"]  = storage.id.get();
        info.data["stored"]   = device->settings.template get<String>("esp_id");
        info.data["deadline"] = (deadline == "null") ? String() : deadline;
        device->server.send(info.toString().c_str());
    }

    void getAll(){
        String response = device->settings.params.toString();
        device->server.send(response.c_str());
    }

    void status(){
        device->server.send(lang.ok.get());
    }
};


#endif