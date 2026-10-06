#ifndef TOUCH_H
#define TOUCH_H
#include <Arduino.h>
#include <LovyanGFX.hpp>
#include <LGFX_AUTODETECT.hpp>
#include "../../../utils/time/index.h"
#include "../../../utils/listener/index.h"


template <typename Parent> class Touch{
  private:
    Parent* device;
  
  public:
    unsigned long lastClick;
    int x, y;

    Touch(Parent* dev):
        device(dev){}

    bool click(){
        static Listener timer = Listener(50);
        int x2, y2;

        if(!timer.ready())
            return false;
        
        if(!device->display.lcd.getTouch(&x2, &y2))
            return false;
        
        const float distance = sqrt(sq(x - x2) + sq(y - y2));

        if(distance < 50 && Time::get() - lastClick < 700)
            return false;
        
        lastClick = Time::get();
        x = x2; y = y2;
        return true;
    }
    
    bool centerClick(){
        static Listener timer = Listener(50);
        static float Xn1, Yn1;
        static bool state;

        if(!timer.ready())
            return state;
        
        const float Xn = float(device->display.lcd.getTouch(&x, &y));
        const float Yn = 0.3934693402873667*Xn + 0.6065306597126334*Yn1;

        if(Yn > 0.90){
            state = false;
            Yn1 = 0.00; 
            Xn1 = 0.00;
            return true;
        }
        
        state = (Yn < 0.10) ? false : state;
        Xn1 = Xn;
        Yn1 = Yn;
        return state;
    }

    bool areaClick(int Xo, int Yo, int width, int height){
        if(x < Xo || x > Xo + width)
            return false;
        
        if(y < Yo || y > Yo + height)
            return false;
        
        reset();
        return true;
    }
    
    bool screenClick(bool updateTouch=true){
        const int startX = device->display.width  * 0.1;
        const int startY = device->display.height * 0.1;
        const int width  = device->display.width  * 0.8;
        const int height = device->display.height * 0.8;
        
        if(updateTouch && !click())
            return false;
        
        return areaClick(startX, startY, width, height);
    }
    
    void enableDraw(int timeout){
        auto& lcd = device->display.lcd;
        auto startTime = Time::get();
        int lx, ly;

        while(Time::get() - startTime < timeout){
            if(!lcd.getTouch(&lx, &ly))
                continue;
            
            lcd.fillRoundRect(lx, ly, 12, 12, 12, TFT_RED);
            startTime = Time::get();
        }
    }

    void reset(){
        lastClick = Time::get();
        x = 0;
        y = 0;
    }
};


#endif