#ifndef EEPROM_H
#define EEPROM_H
#include <Arduino.h>
#include <Wire.h>
#include "../../../../utils/time/index.h"


class EEPROM{
  public:
    bool connect(int addr){
        Wire.beginTransmission(addr);

        if(Wire.endTransmission() == 0)
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
            Wire.beginTransmission(addr);
            Wire.write((byte)(offset >> 8));
            Wire.write((byte)(offset & 0xFF));

            int remaining = totalBytes - offset;
            int chunk = (remaining < pageSize) ? remaining : pageSize;

            for(int i=0; i < chunk; i++)
                Wire.write((byte)0xFF);

            if(Wire.endTransmission() != 0)
                return false;

            delay(10);
        }

        return true;
    }
};

#endif

