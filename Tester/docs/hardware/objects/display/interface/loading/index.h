#ifndef LOADING_WINDOW_H
#define LOADING_WINDOW_H
#include "../../../../utils/time/index.h"
#include "../../../../utils/text/index.h"
#include "../../../../utils/listener/index.h"
#include <LovyanGFX.hpp>


template <typename Parent> class LoadingWindow{
  private:
    Parent* device;

  public:
    unsigned long startTime = Time::get();
    Listener timer = Listener(100);
    Text<30> title, subtitle;
    int heightPercent = 100; 
    int last_index = 0;
    int index   = 0;
    int timeout = 0;

    LoadingWindow(Parent* dev):
        device(dev){}

    void start(const char* _title, const char* _subtitle, int _timeout=0, int _heightPercent=100){
        startTime = Time::get();
        index     = 0;

        title.set(_title);
        subtitle.set(_subtitle);
        
        timeout = _timeout;
        heightPercent = _heightPercent;
        draw();
    }

    void draw(){
        auto& display = device->display;
        int effectiveHeight = (display.height * heightPercent) / 100;

        if(heightPercent < 100){
            display.lcd.fillRect(0, 0, display.width, effectiveHeight, TFT_BLACK);
            display.interface.centeredText(title.get(), TFT_WHITE, effectiveHeight * 0.25);
        }
        else
            display.interface.msg(MSG_BLACK, title.get());

        display.interface.centeredText(subtitle.get(), TFT_WHITE, effectiveHeight * 0.75);
        drawBar(index, true);
    }

    void reset(){
        startTime = 0;
        index   = 0;
        timeout = 0;
        heightPercent = 100; 
    }

    bool done(bool _draw=true){
        if(index < 100)
            return false;

        if(_draw)
            {drawBar(100, false); device->await(100);}
        
        reset();
        return true;
    }
    
    void step(int value=0, bool increment=true, bool render=true){
        if(value > 0)
            index = increment ? (index + value) : value;

        else if(timeout > 0)
            index = ((float) Time::get() - startTime)/((float) timeout) * 100.0;
    
        if(render && index != last_index && timer.ready())
            drawBar(index, false);
    }
    
    void drawBar(int percentage, bool first_time){
        auto& display = device->display;
        LGFX& lcd = device->display.lcd;
        
        // Recalcula a altura ativa para posicionar a barra corretamente
        int activeHeight = (display.height * heightPercent) / 100;
        
        int buttonWidth  = display.width  * 0.8;
        int buttonHeight = 25;
        int buttonX      = display.width  * 0.1;
        
        int buttonY     = activeHeight * 0.55; 
        int filledWidth = map(percentage, 0, 100, 0, buttonWidth-2);
        
        if(first_time){
            lcd.fillRect(buttonX, buttonY, buttonWidth, buttonHeight, TFT_WHITE);
            lcd.fillRect(buttonX+2, buttonY+2, buttonWidth-4, buttonHeight-4, TFT_BLACK);
        }
    
        lcd.fillRect(buttonX+2, buttonY+2, filledWidth, buttonHeight-4, TFT_WHITE);
        display.interface.label(String(percentage) + "%", buttonX, buttonY+35, buttonWidth, buttonHeight, TFT_WHITE, TFT_BLACK, false);
        last_index = index;
    }
};

#endif