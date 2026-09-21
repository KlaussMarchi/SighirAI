#ifndef VEHICLE_H
#define VEHICLE_H
#include "../../device/lang/index.h"
#include <Arduino.h>
#include "driver/index.h"
#include "ignition/index.h"
#include "maneuver/index.h"
#include "valet/index.h"
#include "camera/index.h"
#include "../../utils/time/index.h"


template <typename Parent> class Vehicle{
  private:
    Parent* device;
    
  public:
    Ignition ignition; 
    Driver<Parent> driver;
    ManeuverTime<Parent> maneuver;
    Valet<Parent> valet;
    Camera<Parent> camera;

    unsigned long unblockedTime;
    const int relay = 2;
    bool driving  = false;
    bool blocked  = true;
    bool turnedON = false;
    bool turnedOFF = false;
    byte type = TRUCK_TYPE;

    Vehicle(Parent* dev):
        device(dev),
        driver(dev),
        maneuver(dev),
        valet(dev),
        camera(dev){}

    void setup(){
        type    = device->settings.template get<byte>("vehicle_type");
        blocked = true;
        maneuver.setup();
        valet.setup();
        camera.setup();

        ignition.set(false);
        ignition.reset();
    }

    void block(){
        device->test.postpone.active = false;
        maneuver.active = false;
        unblockedTime   = 0;
        blocked = true;
        driving = false;

        device->display.interface.msg(MSG_RED, lang.vehicleLocked.get());
        device->display.sound.badBeep();
        
        if(device->telemetry.type == SUNTECH_TEL)
            device->telemetry.suntech.block();

        if(device->telemetry.type == ENTRACK_TEL)
            device->telemetry.entrack.block();

        digitalWrite(relay, LOW);
        device->await(400);

        device->telemetry.event("$ETBL020000!");
        device->await(400);
        
        device->telemetry.event("$ETEV02!");
        device->await(400);
    }

    void unblock(){
        unblockedTime   = Time::get();
        maneuver.active = false;
        blocked = false;
        
        device->display.interface.msg(MSG_GREEN, lang.vehicleUnlocked.get());
        device->display.sound.goodBeep();

        if(device->telemetry.type == SUNTECH_TEL)
            device->telemetry.suntech.unblock();

        if(device->telemetry.type == ENTRACK_TEL)
            device->telemetry.entrack.unblock();

        digitalWrite(relay, LOW);
        device->await(400);

        device->telemetry.event("$ETBL010000!");
        device->await(400);
        
        device->telemetry.event("$ETEV01!");
        device->await(400);
    }
    
    void update(){
        maneuver.update();
    }

    void handle(){
        maneuver.handle();
    }

    void forceDriving(const bool state){
        if(state){
            device->telemetry.event("ON");
            blocked = false;
            driving = true;
            turnedOFF = false;
            turnedON  = false;
            ignition.set(true);
            return;
        }

        device->telemetry.event("OFF");
        blocked = true;
        driving = false;
        turnedOFF = false;
        turnedON  = false;
        ignition.set(false);   
    }

    void reset(){
        turnedOFF = false;
        turnedON  = false;
        ignition.changed = false;
    }
};

#endif