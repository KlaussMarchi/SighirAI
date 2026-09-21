#ifndef TASKS_H
#define TASKS_H
#include "../../device/lang/index.h"

template <typename Parent> class Tasks{
  private:
    Parent* device;
  
  public:
    Tasks(Parent* dev):
        device(dev){}
    
    void handle(){
        device->display.handle();
        device->server.handle();
        device->test.handle();

        if(!device->display.interface.menu.active)
            device->sensors.handle();

        if(device->vehicle.valet.active)
            return device->vehicle.valet.handle();
        
        device->telemetry.handle();
        device->vehicle.handle();
        handleRestart();
    }

    void checkSystem(const bool increment=false){
        const int reset_num = device->settings.params.template get<int>("reset");
        
        if(increment){
            device->settings.params.set("reset", reset_num+1);
            device->settings.save();
        }

        if(reset_num < 5)
            return;
        
        device->display.brightness.update(40);
        device->settings.params.set("wifi", "false");
        device->settings.save();

        if(increment)
            return;

        device->display.brightness.update(40);
        device->vehicle.unblock();
        device->display.interface.msg(MSG_ORANGE, lang.unexpectedRestarts.get());
        device->display.sound.set(BUZZER_BAD_SOUND, 2000);
        device->await(1500);

        device->display.interface.msg(MSG_BLACK, lang.vehicleUnlocked2.get());
        device->display.interface.centeredText("Alimentação Indevida\r\nVerifique a Bateria do Veículo", TFT_RED, device->display.height*0.65);
        device->await(30000);
        device->display.lcd.clear();
    }

    void handleRestart(){
        if(Time::get() - device->startProg < 259200000) // 3 dias ligado direto
            return;
        
        if(Time::get() - device->vehicle.ignition.getTime() < 10800000)  // 3h desde o ultimo teste
            return;
        
        if(device->vehicle.driving) // veículo tem que estar desligado
            return;

        if(Time::get() - device->vehicle.valet.lastUpdate < 10800000)  // 3h desde o ultimo uso de vallet
            return;

        device->reset();
    }
};

#endif