#ifndef BLOWS_H
#define BLOWS_H
#include "../../../../../device/lang/index.h"

#define REMINDER_ALERT 1750
#define WARNING_ALERT  2000
#define CAUTION_ALERT  2250
#define LAST_ALERT     2400
#define DANGER_ALERT   2500


template <typename Parent> class Blows{
  private:
    Parent* device;

  public:
    Text<25> info;
    bool deprecated;
    int value;
    
    Blows(Parent* dev):
        device(dev){}
    
    void update(){
        auto& storage = device->sensors.alcohol.storage;
        
        if(device->sensors.alcohol.debug)
            return;

        info.set(storage.read(210, 220));
        info.set(info.substring(info.indexOf('$')+1, info.indexOf('!')).get());
        value      = info.toInt();
        deprecated = (value > DANGER_ALERT);
    }
    
    void increment(){
        auto& storage = device->sensors.alcohol.storage;

        if(device->sensors.alcohol.debug)
            return;

        value = value + 1;
        storage.write(" $" + String(value) + "!", 210);
    }

    void check(){
        deprecated = (value > DANGER_ALERT);

        if(value < REMINDER_ALERT)
            return;

        if(value > REMINDER_ALERT && value < WARNING_ALERT)
            reminder();

        if(value > WARNING_ALERT && value < CAUTION_ALERT)
            warning();

        if(value > CAUTION_ALERT && value < LAST_ALERT)
            caution();

        if(value > LAST_ALERT && !deprecated)
            lastwarning();

        if(deprecated)
            danger();
        
        device->display.lcd.clear();
        device->test.screens.start();
    }

    void reminder(){
        device->display.interface.msg(MSG_BLACK, lang.sensorChangeReminder.get());
        drawBlows(TFT_WHITE);
        device->server.wait(2000);
    }

    void warning(){
        device->display.interface.msg(MSG_WHITE, lang.attentionSensorChange.get());
        drawBlows(TFT_BLACK);
        device->server.wait(4000);
    }

    void caution(){
        device->display.interface.msg(MSG_ORANGE, lang.sensorExpiringAlert.get());
        drawBlows(TFT_WHITE);

        device->telemetry.event("$ETEV20!");
        device->display.sound.twoBeep();
        device->server.wait(6000);
    }

    void lastwarning(){
        device->display.interface.msg(MSG_RED, lang.sensorAlmostExpired.get());
        device->telemetry.event("$ETEV20!");
        drawBlows(TFT_WHITE);
        device->display.sound.badBeep();
        device->server.wait(8000);
    }

    void danger(){
        device->display.interface.msg(MSG_RED, lang.sensorExpired.get());
        device->telemetry.event("$ETEV21!");
        drawBlows(TFT_WHITE);
        device->display.sound.set(BUZZER_BAD_SOUND);
        device->server.wait(10000);
        device->display.sound.disable();
        device->server.wait(30000);
        device->display.lcd.clear();
    }
    
    void drawBlows(int color=TFT_WHITE){
        device->display.interface.centeredText(lang.totalBlows.get() + String(value) + "/2500", color, device->display.height*0.7);
    }
};

#endif
