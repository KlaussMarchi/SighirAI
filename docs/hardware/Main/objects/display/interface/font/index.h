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

    // A MAIOR FONTE EM QUE TODOS OS TEXTOS CABEM NA CAIXA, PARA NENHUM IDIOMA QUEBRAR LINHA; SE NENHUMA SERVE, A MENOR
    template <typename Texts> void setLargest(const Texts& texts, const int width, const int height){
        const GFXfont* fonts[] = {&Roboto_Bold12pt8b, &Roboto_Bold10pt8b, &Roboto_Regular10pt8b};
        lcd.setTextSize(1);

        for(const GFXfont* font : fonts){
            lcd.setFont(font);
            bool fits = (lcd.fontHeight() <= height);

            for(const auto& text : texts)
                fits = fits && (lcd.textWidth(text) <= width);

            if(fits)
                return;
        }
    }
};

#endif