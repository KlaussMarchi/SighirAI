#ifndef BRIGHTNESS_H
#define BRIGHTNESS_H
#include <LovyanGFX.hpp>
#define MIN_BRIGHTNESS 25
#define MAX_BRIGHTNESS 170


template <typename Parent> class Brightness{
  private:
    Parent* device;

  public:
    int value, percent;
    
    Brightness(Parent* dev):
        device(dev){}

    void setup(){
        value = device->settings.template get<int>("brightness");

        if(value == 0)
            value = 127;

        set(value);
    }

    void set(int newValue){
        value = (newValue > MAX_BRIGHTNESS) ? MAX_BRIGHTNESS :
                (newValue < MIN_BRIGHTNESS) ? MIN_BRIGHTNESS : newValue;

        percent = mapFloat(value, MIN_BRIGHTNESS, MAX_BRIGHTNESS, 0, 100);
        device->settings.params.set("brightness", value);
        device->settings.save();
        update();
    }

    void increase(int _percent){
        set(value + (float(_percent)/100.00 * MAX_BRIGHTNESS));
    }

    void update(int val=0){
        if(val > 0)
            value = val;
        
        percent = value * 100/MAX_BRIGHTNESS; 
        device->display.lcd.setBrightness(value);
    }

    void reset(){
        setup();
        update();
    }

    String toString(){
        return String(roundDecimal(percent)) + "%";
    }
};

#endif