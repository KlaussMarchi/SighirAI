#ifndef DIAGNOSTIC_H
#define DIAGNOSTIC_H
#include "../../device/lang/index.h"
#include "../../utils/time/index.h"


template <typename Parent> class Diagnostic{
  private:
    Parent* device;

  public:
    Diagnostic(Parent* dev):
        device(dev){}

    void start(){
        int option = device->display.interface.inputs.trichoices(lang.blowTest.get(), lang.componentsTest.get(), lang.relayTest.get());

        if(option == 0)
            return blow();

        if(option == 1)
            return components();

        if(option == 2)
            return relay();
    }
    
    void components(){
        pressure();
        temperature();
        alcohol();
    }

    void serial(){
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
        fail("ERROR");
    }

    void blow(){
        device->sensors.pressure.tare(true);
        device->await(100);
        
        device->display.interface.msg(MSG_BLACK, lang.blow.get());
        device->display.sound.set(BUZZER_BLOW, 200);
        device->display.sound.set(BUZZER_NO_SOUND, 50);
        device->display.sound.set(BUZZER_BLOW, 200);

        if(!device->sensors.pressure.getFirstBreath()){
            device->display.interface.msg(MSG_RED, lang.noBlow.get());
            device->display.sound.badBeep();
            return fail("$ERROR!");
        }
        
        const unsigned long startTime = Time::get();
        int blowTime = 0;
        
        while(blowTime < 3000){
            const bool blowing = device->sensors.pressure.blower.get();
            const int analog   = device->sensors.alcohol.smooth();
            
            device->display.sound.handleBeep();
            blowTime = (Time::get() - startTime);

            if(blowing || blowTime > 1800)
                continue;
            
            device->display.interface.msg(MSG_RED, lang.noBlow.get());
            device->display.sound.badBeep();
            device->telemetry.event("$NOBLOW!"); 
            device->sensors.pressure.warm(2000);
            device->display.brightness.reset();
            return fail("$ERROR!");
        }

        check("pressworking");
    }

    void pressure(){
        device->display.interface.msg(MSG_BLACK, lang.checkingPressure.get());
        device->await(2500);
        
        if(!device->sensors.pressure.check(2500)){
            device->display.interface.msg(MSG_RED, lang.sensorNoComm.get());
            device->display.sound.badBeep();
            return fail("$ERROR!");
        }
        
        device->display.interface.msg(MSG_WHITE, lang.sensorConnected.get());
        device->await(2500);
        check("pressworking");
    }

    void alcohol(){
        device->display.interface.msg(MSG_BLACK, lang.checkingAlcohol.get());
        device->await(2500);
        
        if(device->sensors.alcohol.failed())
            return fail("$ETEV24!");

        check("$ETEV20!");
    }

    void temperature(){
        device->display.interface.msg(MSG_BLACK, lang.checkingTemp.get());
        unsigned long startTime = Time::get();
        device->await(2500);
        
        while(Time::get() - startTime < 7000){
            device->sensors.dht.update();
            bool temp = device->sensors.dht.temperature.working;
            bool hum  = device->sensors.dht.humidity.working;
            
            if(temp && hum)
                return check("tempworking");
        }

        fail("ERROR");
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

    void fail(const char* event){
        device->display.interface.msg(MSG_RED, lang.testFailed.get());
        device->telemetry.event(event);
        device->display.sound.badBeep();
    }

    void check(const char* event){
        device->display.interface.msg(MSG_GREEN, lang.functionalState.get());
        device->telemetry.event(event);
        device->display.sound.goodBeep();
    }
};


#endif