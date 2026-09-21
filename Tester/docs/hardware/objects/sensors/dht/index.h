#ifndef DHTSENSOR_H
#define DHTSENSOR_H
#include "../../../device/lang/index.h"
#include <Arduino.h>
#include <DHT.h>
#include "temperature/index.h"
#include "humidity/index.h"


template <typename Parent> class sensorDHT{
  private:
    Parent* device;

  public:
    const int pin = 32;
    DHT dht = DHT(pin, DHT22);
    bool debug;
    
    Temperature temperature = Temperature(dht);
    Humidity humidity = Humidity(dht);

    sensorDHT(Parent* dev):
        device(dev){}

    void setup(){
        Serial.println("Sensor DHT em " + String(debug ? "debug" : "Funcionamento"));
        temperature.debug = debug;
        humidity.debug    = debug;

        if(debug)
            return;

        dht.begin();
        handle();
    }

    void handle(){
        static Listener timer  = Listener(15*60*1000);
        static bool first_time = true;

        if(debug)
            return;

        temperature.handle();
        humidity.handle();

        if(!temperature.working && !device->display.on  && (timer.ready() || first_time)){
            device->display.interface.alert(lang.defectiveSensor.get(), lang.temperature.get() + temperature.toString(), MSG_RED, 10000, true);
            first_time = false;
            return device->telemetry.event("$ETEV27!");
        }

        if(temperature.value > 52 && !device->display.on && (timer.ready() || first_time)){
            device->display.interface.alert(lang.highTemp.get(), temperature.toString(), MSG_ORANGE, 10000, true);
            first_time = false;
            return device->telemetry.event("$ETEV27!");
        }

        if(temperature.value > 60 && !device->display.on && (timer.ready() || first_time)){
            device->display.interface.alert(lang.severeTemp.get(), temperature.toString(), MSG_RED, 10000, true);
            first_time = false;
            return device->telemetry.event("$ETEV28!");
        }
    }

    void update(){
        if(debug)
            return;

        temperature.handle(true);
        humidity.handle(true);
    }
};

#endif
