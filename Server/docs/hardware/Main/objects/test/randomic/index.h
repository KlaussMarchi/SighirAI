#ifndef RANDOMIC_H
#define RANDOMIC_H
#include "screens/index.h"
#include "travels/index.h"


template <typename Parent> class Randomic{
  private:
    Parent* device;
    RandomicScreens<Parent> screens;

  public:
    Travels<Parent> travels;
    bool active, enabled;
    bool monitoring;
    bool done = false;
    int index = 0;
    int max_tests;
    int nextTest;

    Randomic(Parent* dev):
        device(dev),
        screens(dev),
        travels(dev){}

    void setup(){
        enabled   = device->settings.isEnabled("enable_random");
        max_tests = device->settings.template get<int>("number_of_tests");
        monitoring = false;
        active     = false;
        travels.setup();
    }

    void handle(){
        static auto& vehicle = device->vehicle;

        if(!enabled || !vehicle.driving)
            return;
        
        travels.update();

        if(!done && !monitoring && travels.started)
            update();

        if(monitoring && travels.endded)
            reset();

        if(monitoring && vehicle.ignition.getTime() > nextTest)
            if(device->sensors.alcohol.calibration.done)
                start();
    }

    void update(){
        index = (index + 1);
        monitoring = true;

        if(index > max_tests){
            Serial.println("No More Randomic Tests");
            monitoring = false;
            active = false;
            done   = true;
            return;
        }

        int minTime = travels.minTime;
        int maxTime = (index < max_tests) ? (travels.mean * index/max_tests) : 0.8*travels.mean;
        nextTest = (maxTime < minTime) ? minTime : genTime(minTime, maxTime);
        Serial.println("(randomic) first test: " + String(nextTest/60/1000) + " min");
        device->vehicle.ignition.resetTime();
    }

    void start(){
        const unsigned long startTime = Time::get();
        static const int timeout = 3*60*1000;
        
        if(!device->vehicle.driving)
            return device->display.turnOFF();

        device->display.sound.volume = 255;
        device->telemetry.event("$ETEV12!");
        active = true;
        
        if(device->test.postpone.active || !device->test.postpone.allowed())
            return test();
        
        screens.alert();
        screens.bichoices(lang.startTest.get(), "Adiar");
        auto& display  = device->display;
        bool postponed = false;

        while(Time::get() - startTime < timeout){
            display.sound.handleBeep(2000, BUZZER_RND_SOUND);

            if(!display.touch.click())
                continue;
            
            if(display.touch.areaClick(0, display.height*.5, display.width, display.height))
                postponed = true;

            break;
        }
        
        if(Time::get() - startTime >= timeout || postponed){
            device->test.postpone.start();
            return start();
        }

        test();
    }
        
    void test(){
        device->display.sound.reset();
        device->display.touch.reset();
        device->test.start(true);
        device->test.postpone.reset();
        active = false;
        update();
    }

    void reset(){
        monitoring = false;
        active = false;
        done   = false;
        index = 0;
    }

    int genTime(int minVal, int maxVal){
        warmRandomSeed();
        return random(minVal, maxVal);
    }

    String toString(){
        String response = enabled ? "Ativo" : "Desativado";
        response += " - ";
        response += monitoring ? "Monitorando" : lang.notStarted.get();
        return response;
    }
};

#endif