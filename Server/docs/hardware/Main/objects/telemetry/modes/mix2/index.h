#ifndef MIX2_H
#define MIX2_H
#include "../../../../device/lang/index.h"
#include <Arduino.h>
#include "../../../../globals/constants.h"
#include "../../../../globals/functions.h"
#include "../../../../utils/listener/index.h"


template <typename Parent> class MIX2{
  private:
    Parent* device;
    
  public:
    bool key;

    MIX2(Parent* dev):
        device(dev){}

    void setup(){
        device->display.interface.msg(MSG_BLACK, lang.mix2Started.get());
        device->display.interface.centeredText(lang.checkingComm.get(), TFT_RED, device->display.height*0.65);
        device->await(2500);
    }

    void request(){
        static Listener timer = Listener(5*60*1000);
        
        if(timer.ready())
            device->telemetry.serial.send("$ETACK!");
    }

    void check(){
        if(!device->telemetry.serial.available)
            return;
        
        if(device->telemetry.serial.command.length() > 100)
            return;
        
        if(device->telemetry.serial.command.contains("ETAT01")){
            device->telemetry.response.set("$ETATACK!");
            device->vehicle.ignition.set(true);
            return;
        }

        if(device->vehicle.type == CAR_TYPE && device->telemetry.serial.command.contains("ETEV31")){
            device->telemetry.response.set("$ETATACK!");
            device->vehicle.ignition.set(true);
            return;
        }

        if(device->telemetry.serial.command.contains("ETEV04")){
            device->telemetry.response.set("$ETEVACK!");
            device->vehicle.ignition.set(false);
            return;
        }

        if(device->telemetry.serial.command.contains("ETEV03")){
            if(device->vehicle.type == TRUCK_TYPE)
                device->vehicle.driving = true;
            
            device->telemetry.response.set("$ETEVACK!");
            return;
        }
    }

    void handle(){
        static auto& vehicle  = device->vehicle;
        static auto& ignition = vehicle.ignition;
        
        if(ignition.changed && ignition.on){
            vehicle.turnedON = true;

            if(vehicle.blocked && !vehicle.driving)
                device->test.start();

            if(vehicle.type == CAR_TYPE)
                vehicle.driving = !vehicle.blocked;
        }
        
        if(ignition.changed && ignition.off && vehicle.driving){
            vehicle.turnedOFF = true;
            vehicle.driving   = false;
        }

        if(!vehicle.driving && ignition.on && !vehicle.blocked && timeOut()){
            device->display.interface.msg(MSG_WHITE, lang.timeOut.get());
            device->await(3000);
            device->vehicle.block();
            device->display.turnOFF();
        }
        
        vehicle.update();
        vehicle.reset();
        ignition.reset();
    }

    bool timeOut(){
        const bool ignition_timeout = (device->vehicle.ignition.getTime()   > 70000);
        const bool test_timeout     = (Time::get() - device->test.lastTime) > 70000; 
        return (ignition_timeout && test_timeout);
    }
};

#endif