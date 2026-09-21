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
        return !isnan(hum) && abs(hum) < 100;
    }

    float get(){
        const float current = debug ? 25 : dht.readTemperature();
        
        if(isnan(current) || abs(current) > 100)
            index = (index + 1);

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

    float sample(const int timeout){
        const unsigned long startTime = Time::get();

        while(Time::get() - startTime < timeout){
            const float current = get();

            if(current != 999)
                return current;
            
            delay(5);
        }

        return 999;
    }

    String toString(){
        return String((int) value) + " %";
    }
};

#endif