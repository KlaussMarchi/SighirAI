#ifndef ALCOHOL_SENSOR_H
#define ALCOHOL_SENSOR_H
#include <Wire.h>
#include <Arduino.h>
#include <Adafruit_ADS1X15.h>

#include "../../../utils/listener/index.h"
#include "../../../utils/time/index.h"
#include "heater/index.h"
#include "eeprom/index.h"
#include "calibration/index.h"
#include "storage/index.h"
#include "screens/index.h"


template <typename Parent> class AlcoholSensor{
  private:
    Parent* device;

  public:
    bool debug;
    bool bypass;
    const int pin = 1;
    const int sda = 18;
    const int scl = 19;

    StorageScreens<Parent> screens;
    Calibration<Parent> calibration;
    Storage<Parent> storage;
    Heater<Parent> heater;

    Adafruit_ADS1115 ads;
    EEPROM eeprom;
    byte ERROR_STATUS;
    
    AlcoholSensor(Parent* dev):
        device(dev),
        calibration(dev),
        heater(dev),
        screens(dev),
        storage(dev){}
    
    void setup(){
        Wire.begin(sda, scl);
        ads.begin(storage.sensor_addr);
        check(true);
        
        heater.setup();
        storage.setup();
        calibration.setup();
        
        if(debug)
            storage.id.set("ETL3550904305917103");
        
        device->telemetry.event("$ETEV09" + storage.id.toString() + "!");
    }

    void handle(){
        calibration.handle();
        heater.handle();
        check();
    }
    
    int get(){
        if(bypass)
            return 23000;

        if(!eeprom.connect(storage.sensor_addr))
            return -1;
        
        const int analog = ads.readADC_SingleEnded(pin);
        return (analog > ANALOG_INVALID) ? analog : -1;
    }
    
    float smooth(){
        static Listener timer = Listener(100);
        static float Xn1, Xn2;
        static float Yn1, Yn2;

        if(!timer.ready())
            return Yn1;

        int analog = get();
        
        if(analog == -1)
            analog = Yn1;

        const float Xn = (float) analog;
        const float Yn = Xn*(0.196462) + Xn1*(0.137177) + Yn1*(1.010643) + Yn2*(-0.344283);
        Xn2 = Xn1; Xn1 = Xn;
        Yn2 = Yn1; Yn1 = Yn;
        return Yn;
    }

    int sample(const int timeout=700){
        const unsigned long startTime = Time::get();
        int analog = 0;
        
        while(Time::get() - startTime < timeout)
            analog = smooth();

        return analog;
    }

    void check(bool force=false){
        static Listener timer      = Listener(60000);
        static Listener eventTimer = Listener(EVENT_MIN_INTERVAL);
        static bool first_fail     = true;

        if(debug)
            return;

        if(!force && !timer.ready())
            return;

        bool wasBad = false;

        while(!eeprom.check(storage.sensor_addr, 1500)){
            screens.sensorFail();

            if(eventTimer.ready() || first_fail)
                {device->telemetry.event("$ETEV24!"); first_fail = false;}

            wasBad = true;
        }

        while(!eeprom.check(storage.eeprom_addr, 1500)){
            screens.eepromFail();

            if(eventTimer.ready() || first_fail)
                {device->telemetry.event("$ETEV24!"); first_fail = false;}

            wasBad = true;
        }

        if(device->test.active)
            device->display.lcd.clear();

        if(wasBad)
            device->display.turnOFF();
    }

    bool failed(){
        if(debug)
            return true;

        if(!eeprom.check(storage.sensor_addr, 1500))
            {screens.sensorFail(); return true;}

        if(!eeprom.check(storage.eeprom_addr, 1500))
            {screens.eepromFail(); return true;}

        return false;
    }

    float analyze(float x){ 
        const float a = storage.a;
        const float b = storage.b;
        const float c = storage.c;
        const float d = storage.d;
        const float result = a*pow(b, c*x + d);

        if(result > 2.500)
            return 2.500;

        if(result < 0.010)
            return 0.00;

        return result;
    }
};

#endif