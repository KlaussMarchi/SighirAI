#ifndef HEATER_H
#define HEATER_H
#include <Arduino.h>
#include "../../../../utils/listener/index.h"
#include "../../../../utils/time/index.h"


template <typename Parent> class Heater{
  private:
    const int pin = 0;  
    Parent* device;

  public:
    unsigned long lastUpdate;
    bool active = false;
    
    Heater(Parent* dev):
        device(dev){}

    void setup(){
        lastUpdate = Time::get();
        pinMode(pin, OUTPUT);
        set(true);
    }

    void handle(){
        static Listener timer = Listener(1000);
        static const int timeout   = 10*60*1000;
        static const int long_stop = 24*60*60*1000;

        if(!timer.ready())
            return;

        if(Time::get() - device->startProg < timeout)
            return set(true);

        if(device->display.on)
            return set(true);

        if(device->vehicle.driving)
            return set(true);

        if(Time::get() - device->vehicle.ignition.getTime() < 10*60*1000)
            return set(true);

        if(Time::get() - device->vehicle.ignition.getTime() > long_stop)
            return setDuty(15, 60);

        return setDuty(5, 2);
    }
    
    void set(const bool value){
        if(active == value)
            return;

        digitalWrite(pin, value ? LOW : HIGH);
        lastUpdate = Time::get();

        Serial.println("heater "  + String(value ? "ON" : "OFF"));
        active = value;
    }

    void setDuty(const int on, const int off){
        const int onTime  = on  * (60*1000);
        const int timeOff = off * (60*1000);
        
        if(active && Time::get() - lastUpdate > onTime)
            return set(!active);
        
        if(!active && Time::get() - lastUpdate > timeOff)
            return set(!active);
    }

    String toString(){
        return (active ? "ligado por " : "desligado por ") + formatTimeString(Time::get() - lastUpdate);
    }
};


#endif