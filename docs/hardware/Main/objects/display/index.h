#ifndef DISPLAY_H
#define DISPLAY_H
#include "../../device/lang/index.h"

#define LGFX_WT32_SC01  // CONFIGURANDO O NOME DA PLACA DO DISPLAY
#define LGFX_USE_V1     // CONFIGURE PARA USAR A NOVA VERSÃO DA BIBLIOTECA

#include <Arduino.h>
#include <LovyanGFX.hpp>
#include <LGFX_AUTODETECT.hpp>

#include "../../assets/font/Remix_Icon_64px.h"
#include "../../assets/font/Roboto_400R_10px.h"
#include "../../assets/font/Roboto_700B_10px.h"
#include "../../assets/font/Roboto_400R_12px.h"
#include "../../assets/font/Roboto_700B_12px.h"

#include "brightness/index.h"
#include "interface/index.h"
#include "sound/index.h"
#include "touch/index.h"


template <typename Parent> class Display{
  private:
    Parent* device;

  public:
    Brightness<Parent> brightness;
    Interface<Parent> interface;
    Sound<Parent> sound;
    Touch<Parent> touch;
    unsigned long timeOff;
    int width, height;
    bool on = false;
    LGFX lcd;
    
    Display(Parent* dev):
        device(dev),
        brightness(dev),
        interface(dev),
        sound(dev),
        touch(dev){}
    
    void setup(){
        start();
        lcd.setRotation(2);
        lcd.setBrightness(255);
        width  = lcd.width();
        height = lcd.height();
        interface.setup();
        brightness.setup();
        touch.click();
        sound.setup();
        turnON();
    }

    void handle(){
        interface.menu.handle();
        
        if(on && Time::get() - touch.lastClick > 60000)
            if(!device->vehicle.maneuver.active)
                turnOFF();
    }

    // SEM DISPLAY O BOOT SEGUE (O LGFX VIRA PAINEL NULO): APAGAR O NVS PERDIA O ID E REINICIAVA PARA SEMPRE
    void start(){
        for(int x=0; x<15; x++){
            if(lcd.init())
                return;

            releaseBus();
            delay(250);
        }
    }

    // O AUTODETECT LE O TOUCH NO I2C DO SENSOR; UM CHIP PARADO NO MEIO DE UM BYTE SEGURA O SDA E O ESP.restart() NAO O REINICIA
    void releaseBus(){
        const int sda = device->sensors.alcohol.sda;
        const int scl = device->sensors.alcohol.scl;
        pinMode(sda, INPUT_PULLUP);
        pinMode(scl, OUTPUT_OPEN_DRAIN);

        for(int x=0; x<9 && !digitalRead(sda); x++){
            digitalWrite(scl, LOW);  delayMicroseconds(5);
            digitalWrite(scl, HIGH); delayMicroseconds(5);
        }

        pinMode(scl, INPUT_PULLUP);
    }
    
    void turnON(){
        brightness.update();
        touch.reset();
        timeOff = 0;
        on = true;
    }
    
    void turnOFF(){
        if(!on)
            return;
        
        timeOff = Time::get();
        interface.menu.reset();
        sound.reset();
        touch.reset();
        exit();
        on = false;
    }

    void exit(){
        interface.msg(MSG_BLACK, lang.turningOffDisplay.get());
        int centerX = width  / 2;
        int centerY = height / 2 + 70;
        int radius = 20;
        int step   = 0;
    
        lcd.fillCircle(centerX, centerY, radius + 10, TFT_BLACK);
        device->await(40);
        
        for(int i = 0; i < 12; i++){
            int angle = i * 30 + step * 30;
            int innerX = centerX + (radius - 10) * cos((angle - 90) * 3.14159 / 180);
            int innerY = centerY + (radius - 10) * sin((angle - 90) * 3.14159 / 180);
            int outerX = centerX + radius * cos((angle - 90) * 3.14159 / 180);
            int outerY = centerY + radius * sin((angle - 90) * 3.14159 / 180);
            lcd.drawLine(innerX, innerY, outerX, outerY, TFT_WHITE);
            device->await(40);
        }
        
        clear();
    }
    
    void clear(){
        sound.set(BUZZER_NO_SOUND);
        lcd.fillScreen(TFT_BLACK);
        lcd.setBrightness(0);
    }
};

#endif