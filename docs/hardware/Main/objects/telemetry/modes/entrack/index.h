#ifndef ENTRACK_H
#define ENTRACK_H
#include "../../../../device/lang/index.h"
#include <Arduino.h>
#include "../../../../globals/constants.h"
#include "../../../../utils/listener/index.h"
#include "../../../../utils/array/index.h"


template <typename Parent> class Entrack{
  private:
    Parent* device;

  public:
    unsigned long lastAck;
    bool active = false;
    Array<4> states;
    Text<16> id;
    
    Entrack(Parent* dev): 
        device(dev){}

    void setup(){   
        device->display.interface.msg(MSG_BLACK, lang.entrackStarted.get());
        device->display.interface.centeredText(lang.checkingComm.get(), TFT_RED, device->display.height*0.65);
        device->await(1000);
        
        if(device->telemetry.serial.expect("AT+QACC?", lang.ok.get(), 20000))
            active = true;
        
        if(active && device->telemetry.serial.expect("AT+ID?", "ID:", 5000))
            id = getID();
        
        if(!active){
            device->display.interface.msg(MSG_RED, lang.commNotFound.get());
            device->display.sound.badBeep();
            return device->await(1500);
        }

        device->display.interface.msg(MSG_BLACK, lang.entrackConfigured.get());
        device->await(500);
        
        device->display.interface.centeredText(id.get(), TFT_RED, device->display.height*0.65);
        device->await(500);

        device->telemetry.serial.send("AT+ASSISTMASK0900=2");
        device->await(500);

        device->telemetry.serial.send("AT+LOG=5");
        device->await(500);
        
        device->telemetry.serial.send("AT+RELAYMODE=1");
        device->await(500);
    }
    
    void request(){
        static Listener timer = Listener(2000);

        if(timer.ready())
            device->telemetry.serial.send("AT+QACC?");
    }

    void check(){
        if(!device->telemetry.serial.available)
            return;

        auto& command    = device->telemetry.serial.command;
        const int length = command.length();
        active = true;
        
        if(command.contains("+QACC:high"))
            states.append(1.0);

        if(command.contains("+QACC:low"))
            states.append(0.0);

        states.update();

        if(states.mean > 0.75)
            device->vehicle.ignition.set(true);

        if(states.mean < 0.15)
            device->vehicle.ignition.set(false);
    }

    void handle(){
        static auto& vehicle  = device->vehicle;
        static auto& ignition = vehicle.ignition;
        
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

    void block(){
        device->telemetry.event("AT+GPIOVALUE=0,1");
    }

    void unblock(){
        device->telemetry.event("AT+GPIOVALUE=0,0");
    }

    String getID() {
        auto& command = device->telemetry.serial.command;
        int start = command.indexOf("ID:");
        
        if(start == -1) 
            return "";
        
        int end = command.indexOf(lang.ok.get(), start + 3);
        
        if(end == -1)
            end = command.length();

        auto newID = command.substring(start + 3, end);
        newID.strip();
        return newID.toString();
    }
};

#endif 

