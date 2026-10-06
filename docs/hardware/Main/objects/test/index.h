#ifndef TEST_H
#define TEST_H
#include "../../device/lang/index.h"
#include <Arduino.h>
#include "postpone/index.h"
#include "../../globals/constants.h"
#include "../../utils/time/index.h"
#include "screens/index.h"
#include "randomic/index.h"
#include "model/index.h"
#include "pass/index.h"


template <typename Parent> class Test{
  private:
    Parent* device;

  public:
    TestScreens<Parent> screens;
    Randomic<Parent> randomic;
    Postpone<Parent> postpone;
    Pass<Parent> pass;
    AlcoholModel model;

    unsigned long lastTime, startRequestTime, endRequestTime;
    bool active;
    bool had_alcohol;
    int   last_analog;
    float last_alcohol;
    int MIN_TIME;
    bool alcohol_debug;
    bool done;
    byte status;
    
    Test(Parent* dev):
        device(dev),
        postpone(dev),
        screens(dev),
        randomic(dev),
        pass(dev){}
    
    void setup(){
        MIN_TIME = (1.25*HEAT_MIN_TIME) + device->settings.template get<int>("camera")*1000;
        postpone.setup();
        randomic.setup();
    }

    void handle(){
        randomic.handle();
    }
    
    void reset(){
        active   = false;
        lastTime = Time::get(); 
    }

    void start(bool turbo=false){
        device->display.interface.menu.reset();
        device->display.brightness.update(120);
        device->vehicle.ignition.reset();
        device->sensors.alcohol.heater.set(true);
        startRequestTime = Time::get();
        pass.liberated = false;
        active = true;

        screens.start();
        device->sensors.alcohol.check();
        device->sensors.alcohol.storage.blows.check();
        screens.start();
        screens.beep();

        if(!turbo && startLoadings())
            status = TEST_POSTPONED;
        else
            status = process(turbo);
        
        device->display.brightness.reset();
        device->await(100);

        if(device->sensors.alcohol.calibration.debug)
            return;

        if(status == TEST_OK || status == TEST_ALCOHOL){
            device->telemetry.event(randomic.active ? "$ETEV25!" : "$ETEV16!");
            endRequestTime = Time::get();
        }
        
        if(status == TEST_CALIBRATION_FAIL){
            device->sensors.alcohol.calibration.reset();
            screens.calibrationFail();
            return start(true);
        }

        if(status == TEST_POSTPONED){
            bool clicked = postpone.start();
            
            if(device->vehicle.ignition.on)
                return start(clicked);
        }

        if(status == TEST_OK){
            device->sensors.alcohol.storage.blows.increment();
            device->vehicle.unblock();
            postpone.reset();
            pass.reset();
        }
        
        if(status == TEST_ALCOHOL && !device->vehicle.driving && pass.enabled){
            device->vehicle.block();
            pass.start();

            if(pass.required())
                device->vehicle.block();
        }

        if((status == TEST_ALCOHOL || status == TEST_BLOW_TIMEOUT) && device->vehicle.driving && !pass.liberated){
            device->telemetry.event("$ETEV35!");
            alertDriver();
        }
        
        device->display.turnOFF();
        active = false;
    }
    
    bool startLoadings(){
        if(postpone.allowed() && screens.waitUser())
            return true;

        device->company.sighir();
        device->await(1000);

        device->company.logo();
        device->await(1000);
        return false;
    }

    byte process(bool turbo){
        if(!turbo && device->vehicle.camera.load())
            return TEST_POSTPONED;

        if(device->sensors.alcohol.calibration.load())
            return TEST_POSTPONED;

        if(!device->sensors.alcohol.calibration.prepare())
            return TEST_CALIBRATION_FAIL;

        if(!turbo || device->sensors.alcohol.calibration.had_to_wait)
            screens.input();
        
        if(!compute())
            return TEST_BLOW_TIMEOUT;
        
        int analog  = model.min;
        float mgl   = device->sensors.alcohol.analyze(analog);
        
        bool detected = device->sensors.alcohol.storage.has_coefs ? (model.result && mgl > 0.020) : model.result;
        had_alcohol   = (detected || alcohol_debug);

        if(!had_alcohol)
            mgl = 0.00;

        if(had_alcohol || model.result)
            device->sensors.alcohol.calibration.data.reset();
        
        last_alcohol = mgl;
        last_analog  = analog;

        show();
        reset();
        return (had_alcohol ? TEST_ALCOHOL : TEST_OK);
    }
    
    void show(){
        auto& display = device->display;

        Text<10> mgl = String(last_alcohol, 3);
        display.interface.msg(MSG_BLACK, mgl.toString() + " mg/L");
        display.interface.label(String(last_analog), display.width*.1, display.height*.85, display.width*.8, 30, TFT_RED, TFT_BLACK, false);
        mgl.remove('.');
        mgl.remove(' ');
        device->await(1500);

        device->telemetry.event(had_alcohol ? String("$ETEV30" + mgl.toString() + "!") : "$ETEV29!");
        device->await(1500);
        //Serial.println("analog: " + String(last_analog));
        //Serial.println("mgl:    " + String(last_alcohol));
        //Serial.println("newZero:  " + String(model.data.get(0)));
        //Serial.println();
        
        if(!had_alcohol)
            return;

        display.interface.msg(MSG_RED, lang.alcoholDetected.get());
        display.sound.badBeep();
    }

    bool compute(){;
        model.init(device->sensors.alcohol.calibration.newZero);
        device->display.brightness.update(50);
        device->sensors.pressure.tare(true);
        screens.blow();

        // ASSOPRE (INÍCIO)
        if(!device->sensors.pressure.getFirstBreath()){
            device->display.interface.msg(MSG_RED, lang.noBlow.get());
            device->await(1000);

            device->telemetry.event("$ETEV11!");
            device->await(1000);

            if(device->display.interface.inputs.boolean(lang.tryAgain.get()))
                return compute();

            if(randomic.active)
                device->telemetry.event("$ETEV33!");

            device->display.sound.badBeep();
            device->display.brightness.reset();
            return false;
        }
        
        unsigned long startTime = Time::get();
        int blowTime = 0;
        
        // ASSOPRE (CONTINUANDO)
        while(blowTime < 3000){
            model.add(device->sensors.alcohol.smooth());
            device->display.sound.handleBeep(75);

            const bool blowing = device->sensors.pressure.blower.get();
            blowTime = (Time::get() - startTime);

            if(blowing || blowTime > 1800)
                continue;
            
            device->display.interface.msg(MSG_RED, lang.noBlow.get());
            device->display.sound.badBeep();
            device->telemetry.event("$NOBLOW!"); 
            device->sensors.pressure.warm(2000);
            device->display.brightness.reset();
            return compute();
        }
        
        // ANALISANDO (20 SEGUNDOS)
        device->telemetry.event("$ETEV05!");
        device->display.sound.disable();

        auto& loader   = device->display.interface.loading; 
        Listener timer = Listener(300);

        screens.inmetro();
        loader.start(lang.analyzing.get(), "", 0, 25);
        
        while(true){
            model.add(device->sensors.alcohol.smooth());   
            loader.step(((model.data.index-7)/40.00f)*100.00f, false);

            if(model.done)
                break;
        }
        
        device->display.brightness.reset();
        model.update();
        device->telemetry.serial.send(model.getInfo().toString());
        return true;
    }

    unsigned long getTime(){
        if(!active)
            return 0;

        return (unsigned long) (Time::get() - lastTime);
    }

    void alertDriver(){
        screens.killdriver();
        
        while(device->vehicle.ignition.on){
            device->display.sound.handleBeep(500, BUZZER_BAD_SOUND);
            device->telemetry.handle();
            device->server.handle();
        }

        device->vehicle.block();
        device->vehicle.reset();
    }
};

#endif