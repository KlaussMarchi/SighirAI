#ifndef SOUND_H
#define SOUND_H

#include <Arduino.h>
#include "../../../globals/constants.h"
#include "../../../utils/time/index.h"
#define BUZZER_PIN 25
#define MIN_VOLUME 25
#define MAX_VOLUME 255

// ledcWriteTone() deixa o canal em 10 bits (duty 0..1023). O volume máximo vai a 50% de duty, o som
// mais forte de uma onda quadrada (acima disso cai de novo); antes parava em 25%
#define TONE_MAX_DUTY 512

// core 3.x: ledc* recebe o pino e o canal/timer é alocado sozinho (canal 0 fixo cairia no
// mesmo canal do backlight do LovyanGFX, que é anexado antes). core 2.x: ledc* recebe o canal.
#if ESP_ARDUINO_VERSION_MAJOR >= 3
#define BUZZER_LEDC BUZZER_PIN
#else
#define BUZZER_LEDC 0
#endif


template <typename Parent> class Sound{
  private:
    Parent* device;
    
  public:
    int frequency;
    int volume, percent;
    
    Sound(Parent* dev):
        device(dev){}

    void setup(){
#if ESP_ARDUINO_VERSION_MAJOR >= 3
        ledcAttach(BUZZER_PIN, 4000, 8);
#else
        ledcSetup(BUZZER_LEDC, 4000, 8);
        ledcAttachPin(BUZZER_PIN, BUZZER_LEDC);
#endif
        volume = device->settings.template get<int>("volume");
        
        if(volume == 0)
            volume = 127;

        setVolume(volume);
        device->await(100);
        
        set(BUZZER_GOOD_SOUND, 100);
        set(BUZZER_NO_SOUND, 50);
        set(BUZZER_GOOD_SOUND, 100);
        set(BUZZER_NO_SOUND, 50);
        set(BUZZER_GOOD_SOUND, 100);
        set(BUZZER_NO_SOUND, 50);
    }

    void set(int value, int wait=0){
        frequency = value;
        ledcWriteTone(BUZZER_LEDC, frequency);

        if(frequency != BUZZER_NO_SOUND)
            ledcWrite(BUZZER_LEDC, map(volume, 0, MAX_VOLUME, 0, TONE_MAX_DUTY));
        
        if(wait == 0)
            return;

        device->await(wait);
        ledcWriteTone(BUZZER_LEDC, 0);
    }

    void setVolume(const int newValue){
        volume = (newValue > MAX_VOLUME) ? MAX_VOLUME :
                 (newValue < MIN_VOLUME) ? MIN_VOLUME : newValue;      

        percent = mapFloat(volume, MIN_VOLUME, MAX_VOLUME, 0, 100);
        device->settings.params.set("volume", volume);
        device->settings.save();
    }

    void increase(int _percent){
        setVolume(volume + (float(_percent)/100.00 * MAX_VOLUME));
        set(BUZZER_GOOD_SOUND, 100);
    }

    void handleBeep(int interval=150, int sound=BUZZER_BLOW){
        static unsigned long startTime = 0;
        static volatile bool state = false;

        if(Time::get() - startTime < interval)
            return;
        
        startTime = Time::get();
        state     = !state;
        set(state ? sound : BUZZER_NO_SOUND, 0);
    }
    
    void okBeep(){
        set(BUZZER_GOOD_SOUND, 500);
    }

    void goodBeep(){
        set(BUZZER_SIGNAL, 1500);
    }

    void twoBeep(){
        set(BUZZER_BLOW, 100);
        set(BUZZER_NO_SOUND, 30);
        set(BUZZER_BLOW, 100);
    }

    void badBeep(){
        set(BUZZER_BAD_SOUND, 1500);
    }

    void disable(){
        set(BUZZER_NO_SOUND, 0);
    }
    
    void reset(){
        volume    = device->settings.template get<int>("volume");
        frequency = BUZZER_NO_SOUND;
        ledcWriteTone(BUZZER_LEDC, 0);
    }

    String toString(){
        return String(roundDecimal(percent)) + "%";
    }
};

#endif