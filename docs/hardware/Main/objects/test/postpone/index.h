#ifndef POSTPONE_H
#define POSTPONE_H
#include "../../../device/lang/index.h"
#include <Arduino.h>


template <typename Parent> class Postpone{
  private:
    Parent* device;

  public:
    unsigned long startTime;
    bool active;
    int max_tries;
    int index;
    int timeout;

    Postpone(Parent* dev):
        device(dev){}

    void setup(){
        max_tries = device->settings.template get<int>("max_postpone");
        
        if(max_tries == 0 && device->settings.isEnabled("enable_random"))
            max_tries = 1;
    }

    int getTimeout(){
        const char* key = device->test.randomic.active ? "rand_ppn_time" : "postpone_time";
        return device->settings.template get<int>(key)*60*1000;
    }

    bool start(){
        device->vehicle.unblock();
        device->vehicle.forceDriving(true);

        device->display.sound.disable();
        index  = (index + 1);
        active = true;

        device->display.interface.msg(MSG_BLACK, lang.testPostponed.get());
        device->display.interface.font.reset();
        
        timeout     = getTimeout();
        int minutes = (timeout/60.0/1000.0);
        device->telemetry.event(device->test.randomic.active ? "$ETEV34!" : "$ETEV15!");
        
        device->display.interface.centeredText("\n\n" + String(index) + "/" + String(max_tries) + String(lang.foreng.get()) + String(minutes) + " min");
        device->await(3000);
        
        device->display.interface.msg(MSG_BLACK, lang.tapToStart.get());
        device->display.interface.font.reset();
        startTime = Time::get();
        update();

        while(!ready()){
            device->telemetry.handle();
            device->sensors.warm();

            if(device->display.touch.centerClick())
                return true;

            if(device->vehicle.ignition.off && Time::get() - startTime > 7000)
                {device->vehicle.block(); break;}
        }

        return false;
    }

    bool ready(){
        static Listener timer = Listener(45000);

        if(Time::get() - startTime > timeout)
            return true;

        if(!timer.ready())
            return false;

        update();
        return false;
    }

    void update(){
        static auto& display = device->display;
        static const int buttonX = display.width  * 0.48;
        static const int buttonY = display.height * 0.75;
        static const int buttonWidth  = display.height * 0.08;
        static const int buttonHeight = 25;
        
        display.lcd.fillRect(0, display.height*0.7, display.width, display.height, TFT_BLACK);
        display.interface.centeredText(Time::getLeft(startTime, timeout), TFT_WHITE, display.height*0.7);
    }

    bool allowed(){
        return (index < max_tries);
    }

    void reset(){
        index  = 0;
        active = false;
    }
};

#endif