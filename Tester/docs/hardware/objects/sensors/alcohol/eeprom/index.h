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
};

#endif

