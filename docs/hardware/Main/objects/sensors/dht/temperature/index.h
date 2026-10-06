#ifndef TEMPERATURE_H
#define TEMPERATURE_H
#include <Arduino.h>
#include <DHT.h>


class Temperature{
  private:
    Listener timer = Listener(5000);
    DHT& dht;

  public:
    float value  = 25;
    bool working = true;
    bool debug = false;
    int index  = 0;

    Temperature(DHT& _dht):
        dht(_dht){}
    
    bool isWorking(const float temp){
        return !isnan(temp) && abs(temp) < 100;
    }

    float get(){
        const float current = debug ? 25 : dht.readTemperature();

        index   = (isWorking(current) ? 0 : index + 1);
        working = (index < 8);
        return current;
    }

    void handle(bool force=false){
        if(!force && !timer.ready())
            return;

        const float newValue = get();

        if(isWorking(newValue))
            value = newValue;
    }

    String toString(){
        return String((int) value) + " ºC";
    }
};

#endif