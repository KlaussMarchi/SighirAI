#ifndef EEPROM_H
#define EEPROM_H
#include <Arduino.h>
#include <Wire.h>
#include "../../../../utils/time/index.h"

// O touch do WT32-SC01 (LovyanGFX) usa o controlador I2C1 (Wire1) nos mesmos pinos 18/19 do sensor.
// No core 3.x o Wire.begin(18, 19) tomaria os pinos e desligaria o I2C1 do touch, e cada leitura do
// touch passaria a derrubar o sensor; por isso o sensor compartilha o Wire1 que o LovyanGFX já abriu.
#define SENSOR_WIRE Wire1


class EEPROM{
  public:
    bool connect(int addr){
        SENSOR_WIRE.beginTransmission(addr);

        if(SENSOR_WIRE.endTransmission() == 0)
            return true;

        return false;
    }

    bool check(int addr, int timeout=500){
        const unsigned long startTime = Time::get();
        
        while(Time::get() - startTime < timeout){
            if(connect(addr))
                return true;

            delay(100);
        }
        
        return false;
    }

    // pageSize divide a página física de 64 bytes: nenhuma escrita cruza a fronteira
    bool erase(int addr, int totalBytes=32768, int pageSize=16){
        for(int offset=0; offset < totalBytes; offset += pageSize){
            SENSOR_WIRE.beginTransmission(addr);
            SENSOR_WIRE.write((byte)(offset >> 8));
            SENSOR_WIRE.write((byte)(offset & 0xFF));

            int remaining = totalBytes - offset;
            int chunk = (remaining < pageSize) ? remaining : pageSize;

            for(int i=0; i < chunk; i++)
                SENSOR_WIRE.write((byte)0xFF);

            if(SENSOR_WIRE.endTransmission() != 0)
                return false;

            delay(10);
        }

        return true;
    }
};

#endif

