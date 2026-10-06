#ifndef CALIBRATION_H
#define CALIBRATION_H
#include "../../../../device/lang/index.h"
#include <Arduino.h>
#include "../../../../globals/constants.h"
#include "../../../../globals/functions.h"
#include "../../../../utils/listener/index.h"
#include "../../../../utils/array/index.h"
#include "../../../../utils/time/index.h"


template <typename Parent> class Calibration{
  private:
    Listener toleranceTimer = Listener(20000);
    Parent* device;

  public:
    Array<20> data;
    unsigned long lastUpdate;
    bool debug  = false;
    bool done   = false;
    bool bypass = false;
    bool had_to_wait = false;
    int percentage;
    int lastPercent;
    int newZero;

    Calibration(Parent* dev):
        device(dev){}

    void setup(){
        reset();
    }

    void handle(){
        static Listener timer = Listener(500);
        device->sensors.alcohol.heater.handle();
        
        if(!timer.ready() || device->display.interface.menu.active)
            return;

        if(done && device->test.active)
            return;

        if(bypass || debug)
            {done = true; return;}
        
        int analog = device->sensors.alcohol.get();
        data.append(analog);
        data.update();
        
        if((data.mean > MIN_ANALOG && data.rel < 0.15) || (data.mean > 20000))
            newZero = device->display.on ? data.mean : (data.mean - 1500);

        percentage = processPercent();
        stateUpdate();
    }
    
    int processPercent(){
        if(data.mean > 0.98*device->sensors.alcohol.storage.zero)
            return 100;
    
        if(data.mean > 0.98*newZero && newZero > MIN_ANALOG)
            return 100;
        
        return getPercent(data.mean);
    }
    
    void stateUpdate(){
        const bool calibrated = (data.mean > 20000 || (newZero > MIN_ANALOG) && (percentage == 100) && (data.rel < 0.20));
        
        if(!ready()){
            done = false;
            return;
        }
        
        if(calibrated){
            if(!done)
                Serial.println("sensor calibrado!");
            
            toleranceTimer.reset();
            done = true;
        }

        if(!calibrated && done){
            if(!toleranceTimer.ready())
                return;

            Serial.println("sensor descalibrado");
            toleranceTimer.reset();
            done = false;
        }
    }

    int getPercent(const int analog){
        const float mgl = device->sensors.alcohol.analyze(analog);
        return mapFloat(mgl, 0.5, 0.0, 5.0, 100.0);
    }

    void reset(){
        toleranceTimer.reset();
        lastUpdate = Time::get();
        had_to_wait = false;
        done = false;
        newZero = 0;
        lastPercent = -1;
        data.reset();
    }

    void setDebug(bool value){
        static bool aux_sens_debug = device->sensors.alcohol.debug;
        debug = value;

        if(debug){
            device->sensors.pressure.debug = true;
            device->sensors.alcohol.debug  = true;
            device->test.pass.enabled = false;
            bypass = true;
            return;
        }

        device->sensors.pressure.debug = false;
        device->sensors.alcohol.debug  = aux_sens_debug;
        device->test.pass.enabled = true;
        bypass = false;
    }
    
    bool prepare(){
        const int analog  = device->sensors.alcohol.sample(700);
        const bool ranged = (analog > MIN_ANALOG) && (newZero > MIN_ANALOG);
        const bool valid  = (analog > newZero) || (abs(newZero - analog) < 2500);
        
        if(!debug && (!ranged || !valid))
            {reset(); return false;}

        newZero = analog;   
        return true;
    }

    bool load(){
        if(done)
            return false;
        
        reset();
        if(!ready())
            return awaitScreen();

        auto& loader   = device->display.interface.loading;
        auto& postpone = device->test.postpone;
        auto& display  = device->display;

        const char* msg = device->test.had_alcohol        ? lang.lastAlcoholTest.get() :
                          device->test.postpone.allowed() ? lang.touchToPostpone.get() : lang.postponeLimitExceeded.get();

        loader.start(lang.calibratingSensor.get(), msg);
        const unsigned long startTime = Time::get();
        unsigned long stableTime;
        
        loader.step(0, false);
        int timeout = (7*60*1000);
        int percent = -1;

        while(!done){
            device->server.handle();
            handle();

            if(percentage > percent){
                device->sensors.dht.handle();
                Text<15> msg = String((int) data.mean) + " - " + device->sensors.dht.temperature.toString();
                percent      = percentage;

                if(percentage == 100){
                    stableTime = Time::get();
                    loader.title.set("Estabilizando");
                    loader.draw();
                }
                
                display.interface.label(msg.get(), display.width*.1, display.height*.07, display.width*.8, display.height*.05, TFT_RED, TFT_BLACK);
                loader.step(percent, false);
            }

            if(Time::get() - startTime > timeout){
                postpone.index = (postpone.index > 0) ? (postpone.index - 1) : postpone.index;
                display.interface.msg(MSG_RED, lang.calibrationFrozen.get());
                display.sound.set(BUZZER_BAD_SOUND, 6000);
                device->await(3000);
                display.interface.msg(MSG_BLACK, lang.postponingTest.get());
                device->await(4000);
                return true;
            }

            if(percentage == 100 && Time::get() - stableTime > 12000)
                done = true;

            if(!device->test.had_alcohol && device->test.postpone.allowed() && device->display.touch.screenClick(true))
                return true;
        }

        return false;
    }
    
    long getRefreshTime(){
        const long value = ((long) getWarmTime()) - ((long) (Time::get() - device->test.endRequestTime));
        return (value <= 0) ? 0 : value;
    }

    int getWarmTime(){
        if(device->test.last_analog < 7000)
            return 5*60*1000;

        if(device->test.last_analog < 15000)
            return 4*60*1000;

        if(device->test.last_analog < 17000)
            return 3*60*1000;
        
        return 2*60*1000;
    }

    bool ready(){
        auto& test = device->test;
        
        if(!test.had_alcohol)
            return true;

        if(getRefreshTime() == 0)
            return true;

        return false;
    }

    bool awaitScreen(){
        auto& loader   = device->display.interface.loading;
        auto& postpone = device->test.postpone;
        auto& display  = device->display;

        loader.start(lang.heatingRequired.get(), device->test.postpone.allowed() ? lang.touchToPostpone.get() : lang.postponeLimitExceeded.get());    
        display.interface.centeredText(lang.lastAlcoholTest.get() + formatTimeString(getRefreshTime()), TFT_RED, display.height*.07);
         
        const unsigned long startTime = Time::get();
        loader.step(0, false);
        Listener timer = Listener(1000);
        int percent    = 0;
        
        while(percent < 100){
            device->server.handle();
            handle();

            if(device->test.postpone.allowed() && device->display.touch.screenClick(true))
                return true;

            if(!timer.ready())
                continue;

            percent = mapFloat(getRefreshTime(), getWarmTime(), 0, 0, 100); 
            loader.step(percent, false);
        }
        
        had_to_wait = true;
        return done ? false : load();
    }
};

#endif