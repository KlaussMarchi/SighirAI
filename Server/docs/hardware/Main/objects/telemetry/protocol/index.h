#ifndef PROTOCOL_H
#define PROTOCOL_h
#include "../../../device/lang/index.h"
#include <Arduino.h>


template <typename Parent> class Protocol{
  private:
    Parent* device;
    
  public:
    Protocol(Parent* dev):
        device(dev){}

    void check(){
        if(device->telemetry.serial.command.contains("D:"))
            return handleID();

        if(device->telemetry.serial.command.contains("F:"))
            return handleConfig();
        
        if(device->telemetry.serial.command.contains("updt"))
            return device->server.updater.local();

        if(device->telemetry.serial.command.contains("ETRS"))
            return device->reset();

        if(device->telemetry.serial.command.contains("firmware"))
            return device->telemetry.response.set(device->firmware);

        if(device->telemetry.serial.command.contains("ETBL02")){
            device->telemetry.response.set("$ETKAACK!");
            device->vehicle.block();
            return device->display.turnOFF();
        }

        if(device->telemetry.serial.command.contains("ETBL01")){
            device->telemetry.response.set("$ETKAACK!");
            device->vehicle.unblock();
            return device->display.turnOFF();
        }

        if(device->telemetry.serial.command.contains("erase_sensor")){
            auto& sensor = device->sensors.alcohol;

            if(!sensor.eeprom.check(sensor.storage.eeprom_addr, 1500))
                return device->telemetry.event("error");

            bool ok = sensor.eeprom.erase(sensor.storage.eeprom_addr, sensor.storage.data_size);
            device->telemetry.event(ok ? "success" : "error");
            return;
        }

        if(device->telemetry.serial.command.contains("erase")){
            device->display.interface.msg(MSG_BLACK, lang.factorySettings.get());
            device->display.sound.set(BUZZER_BLOW, 10000);

            device->settings.erase(); 
            return device->reset();
        }

        if(device->telemetry.serial.command.contains("ETACK")){
            device->telemetry.response.set("$ETKAACK!");
            return;
        }

        if(device->telemetry.serial.command.contains("ETKA")){
            device->telemetry.event("$ETKAACK!");
            device->telemetry.response.set("$ETEV17!");
            return;
        }

        if(device->telemetry.serial.command.contains("ETBL01")){
            device->telemetry.event("$ETBLACK!");
            device->vehicle.unblock();
            return;
        }
    
        if(device->telemetry.serial.command.contains("ETBL02")){
            device->telemetry.event("$ETBLACK!");
            device->vehicle.block();
            return;
        }
        
        if(device->telemetry.serial.command.contains("TST_TEMP")){
            device->diagnostic.temperature();
            return;
        }
        
        if(device->telemetry.serial.command.contains("TST_SENS")){
            device->diagnostic.alcohol();
            return;
        }

        if(device->telemetry.serial.command.contains("TST_PRESS")){
            device->diagnostic.pressure();
            return;
        }

        if(device->telemetry.serial.command.contains("endTravel")){
            device->vehicle.forceDriving(false);
            return;
        }

        if(device->telemetry.serial.command.contains("last_analog")){
            device->telemetry.event(String(device->test.last_analog));
            return;
        }
        
        if(device->telemetry.serial.command.contains("analog")){
            device->telemetry.event(String(device->sensors.alcohol.get()));
            return;
        }
        
        if(device->telemetry.serial.command.contains("sensor_id")){
            if(device->sensors.alcohol.debug)
                return device->telemetry.event("ETL2608402025435219");

            device->sensors.alcohol.storage.update();
            device->telemetry.event(device->sensors.alcohol.storage.id.get());
            return;
        }

        if(device->telemetry.serial.command.contains("cf_coefs")){
            bool ok = device->sensors.alcohol.storage.genCoefs(device->telemetry.serial.command.toString());
            device->telemetry.event(ok ? "success" : "error");
            return;
        }

        if(device->telemetry.serial.command.contains("coefs")){
            device->sensors.alcohol.storage.update();
            device->telemetry.event(device->sensors.alcohol.storage.coefs.get());
            return; 
        }

        if(device->telemetry.serial.command.contains("calibrate")){
            device->sensors.alcohol.calibration.setDebug(true);
            device->test.start(true);
            device->sensors.alcohol.calibration.setDebug(false);
            return;
        }
    }

    void handleID(){
        const int start = device->telemetry.serial.command.find(':');
        const int end   = device->telemetry.serial.command.find('$');

        if(start == -1 || end == -1)
            return device->telemetry.response.set("ERROR");
        
        auto key   = device->telemetry.serial.command.substring(start+1, end);
        auto value = device->settings.template get<String>(key.get());

        if(value == nullptr)
            return device->telemetry.response.set("ERROR");

        device->telemetry.response.reset();
        device->telemetry.response += '$';
        device->telemetry.response += (value);
        device->telemetry.response += '!';
    }

    void handleConfig(){
        const int start = device->telemetry.serial.command.find(':');
        const int mid   = device->telemetry.serial.command.find('$');
        const int end   = device->telemetry.serial.command.find('!');

        if(start == -1 || mid == -1 || end == -1)
            return device->telemetry.response.set("NONE");

        auto key   = device->telemetry.serial.command.substring(start+1, mid);
        auto value = device->telemetry.serial.command.substring(mid+1, end);
        
        if(key.equals("press"))
            device->sensors.pressure.debug = (bool) value.toInt();

        if(key.equals("testalc"))
            device->test.alcohol_debug = (bool) value.toInt();
        
        device->settings.params.set(key.get(), value.get());
        device->telemetry.response.set(lang.ok.get());
        device->settings.save();
    }
};

#endif