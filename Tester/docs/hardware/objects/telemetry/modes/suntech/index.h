#ifndef SUNTECH_H
#define SUNTECH_H
#include "../../../../device/lang/index.h"
#include <Arduino.h>
#include "../../../../utils/listener/index.h"
#include "../../../../utils/text/index.h"
#include "../../../../utils/array/index.h"


template <typename Parent> class Suntech{
  private:
    Parent* device;

  public:
    Text<16> id;
    Array<4> states;
    bool active = false;
    unsigned long lastAck;
    
    Suntech(Parent* dev): 
        device(dev){}

    void setup(){
        device->display.interface.msg(MSG_BLACK, lang.suntechStarted.get());
        device->display.interface.centeredText(lang.checkingComm.get(), TFT_RED, device->display.height*0.65);
        device->await(1000);
        
        if(device->telemetry.serial.expect("SttReq", "STT;", 20000))
            active = true;

        if(!active){
            device->display.interface.msg(MSG_RED, lang.commNotFound.get());
            device->display.sound.badBeep();
            return device->await(1500);
        }

        check();
        device->display.interface.msg(MSG_BLACK, lang.suntechConfigured.get());
        device->display.interface.centeredText(id.get(), TFT_RED, device->display.height*0.65);
        device->await(3000);
    }

    void request(){
        static Listener timer = Listener(2000);

        if(timer.ready())
            device->telemetry.serial.send("SttReq");
    }

    void check(){
        if(!device->telemetry.serial.available)
            return;

        auto& command    = device->telemetry.serial.command;
        const int length = command.length();
        //device->telemetry.event(command.toString());
        
        if(length < 100)
            return;

        if(!command.contains("T;"))
            return;
        
        int start = command.indexOf("T;");
        command   = command.substring(start, start+200);
        
        update("id",  1);
        update("key", (length < 170) ? 14 : 19);      
        active = true;
        print();
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
    
    void update(const char* key, const int index){
        auto command = device->telemetry.serial.command;
        int start = 0;
        int end   = -1;

        for(int i=0; i<=index; i++){
            start = end + 1;             
            end   = command.indexOf(';', start); 

            if(end == -1)
                {end = command.length(); break;}
        }
        
        auto target = command.substring(start, end);
        
        if(target.length() == 0)
            return;

        if(strcmp(key, "id") == 0)
            return id.set(target.get());

        if(strcmp(key, "key") == 0)
            return keyUpdate(target.charAt(7) == '1');
    }

    void keyUpdate(const bool state){
        states.append((float) state);
        states.update();

        if(device->telemetry.serial.port == 1)
            return device->vehicle.ignition.set(state);

        if(states.mean > 0.90)
            return device->vehicle.ignition.set(true);

        if(states.mean < 0.10)
            return device->vehicle.ignition.set(false);
    }

    void block(){
        device->telemetry.event("CMD;" + id.toString() + ";04;01");
    }

    void unblock(){
        device->telemetry.event("CMD;" + id.toString() + ";04;02");
    }
    
    void print(){
        Serial.println("id: " + id.toString() + " | " + "key: " + String(device->vehicle.ignition.on));
    }
};

#endif 
