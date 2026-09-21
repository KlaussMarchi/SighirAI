#ifndef INPUTS_H
#define INPUTS_H
#include "../../../../device/lang/index.h"
#include "../../../../utils/time/index.h"


template <typename Parent> class Inputs{
  private:
    Parent* device;

  public:
    Inputs(Parent* dev):
        device(dev){}

     bool bichoices(const char* upper, const char* lower, bool await=true, int timeout=60000){
        auto& display = device->display;
        auto& lcd = display.lcd; 

        int txt_x, txt_y;
        display.brightness.update();
        lcd.setFont(&Roboto_Bold12pt8b);
        lcd.setTextSize(1);
        lcd.setTextColor(DARK_GREY);

        txt_x = (display.width - lcd.textWidth(upper))/2;
        txt_y = (display.height/4 - lcd.fontHeight());
        lcd.fillRect(0, 0, display.width, display.height / 2, YELLOW);
        lcd.setCursor(txt_x, txt_y);
        lcd.print(upper);
        
        lcd.setTextColor(YELLOW);
        txt_x = (display.width - lcd.textWidth(lower)) / 2;
        txt_y = (display.height - display.height/4 - lcd.fontHeight());
        lcd.fillRect(0, display.height / 2, display.width, display.height / 2, DARK_GREY);
        lcd.setCursor(txt_x, txt_y);
        lcd.print(lower);

        const unsigned long startTime = Time::get();
        display.touch.reset();

        if(!await)
            return true;

        while(!display.touch.click() && Time::get() - startTime < timeout)
            continue;
        
        if(Time::get() - startTime > timeout)
            return true;

        if(display.touch.areaClick(0, 0, display.width, display.height*.5))
            return true;
        
        return false;
    }

    int trichoices(const char* txt0, const char* txt1, const char* txt2, uint32_t timeout=120000, int standard=2){
        auto& display = device->display;
        auto& lcd = display.lcd; 

        int txt_x, txt_y;
        display.brightness.update();
        lcd.setFont(&Roboto_Bold12pt8b);
        lcd.setTextSize(1);

        lcd.setTextColor(DARK_GREY);
        txt_x = (display.width - lcd.textWidth(txt0))/2;
        txt_y = (display.height/6 - lcd.fontHeight());
        lcd.fillRect(0, 0, display.width, display.height*0.333, YELLOW);
        lcd.setCursor(txt_x, txt_y);
        lcd.print(txt0);
        
        lcd.setTextColor(YELLOW);
        txt_x = (display.width - lcd.textWidth(txt1)) / 2;
        txt_y = (display.height/3 + display.height/6 - lcd.fontHeight());
        lcd.fillRect(0, display.height*0.333, display.width, display.height*0.333, DARK_GREY);
        lcd.setCursor(txt_x, txt_y);
        lcd.print(txt1);

        lcd.setTextColor(TFT_BLACK);
        txt_x = (display.width - lcd.textWidth(txt2))/2;
        txt_y = (display.height - display.height/6 - lcd.fontHeight());
        lcd.fillRect(0, display.height*0.666, display.width, display.height*0.333, TFT_WHITE);
        lcd.setCursor(txt_x, txt_y);
        lcd.print(txt2);

        auto startTime = Time::get();
        display.touch.reset();
        device->await(500);

        while(!display.touch.click() && Time::get() - startTime < timeout)
            continue;
        
        if(display.touch.areaClick(0, 0, display.width, display.height*.333))
            return 0;

        if(display.touch.areaClick(0, display.height*.333, display.width, display.height*.333))
            return 1;
        
        return (Time::get() - startTime < timeout) ? 2 : standard;
    }
    
    bool boolean(const char* label, const char* subtitle=nullptr, int timeout = 5*60*1000){
        auto& display = device->display;
        auto& lcd = device->display.lcd;

        const unsigned long startTime = Time::get();
        lcd.fillScreen(TFT_BLACK);
        display.interface.font.reset();

        display.interface.label(label, 110, 100, 100, 50, TFT_WHITE, TFT_BLACK, false);
        display.interface.label(lang.yes.get(), 70, 200, 70, 50, TFT_WHITE, TFT_BLUE);
        display.interface.label(lang.no.get(), 180, 200, 70, 50, TFT_WHITE, TFT_RED);
        display.touch.reset();

        if(subtitle != nullptr){
            device->await(1000);
            display.interface.centeredText(subtitle, TFT_RED, display.height*0.72);
            device->await(2000);
        }

        while(Time::get() - startTime < timeout){
            display.touch.click();

            if(display.touch.areaClick(70, 200, 70, 50))
                return true;
    
            if(display.touch.areaClick(180, 200, 70, 50))
                return false;    
        }
        
        return false;
    }   
};

#endif