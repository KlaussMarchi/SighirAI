#ifndef KEYBOARD_H
#define KEYBOARD_H
#include "../../../../device/lang/index.h"
#include <ctype.h>
#define MSG_MAX_SIZE 30


template <typename Parent> class Keyboard{
  private:
    Parent* device;

    // 5 páginas, 4 linhas cada, 3 colunas, 3 caracteres max
    char keyboard[5][4][3][3] = {
        {{"1", "2", "3" },
        { "4", "5", "6" },
        { "7", "8", "9" },
        { "<", "0", "+"}},

        {{"a", "b", "c" },
        { "d", "e", "f" },
        { "g", "h", "i" },
        { "<", "j", "+"}},

        {{"k", "l", "m"},
        { "n", "o", "p" },
        { "q", "r", "s" },
        { "<", "t", "+"}},
        
        {{"u", "v", "w"},
        { "x", "y", "z" },
        { "*", "@", "#" },
        { "<", " ", "+"}},
        
        {{"%", "-", "="},
        { "/", "~", "_" },
        { "?", "!", "&" },
        { "<", "$", "+"}},
    };

    void toUpper(char *s) {
        while(*s){
            *s = toupper(*s);
            s++;
        }
    }

    void toLower(char *s){
        while (*s){
            *s = tolower(*s);
            s++;
        }
    }

  public:
    int page   = 0;
    bool upper = false;
    bool done  = false;
    String message;

    Keyboard(Parent* dev):
        device(dev){
            message.reserve(MSG_MAX_SIZE);
        }

    void draw(const char* title, const char* value, bool alpha=false){
        auto& display = device->display;
        auto& lcd = device->display.lcd;

        display.brightness.update();
        display.touch.reset();
        
        display.interface.font.setBold();
        lcd.fillScreen(TFT_BLACK);
        display.interface.label(title, 40, 20, 250, 45, TFT_WHITE, TFT_BLACK, false);
        display.interface.label(value, 40, 60, 250, 45, TFT_BLACK, TFT_WHITE, true);

        display.interface.label(lang.typeWord.get(), 40, 110, 250, 45, TFT_WHITE, TFT_BLACK, false);
        display.interface.label("", 40, 150, 250, 45, TFT_BLACK, TFT_WHITE, true);

        display.interface.label("^",  260, 340, 50, 50, TFT_BLACK, TFT_WHITE, true);
        display.interface.label(lang.ok.get(), 260, 400, 50, 50, TFT_BLACK, TFT_WHITE, true);

        if(alpha)
            page = 1;

        drawKeys();
    }

    void drawKeys(){
        auto& display = device->display;
        auto& lcd = device->display.lcd;
        
        int i = 80;
        int j = 220;

        for(int lin=0; lin<4; lin++){
            for(int col=0; col<3; col++){
                char* key = keyboard[page][lin][col];
                upper ? toUpper(key) : toLower(key);
                
                display.interface.label(key, i, j, 50, 50, TFT_BLACK, TFT_WHITE, true);
                i += 60;
            }

            i = 80;
            j += 60;
        }
    }

    void handle(){
        auto& display = device->display;
        auto& lcd     = device->display.lcd;

        if(!display.touch.click())
            return;
        
        int i = 20;
        int j = 220;
        
        for(int lin=0; lin<4; lin++){
            for(int col=0; col<3; col++){
                i += 60;

                if(!display.touch.areaClick(i, j, 50, 50))
                    continue;
                
                char* key = keyboard[page][lin][col];
                update(key);

                if(done)
                    break;
            }

            i = 20;
            j += 60;
        }

        if(!done && display.touch.areaClick(260, 340, 50, 50))
            update("^");

        if(!done && display.touch.areaClick(260, 400, 50, 50))
            update(lang.ok.get());
        
        display.touch.reset();
        device->await(350);
    }

    void update(const char* key){
        auto& display = device->display;
        auto& lcd = device->display.lcd;

        if(strcmp(key, lang.ok.get()) == 0){
            lcd.clear();
            done = true; 
            return;
        }

        if(strcmp(key, "^") == 0){
            upper = !upper; 
            drawKeys();
            return;
        }

        if(strcmp(key, "+") == 0){
            page = (page + 1 < 5) ? (page + 1) : 0; 
            drawKeys();
            return;
        }
        
        if(strcmp(key, "<") == 0){
            message = message.substring(0, message.length()-1);
            showMessage();
            return;
        }
        
        if(message.length() < MSG_MAX_SIZE){
            message.concat(key);
            showMessage();
            return;
        }
    }

    void showMessage(){
        device->display.interface.label(message, 40, 150, 250, 45, TFT_BLACK, TFT_WHITE, true);
    }
    
    String get(){
        auto& display = device->display;
        auto& lcd = device->display.lcd;
        message   = String();

        while(!done)
            handle();
        
        reset();
        message.trim();
        return message;
    }

    void reset(){
        page    = 0;    
        upper   = false;
        done    = false;
    }  
};

#endif