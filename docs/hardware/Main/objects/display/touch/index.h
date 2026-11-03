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
    static const int POLL_TIME    = 20;   // ms, UM TOQUE CURTO DURA ~50 MS
    static const int RELEASE_TIME = 60;   // ms SEM LEITURA = DEDO FORA; O CONTROLADOR PERDE LEITURAS NO MEIO DO TOQUE
    unsigned long lastClick;
    unsigned long lastSeen = 0;
    bool pressed = false;   // O DEDO DO ÚLTIMO CLIQUE AINDA NÃO SAIU DA TELA
    int x, y;

    Touch(Parent* dev):
        device(dev){}

    // UM CLIQUE POR TOQUE, NA HORA QUE O DEDO ENCOSTA: SEGURAR NÃO REPETE E TOQUES RÁPIDOS NO MESMO LUGAR CONTAM
    bool click(){
        static Listener timer = Listener(POLL_TIME);
        int x2, y2;

        if(!timer.ready())
            return false;

        if(!device->display.lcd.getTouch(&x2, &y2)){
            if(Time::get() - lastSeen > RELEASE_TIME)
                pressed = false;

            return false;
        }

        lastSeen = Time::get();

        if(pressed)
            return false;

        pressed   = true;
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

    // TELA NOVA: O DEDO QUE AINDA ESTÁ NELA PRECISA SAIR ANTES DO PRÓXIMO CLIQUE
    void reset(){
        int x2, y2;

        if(device->display.lcd.getTouch(&x2, &y2))
            lastSeen = Time::get();

        lastClick = Time::get();
        pressed   = (Time::get() - lastSeen < RELEASE_TIME);
        x = 0;
        y = 0;
    }
};


#endif