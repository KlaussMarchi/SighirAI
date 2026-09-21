#ifndef VALET_H
#define VALET_H 
#include "../../../device/lang/index.h"


template<typename Parent> class Valet{
  private:
    Parent* device;

  public:
    unsigned long lastUpdate;
    bool enabled = false;
    bool active  = false;

    Valet(Parent* dev):
        device(dev){}

    void setup(){
        enabled = device->settings.isEnabled("valet");
    }

    void set(const bool state){
        active = state;
        lastUpdate = Time::get();
    }
    
    void start(){
        set(!active);
        device->display.interface.msg(MSG_BLACK, active ? lang.valetEnabled.get() : lang.valetDisabled.get());
        device->telemetry.event(active ? "$ETEV22!" : "!ETEV23$");
        device->await(3000);

        if(active)
            return device->display.turnOFF(); 

        if(device->vehicle.ignition.on)
            return device->test.start();

        device->vehicle.driving = false;
        device->vehicle.blocked = true;
        device->display.turnOFF();
    }

    void handle(){
        device->telemetry.serial.listen();
        device->telemetry.handleProtocol();
        device->telemetry.handleRequest();

        if(device->vehicle.ignition.changed && device->vehicle.ignition.on)
            unblock();

        device->telemetry.serial.reset();
        device->vehicle.reset();
    }

    void unblock(){
        device->display.interface.msg(MSG_WHITE, lang.waitGreenScreen.get());
        device->await(3000);
        device->telemetry.event("$ETEV32!");

        device->vehicle.unblock();
        device->display.interface.msg(MSG_WHITE, lang.startVehicle.get());
        
        device->await(5000);
        device->display.turnOFF();
    }

    void drawButton(){
        auto& display = device->display;
        display.interface.label(active ? lang.disableValet.get() : lang.enableValet.get(), display.width*.15, display.height*.08, display.width*0.7, 45, TFT_BLACK, LIGHT_GREY);
    }
};

#endif