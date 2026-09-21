#ifndef FONT_H
#define FONT_H


class DisplayFont{
  public:
    LGFX& lcd;
    
    DisplayFont(LGFX& _lcd):
        lcd(_lcd){}

    void setStyle(const GFXfont *font, uint16_t text_color){
        lcd.setFont(font);
        lcd.setTextColor(text_color);
        lcd.setTextSize(1);
    }

    void setBold(){
        lcd.setTextSize(1);
        lcd.setFont(&Roboto_Bold10pt8b);
    }

    void setSmall(){
        lcd.setTextSize(1);
        lcd.setFont(&Roboto_Regular10pt8b);
    }

    void reset(){
        lcd.setFont(&Roboto_Regular12pt8b);
        lcd.setTextSize(1);
    }
};

#endif