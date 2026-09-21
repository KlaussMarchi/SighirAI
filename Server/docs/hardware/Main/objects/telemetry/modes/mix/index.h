#ifndef MIX_H
#define MIX_H
#include "../../../../device/lang/index.h"
#include <Arduino.h>
#include "../../../../utils/listener/index.h"


template <typename Parent> class MIX{
  private:
    Parent* device;
    
  public:
    bool key;

    MIX(Parent* dev):
        device(dev){}

    void setup(){
        device->display.interface.msg(MSG_BLACK, lang.mix1Started.get());
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
        
        if(device->telemetry.serial.command.contains("ETEV04")){
            device->telemetry.response.set("$ETEVACK!");
            device->vehicle.ignition.set(false);
            return;
        }
    }  

    void handle(){
        auto& vehicle  = device->vehicle;
        auto& ignition = vehicle.ignition;
        
        if(ignition.changed && ignition.on){
            vehicle.turnedON = true;

            if(vehicle.blocked && !vehicle.driving)
                device->test.start();

            vehicle.driving = !vehicle.blocked;
        }
        
        if(ignition.changed && ignition.off && vehicle.driving){
            vehicle.turnedOFF = true;
            vehicle.driving   = false;
        }
        
        vehicle.update();
        vehicle.reset();
    }
};

#endif