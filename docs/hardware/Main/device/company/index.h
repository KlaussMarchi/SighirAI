#ifndef DEVICE_COMPANY_H
#define DEVICE_COMPANY_H
#include <Arduino.h>
#include <LovyanGFX.hpp>
#include "../../assets/logos/sighir_logo.h"
#include "../../assets/logos/default_logo.h"

template <typename Parent> class Company{
  private:
    Parent* device;

  public:
    const char* name = "sighir";

    Company(Parent* dev):
        device(dev){}

    void setup(){
        auto& display = device->display;

        if(check())
            return showVersion();

        device->display.interface.msg(MSG_WHITE, lang.configParams.get());
        device->display.sound.set(BUZZER_GOOD_SOUND, 1000);

        display.interface.centeredText(name, TFT_BLACK, display.height*0.7);
        device->await(1000);

        device->settings.params.set("company", name);
        configParams();
        device->server.updater.apply(device->settings.template get<String>("remote"));
        device->await(1000);

        device->settings.save();
        device->await(3000);
        device->reset();
    }

    void configParams(){
        device->settings.params.data["vehicle_type"] = 0;
        device->settings.params.data["telemetry"] = 0;
        device->settings.params.data["enable_random"] = 1;
        device->settings.params.data["max_postpone"] = 3;
        device->settings.params.data["postpone_time"] = 5;
        device->settings.params.data["maneuver_time"] = 1;
        device->settings.params.data["ssid"] = "Etilometro";
        device->settings.params.data["passwd"] = "12345678";
        device->settings.params.data["time_of_travel"] = 5;
        device->settings.params.data["number_of_tests"] = 1;
        device->settings.params.data["rand_ppn_time"] = 2;
        device->settings.params.data["rand_min_time"] = 5;
        device->settings.params.data["camera"] = 5;
        device->settings.params.data["bypass"] = 0;
    }

    void sighir(int await=0){
        device->display.lcd.drawJpg(sighir_logo, sizeof(sighir_logo), 0, 0, device->display.width, device->display.height, 0, 0, 1.0);

        if(await > 0)
            delay(await);
    }

    void logo(){
        device->display.lcd.drawJpg(default_logo, sizeof(default_logo), 0, 0, device->display.width, device->display.height, 0, 0, 1.0);
    }

    void showVersion(){
        device->display.interface.msg(MSG_BLACK, lang.vehicularBreath.get());
        device->display.lcd.fillRect(0, device->display.height*0.7, device->display.width, device->display.height, TFT_BLACK);
        device->display.interface.centeredText(lang.versionStr.get() + String(device->firmware), TFT_RED, device->display.height*0.7);
        device->await(3000);
    }

    bool check(){
        return (String(name) == device->settings.template get<String>("company"));
    }
};

#endif
