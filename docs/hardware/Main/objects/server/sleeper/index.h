#ifndef SERVER_SLEEPER_H
#define SERVER_SLEEPER_H
#include <Arduino.h>
#include <esp_wifi.h>
#include <WiFi.h>
#include "esp_pm.h"


template <typename Parent> class ServerSleeper{
  private:
    Parent* device;

  public:
    bool on = false;
    int frequency = 160;

    ServerSleeper(Parent* dev):
        device(dev){}

    void handle(){
        static const bool active = device->settings.isEnabled("wifi");
        static const int timeout = 5*60*1000;
        static auto& display     = device->display;

        if(!active)
            return;

        if(on)
            delay(10);

        if(on && display.on)
            return end();

        if(!on && !display.on && Time::get() - display.timeOff > timeout)
            return start();
    }   

    void start(){
        frequency = 80;

        if(device->server.enabled)
            device->server.disable();

        esp_pm_config_esp32_t pmCfg{
            .max_freq_mhz = frequency, 
            .min_freq_mhz = 10,
            .light_sleep_enable = true 
        };
        esp_pm_configure(&pmCfg);

        Serial.println("Sleeper Started");
        on = true;
    }

    void end(){
        frequency = 160;

        esp_pm_config_esp32_t pmCfg{
            .max_freq_mhz = frequency, 
            .min_freq_mhz = 80,
            .light_sleep_enable = false
        };

        esp_pm_configure(&pmCfg);
        delay(50);

        if(!device->server.enabled)
            device->server.enable();
        
        Serial.println("Sleeper Endded");
        on = false;
    }
};

#endif
