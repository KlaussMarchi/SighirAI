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

    void update(){
        if(debug)
            return;

        temperature.handle(true);
        humidity.handle(true);
    }

    void handle(){
        if(debug)
            return;

        temperature.handle();
        humidity.handle();
        checkTemperature();
        checkHumidity();
    }

    void checkTemperature(){
        static Listener timer  = Listener(15*60*1000);
        static bool first_time = true;

        if(temperature.working && temperature.value < TEMP_ALERT)
            return;

        if(device->display.on || !(timer.ready() || first_time))
            return;

        first_time = false;
        
        if(!temperature.working)
            return alert(lang.defectiveSensor.get(), lang.temperature.get() + temperature.toString(), MSG_RED, "$ETEV27!");

        if(temperature.value >= TEMP_DANGER)
            return alert(lang.severeTemp.get(), temperature.toString(), MSG_RED, "$ETEV28!");

        alert(lang.highTemp.get(), temperature.toString(), MSG_ORANGE, "$ETEV27!");
    }

    void checkHumidity(){
        static Listener timer        = Listener(5*60*1000);
        static Listener eventTimer   = Listener(EVENT_MIN_INTERVAL);
        static bool first_time       = true;
        static bool event_first_time = true;

        if(humidity.value < HUM_ALERT)
            return;

        if(device->display.on || !(timer.ready() || first_time))
            return;

        first_time = false;
        const bool sendEvent = eventTimer.ready() || event_first_time;
        event_first_time = event_first_time && !sendEvent;
        alert(lang.highHumidity.get(), humidity.toString(), MSG_ORANGE, "$ETEV41!", sendEvent);
    }

    void alert(const String& title, const String& subtitle, byte type, const char* code, bool sendEvent=true){
        device->display.interface.alert(title, subtitle, type, 10000, true);

        if(sendEvent)
            device->telemetry.event(code);
    }
};

#endif
