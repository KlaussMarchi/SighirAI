#ifndef MANEUVER_TIME_H
#define MANEUVER_TIME_H
#include "../../../device/lang/index.h"
#include <Arduino.h>
#include <LovyanGFX.hpp>


template <typename Parent> class ManeuverTime{
  private:
    Listener updateWindowTime = Listener(10000);
    Parent* device;

  public:
    unsigned long lastUpdate;
    bool enabled;
    bool active;
    int timeout;
    
    ManeuverTime(Parent* dev):
        device(dev){}
    
    void setup(){
        timeout = device->settings.template get<float>("maneuver_time")*60*1000;
        enabled = true;

        if(device->telemetry.type == MIX_TEL)
            timeout = 5*60*1000;
    }

    void draw(){
        auto& display = device->display;
        display.interface.menu.active = false;
        display.interface.msg(MSG_BLACK, lang.maneuverTime.get());
        display.interface.centeredText(lang.vehicleUnlocked2.get(), TFT_WHITE, display.height*0.55);
        display.interface.font.reset();

        const char* left  = Time::getLeft(device->vehicle.ignition.startTime, timeout);
        const int buttonX = display.width  * 0.48;
        const int buttonY = display.height * 0.75;
        const int buttonWidth  = display.height * 0.08;
        const int buttonHeight = 25;
        
        display.lcd.fillRect(0, display.height*0.7, display.width, display.height, TFT_BLACK);
        display.interface.centeredText(left, TFT_RED, display.height*0.7);
    }


    void set(const bool state){
        active = state;
        lastUpdate = Time::get();
    }
    
    void start(){
        set(true);

        if(timeout == 0)
            return;

        device->vehicle.ignition.startTime = Time::get();
        device->telemetry.event("$ETEV17!");
        
        draw();
        updateWindowTime.reset();
    }

    void handle(){
        auto& vehicle = device->vehicle;

        if(vehicle.blocked || vehicle.driving)
            set(false);

        if(active && !device->display.interface.menu.active && updateWindowTime.ready())
            draw();

        if(!enabled || device->test.pass.required() || device->test.postpone.active)
            return;
        
        if(!active || vehicle.driving || vehicle.ignition.on)
            return;

        if(vehicle.ignition.getTime() > timeout){
            set(false);
            end();
            vehicle.block();
            device->display.turnOFF();
        }
    }

    void update(){
        auto& vehicle  = device->vehicle;
        auto& ignition = device->vehicle.ignition;

        if(!enabled)
            return;

        if(device->test.pass.required() || device->test.postpone.active)
            return;

        if(active && ignition.changed && ignition.on)
            vehicle.unblock();

        if(drivingChanged() && vehicle.driving)
            vehicleON();
        
        if(ignition.changed && ignition.off && timeout > 0)
            vehicleOFF();

        if(ignition.changed && ignition.off && !vehicle.blocked)
            start();
    }

    bool drivingChanged(){
        static bool previous = device->vehicle.driving;

        if(previous == device->vehicle.driving)
            return false;

        previous = device->vehicle.driving;
        return true;
    }

    void vehicleON(){
        device->display.interface.msg(MSG_WHITE, lang.vehicleOn.get());
        device->await(3000);
        device->display.turnOFF();
    }

    void vehicleOFF(){
        auto& ignition = device->vehicle.ignition;

        device->display.interface.msg(MSG_BLACK, lang.vehicleOff.get());
        device->await(3000);

        if(!ignition.changed || ignition.on || device->vehicle.blocked)
            device->display.turnOFF();
    }
    
    void end(){
        device->display.interface.msg(MSG_BLACK, lang.timeOut.get());
        device->display.sound.set(BUZZER_BLOW, 1500);
        device->telemetry.event("$ETEV18!");
        device->await(4000);
    }
};

#endif 