#ifndef RANDOMIC_SCREENS_H
#define RANDOMIC_SCREENS_H
#include "../../../../device/lang/index.h"
#include "../../../../globals/constants.h"
#include "../../../../utils/time/index.h"
#include <LovyanGFX.hpp>

template <typename Parent> class RandomicScreens{
  private:
    Parent* device;

  public:
    RandomicScreens(Parent* dev):
        device(dev){}

    void bichoices(const char* upper, const char* lower){
        auto& display = device->display;
        auto& lcd = device->display.lcd;

        int txt_x, txt_y;
        display.brightness.update();
        display.touch.reset();
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
    }

    void alert(){
        auto& display = device->display;
        auto& lcd = device->display.lcd;

        display.interface.msg(MSG_BLACK, lang.randomTest.get());
        display.sound.set(BUZZER_RND_SOUND, 500);
    
        display.interface.msg(MSG_WHITE, lang.randomTest.get());
        display.sound.set(BUZZER_NO_SOUND, 400);
        
        display.interface.msg(MSG_BLACK, lang.randomTest.get());
        display.sound.set(BUZZER_RND_SOUND, 500);
    
        display.interface.msg(MSG_WHITE, lang.randomTest.get());
        display.sound.set(BUZZER_NO_SOUND, 400);
    
        display.interface.msg(MSG_BLACK, lang.randomTest.get());
        display.sound.set(BUZZER_RND_SOUND, 1200);
        
        display.sound.set(BUZZER_NO_SOUND, 500);
        lcd.clear();
    }
};


#endif