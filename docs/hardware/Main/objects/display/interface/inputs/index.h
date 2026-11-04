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

    int trichoices(const char* txt0, const char* txt1, const char* txt2, int standard=0, uint32_t timeout=120000){
        auto& display = device->display;
        auto& lcd = display.lcd; 

        int txt_x, txt_y;
        const int band = display.height/3;   // INTEIRO: AS TRÊS FAIXAS COBREM A TELA SEM FRESTA DA TELA ANTERIOR
        display.brightness.update();
        lcd.setFont(&Roboto_Bold12pt8b);
        lcd.setTextSize(1);

        lcd.setTextColor(DARK_GREY);
        txt_x = (display.width - lcd.textWidth(txt0))/2;
        txt_y = (display.height/6 - lcd.fontHeight());
        lcd.fillRect(0, 0, display.width, band, YELLOW);
        lcd.setCursor(txt_x, txt_y);
        lcd.print(txt0);
        
        lcd.setTextColor(YELLOW);
        txt_x = (display.width - lcd.textWidth(txt1)) / 2;
        txt_y = (display.height/3 + display.height/6 - lcd.fontHeight());
        lcd.fillRect(0, band, display.width, band, DARK_GREY);
        lcd.setCursor(txt_x, txt_y);
        lcd.print(txt1);

        lcd.setTextColor(TFT_BLACK);
        txt_x = (display.width - lcd.textWidth(txt2))/2;
        txt_y = (display.height - display.height/6 - lcd.fontHeight());
        lcd.fillRect(0, 2*band, display.width, display.height - 2*band, TFT_WHITE);
        lcd.setCursor(txt_x, txt_y);
        lcd.print(txt2);

        auto startTime = Time::get();
        display.touch.reset();
        device->await(500);

        while(!display.touch.click() && Time::get() - startTime < timeout)
            continue;

        if(Time::get() - startTime >= timeout)   // O RESET DEIXA O TOQUE EM (0,0), DENTRO DA PRIMEIRA FAIXA
            return standard;

        if(display.touch.areaClick(0, 0, display.width, display.height*.333))
            return 0;

        if(display.touch.areaClick(0, display.height*.333, display.width, display.height*.333))
            return 1;

        return 2;
    }

    // A PRIMEIRA OPÇÃO EM DESTAQUE NA LARGURA TODA E AS OUTRAS EM DUAS COLUNAS COMO NO MENU, A ÚLTIMA (SAIR) ESCURA; SEM TOQUE VALE standard
    template <int N> int choices(const char* tag, const char* title, const char* (&labels)[N], const int standard, const uint32_t timeout=120000){
        auto& display = device->display;
        auto& lcd     = display.lcd;

        const int margin = display.width*0.05;
        const int gap    = display.width*0.04;
        const int startY = display.height*0.20;
        const int step   = (display.height*0.985 - startY)/(N/2 + 1);   // O DESTAQUE E AS LINHAS DE DUAS
        const int height = step - gap;
        const int column = (display.width - 2*margin - gap)/2;
        const char* tiles[N-1];

        auto box = [&](const int i, int& x, int& y, int& width){
            x     = (i == 0) ? margin : margin + (i - 1)%2*(column + gap);
            y     = startY + (i + 1)/2*step;
            width = (i == 0) ? display.width - 2*margin : column;
        };

        for(int i=1; i<N; i++)
            tiles[i-1] = labels[i];

        display.brightness.update();
        lcd.fillScreen(BG_COLOR);
        display.interface.pill(tag, display.height*0.03, BLUE);
        display.interface.font.setStyle(&Roboto_Bold12pt8b, TFT_WHITE);
        display.interface.centeredText(title, TFT_WHITE, display.height*0.115, 1, false);

        for(int i=0; i<N; i++){
            const int fill = (i == 0) ? YELLOW : (i == N-1) ? DARK_GREY : LIGHT_GREY;
            const int text = (i == 0) ? TFT_WHITE : (i == N-1) ? LIGHT_GREY : DARK_GREY;
            int x, y, width;

            box(i, x, y, width);

            if(i == 1)
                display.interface.font.setLargest(tiles, column - 16, height);

            lcd.fillRoundRect(x, y, width, height, 12, fill);
            lcd.setTextColor(text);
            lcd.setCursor(x + (width - lcd.textWidth(labels[i]))/2, y + (height - lcd.fontHeight())/2);
            lcd.print(labels[i]);
        }

        const unsigned long startTime = Time::get();
        display.touch.reset();

        while(Time::get() - startTime < timeout){
            device->sensors.warm();   // LINHA DE BASE DO SOPRO VIVA ENQUANTO A LISTA ESPERA

            if(!display.touch.click())
                continue;

            for(int i=0; i<N; i++){
                int x, y, width;
                box(i, x, y, width);

                if(display.touch.areaClick(x, y, width, height))
                    return i;
            }
        }

        return standard;
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