#ifndef DEVICE_H
#define DEVICE_H
#include "../device/lang/index.h"
#include "../globals/functions.h"
#include "../globals/constants.h"

#include "../utils/array/index.h"
#include "../utils/time/index.h"
#include "../utils/json/index.h"
#include "../utils/text/index.h"
#include "../utils/listener/index.h"

#include "settings/index.h"
#include "company/index.h"
#include "tasks/index.h"

#include "../objects/telemetry/index.h"
#include "../objects/vehicle/index.h"
#include "../objects/sensors/index.h"
#include "../objects/test/index.h"
#include "../objects/display/index.h"
#include "../objects/server/index.h"
#include "../objects/diagnostic/index.h"
#include "../objects/logs/index.h"


class Device{
  public:
    unsigned long startProg = Time::get();
    const char* firmware;
    bool in_setup;
    Settings settings;
    Text<20> id;
    
    Diagnostic<Device> diagnostic;
    Telemetry<Device> telemetry;
    EspServer<Device> server;
    Vehicle<Device> vehicle;
    Sensors<Device> sensors;
    Display<Device> display;
    Company<Device> company;
    Tasks<Device> tasks;
    Test<Device> test;
    Logs<Device> logs;
    
    Device(const char* version):
        firmware(version),
        diagnostic(this),
        telemetry(this),
        vehicle(this),
        sensors(this),
        display(this),
        server(this),
        test(this),
        logs(this),
        company(this),
        tasks(this){}
    
    void setup(){
        settings.import(); 
        in_setup = true;

        tasks.checkSystem(true);      
        sensors.dht.debug = settings.isEnabled("temp_debug");
        id = settings.template get<const char*>("esp_id");
        
        Serial.print("Device Started: ");
        Serial.println(id.get());
        
        display.setup();
        company.sighir();
        await(1000);
        
        company.setup();
        logs.setup();
        telemetry.setup();
        vehicle.setup();
        
        sensors.setup();
        test.setup();
        
        tasks.checkSystem(false);
        company.showVersion();
        company.logo();
        await(3000);
        server.setup();
        
        if(server.enabled)
            server.connect(true);

        display.turnOFF();
        display.sound.twoBeep();
        in_setup = false;

        settings.params.set("reset", 0);
        settings.save();
    }

    void await(const int timeout){
        const unsigned long startTime = Time::get();
        
        while(Time::get() - startTime < timeout){
            server.handle();
            sensors.warm();
        }
    }
    
    void reset(){
        display.interface.msg(MSG_ORANGE, lang.restartingDevice.get());
        display.sound.set(BUZZER_GOOD_SOUND, 1500);
        await(1000);
        
        sensors.alcohol.heater.set(false);
        delay(500);
        ESP.restart();
    }
};

#endif