#ifndef INTERFACE_H
#define INTERFACE_H
#include "font/index.h"
#include "menu/index.h"
#include "loading/index.h"
#include "inputs/index.h"
#include "keyboard/index.h"


template <typename Parent> class Interface{
  private:
    Parent* device;

  public:
    LoadingWindow<Parent> loading;
    Menu<Parent> menu;
    Inputs<Parent> inputs;
    Keyboard<Parent> keyboard;
    DisplayFont font;
    
    Interface(Parent* dev):
        device(dev),
        menu(dev),
        loading(dev),
        inputs(dev),
        keyboard(dev),
        font(dev->display.lcd){}

    void setup(){
        menu.setup();
    }

    void label(const String& text, int buttonX, int buttonY, int buttonWidth, int buttonHeight, int txtColor, int bkgColor, bool contorno=false){
        if(!device->display.on)
            device->display.turnON();

        device->display.lcd.fillRect(buttonX, buttonY, buttonWidth, buttonHeight, bkgColor);
        device->display.lcd.setTextColor(txtColor);
        int16_t textX = buttonX + (buttonWidth - device->display.lcd.textWidth(text)) / 2;
        int16_t textY = buttonY + (buttonHeight - device->display.lcd.fontHeight()) / 2;
        device->display.lcd.setCursor(textX, textY);
        device->display.lcd.print(text);
    }

    void msg(int type, const String& text){
        if(!device->display.on)
            device->display.turnON();

        int color = TFT_BLACK;
        font.reset();

        switch(type){
            case 0:
                device->display.lcd.fillScreen(TFT_BLACK);
                color = TFT_WHITE;
                break;
            case 1:
                device->display.lcd.fillScreen(TFT_WHITE);
                color = TFT_BLACK;
                break;
            case 2:
                device->display.lcd.fillScreen(TFT_RED);
                color = TFT_WHITE;
                break;
            case 3:
                device->display.lcd.fillScreen(TFT_GREEN);
                color = TFT_WHITE;
                break;
            case 4:
                device->display.lcd.fillScreen(TFT_ORANGE);
                color = TFT_WHITE;
                break;
            default:
                break;
        }
        
        centeredText(text, color, 0, 2, false);
    }

    void centeredText(const String& text, int textColor=TFT_WHITE, int startY=0, int lineSpace=2, bool resetFont=true){
        LGFX& lcd = device->display.lcd;

        if(!device->display.on)
            device->display.turnON();

        const int length = text.length();
        int num_lines    = 1;
        
        if(resetFont)
            lcd.setFont(&Roboto_Regular10pt8b);
        
        lcd.setTextColor(textColor);
        String section;
        
        for(int i = 0; i < length; i++)
            if(text[i] == '\n' || (text[i] == '\r' && i + 1 < text.length() && text[i + 1] == '\n')) {
                num_lines++;

                if(text[i] == '\r') 
                    i++;
            }
        
        int line_height = lcd.fontHeight() * lineSpace;
        int start_y = (startY == 0) ? (lcd.height() - (num_lines * line_height)) / 2 : startY;
        int y = start_y;

        for(int i = 0; i < length; i++){
            const char c = text.charAt(i);
            
            if(c != '\n' && c != '\r' && c != '\0')
                section.concat(c);

            if(c == '\n' || (c == '\r' && i + 1 < length && text.charAt(i+1) == '\n') || i == length-1){
                const int x = (lcd.width() - lcd.textWidth(section)) / 2;
                lcd.setCursor(x, y);
                lcd.println(section);
                
                y = (y + line_height);
                section = "";
                
                if(c == '\r' && i + 1 < length && text.charAt(i+1) == '\n') 
                    i++;
            }
        }
    }

    void printIcon(const String& icon, float scale, uint16_t color, int x, int y) {
        LGFX& lcd = device->display.lcd;
        lcd.setFont(&remixicon64pt8b);
        lcd.setTextColor(color);
        lcd.setTextSize(scale);
        lcd.setCursor(x, y);
        lcd.print(icon);
    }

    void alert(const String& title, const String& subtitle="", byte type=MSG_RED, int await=3000, bool turnoff=false){
        msg(type, title);
        centeredText(subtitle, TFT_WHITE, device->display.height*0.7);
        
        if(await > 0)
            device->await(await);

        if(turnoff)
            device->display.turnOFF();
    }
};


#endif