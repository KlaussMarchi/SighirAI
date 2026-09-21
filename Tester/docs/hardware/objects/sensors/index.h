#ifndef SENSORS_H
#define SENSORS_H
#include <Arduino.h>
#include <Wire.h>
#include "../../utils/listener/index.h"
#include "dht/index.h"
#include "alcohol/index.h"
#include "pressure/index.h"


template <typename Parent> class Sensors{
  private:
    Parent* device;
    
  public:
    AlcoholSensor<Parent> alcohol;
    Pressure<Parent> pressure;
    sensorDHT<Parent> dht;

    Sensors(Parent* dev):
        device(dev),
        alcohol(dev),
        pressure(dev),
        dht(dev){}

    void setup(){
        alcohol.setup();
        dht.setup();
        pressure.setup();
        warm(3000);
    }
    
    void handle(){
        dht.handle();
        alcohol.handle();
    }

    void warm(int timeout=0){
        const unsigned long startTime = Time::get();

        do{
            alcohol.calibration.handle();
            alcohol.heater.set(true);
            pressure.blower.handle();
            alcohol.smooth();
            device->server.handle();
        }
        while(Time::get() - startTime < timeout);
    }
}; 

#endif