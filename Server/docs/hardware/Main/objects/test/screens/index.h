#ifndef SCREENS_H
#define SCREENS_H
#include "../../../device/lang/index.h"
#include "../../../globals/constants.h"
#include "../../../utils/time/index.h"
#include <LovyanGFX.hpp>


template <typename Parent> class TestScreens{
  private:
    Parent* device;

  public:
    TestScreens(Parent* dev):
        device(dev){}

    void start(){
        if(!device->display.on){
            device->display.turnON();
            device->await(400);
        }

        device->display.interface.msg(MSG_BLACK, lang.testStarted.get());
    }

    void beep(){
        device->display.sound.set(BUZZER_NO_SOUND);
        device->display.sound.set(BUZZER_SIGNAL, 200);
        device->display.sound.set(BUZZER_NO_SOUND, 50);
        device->display.sound.set(BUZZER_SIGNAL, 200);
        device->await(300);
    }
    
    void inmetro(){
        auto& display = device->display;
        auto& lcd = device->display.lcd;

        String message = 
            String(lang.inmetro2.get()) +
            lang.inmetro3.get() +
            lang.inmetro4.get() +
            lang.inmetro5.get() +
            lang.inmetro1.get();

        const int startX = display.width  * 0.10;
        const int startY = display.height * 0.15;
        const int width  = display.width  * 0.80;
        const int height = display.height * 0.10;

        lcd.fillScreen(TFT_BLACK);
        display.interface.label(lang.attention.get(), startX, startY, width, height, TFT_RED, TFT_BLACK);
        
        lcd.setTextColor(TFT_WHITE);
        lcd.setTextSize(1);
        display.interface.centeredText(message, TFT_WHITE, display.height*.35);
    }

    void input(){
        auto& display = device->display;
        auto& lcd = device->display.lcd;

        display.interface.msg(MSG_BLACK, lang.clickToStart.get());
        display.sound.set(BUZZER_BLOW, 500);
        display.interface.font.setSmall();
        static const int buttonX      = display.width  * 0.48;
        static const int buttonY      = display.height * 0.75;
        static const int buttonWidth  = display.width  * 0.08;
        static const int buttonHeight = 25;

        unsigned long startTime = Time::get();
        int seconds = 60;

        while(seconds > 0){
            device->sensors.warm();
            
            if(display.touch.screenClick(true))
                break;

            if(Time::get() - startTime < 1000)
                continue;

            startTime = Time::get();
            seconds   = seconds - 1;
            lcd.fillRect(buttonX+2, buttonY+2, buttonWidth, buttonHeight-4, TFT_BLACK);

            display.interface.label(
                lang.startingInStr.get() + String(seconds < 10 ? " 0" : " ") + String(seconds) + (" seg"), 
                display.width*.1, display.height*0.7, display.width*.8, 50, TFT_WHITE, TFT_BLACK);
        }

        lcd.fillScreen(TFT_BLACK);
        device->await(250);
    }
    
    bool waitUser(){
        auto& display = device->display;
        display.interface.centeredText(lang.clickScreenTo.get(), TFT_WHITE, display.height*.65, 1);
        display.interface.centeredText(lang.emergencyPostpone.get(), TFT_RED, display.height*.70, 1, true);
        
        Listener timer = Listener(1000);
        int seconds    = 5;
        
        while(seconds > 0){
            device->sensors.warm();
            
            if(display.touch.centerClick())
                return true;

            if(!timer.ready())
                continue;

            seconds = (seconds - 1);
            display.interface.label(lang.startingIn.get() + String(seconds <= 1 ? 1 : seconds-1), display.width*.2, display.height*.85, display.width*.6, 50, TFT_WHITE, TFT_BLACK);
        }
        
        return false;
    }

    void killdriver(){
        auto& display = device->display;
        display.interface.msg(MSG_RED, lang.unauthorizedDriver.get());
        display.interface.centeredText(lang.parkVehicle.get(), TFT_WHITE, display.height*0.7);
    }
    
    void blow(){
        device->display.interface.msg(MSG_BLACK, lang.blow.get());
        device->display.sound.set(BUZZER_BLOW, 200);
        device->display.sound.set(BUZZER_NO_SOUND, 50);
        device->display.sound.set(BUZZER_BLOW, 200);
    }

    void calibrationFail(){
        device->display.interface.msg(MSG_ORANGE, lang.recalibratingSensor.get());
        device->display.sound.set(BUZZER_SIGNAL, 250);
        device->await(3000);
    }
};


#endif

