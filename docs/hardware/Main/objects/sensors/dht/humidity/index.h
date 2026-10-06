#ifndef Humidity_H
#define Humidity_H
#include <Arduino.h>
#include <DHT.h>


class Humidity{
  private:
    Listener timer = Listener(5000);
    DHT& dht;

  public:
    float value  = 80;
    bool working = true;
    bool debug = false;
    int index  = 0;

    Humidity(DHT& _dht):
        dht(_dht){}

    bool isWorking(const float hum){
        return !isnan(hum) && hum >= 0 && hum <= 100;
    }

    float get(){
        const float current = debug ? 80 : dht.readHumidity();

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
        return String((int) value) + " %";
    }
};

#endif