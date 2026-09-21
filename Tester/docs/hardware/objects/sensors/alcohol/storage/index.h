#ifndef STORAGE_SENSOR_H
#define STORAGE_SENSOR_H
#include <Arduino.h>
#include <Wire.h>
#include "blows/index.h"
#include "../../../../utils/text/index.h"


template <typename Parent> class Storage{
  private:
    Parent* device;

  public:
    int sensor_addr = (0x48);
    int eeprom_addr = (0x50);

    Blows<Parent> blows;
    Text<25> calibration_date;
    Text<256> coefs;
    Text<25> id;
    bool has_coefs;
    float a, b, c, d;
    int zero;

    Storage(Parent* dev):
        device(dev),
        blows(dev){}

    void setup(){
        update();
        Serial.println("id: "    + id.toString());
        Serial.println("coefs: " + coefs.toString());
        Serial.println("blows: " + String(blows.value));
        Serial.println("zero: "  + String(zero));
        Serial.println("a: " + String(a));
        Serial.println("b: " + String(b));
        Serial.println("c: " + String(c));
        Serial.println("d: " + String(d));

        if(id.length() < 10)
            return;

        if(!id.equals(device->settings.template get<String>("sensor_id")))
            device->telemetry.event("$ETEV36" + id.toString() + "!");

        device->settings.params.set("sensor_id", id.get());
        device->settings.save();
    }

    void update(){
        if(device->sensors.alcohol.debug)
            return;

        id.set(read(0, 19));
        id.set(0, 'E');

        coefs.set(read(19, 170));
        coefs.set(coefs.substring(coefs.indexOf('{'), coefs.indexOf(';')).get());

        StaticJsonDocument<256> data;
        deserializeJson(data, coefs.buffer);
        a = data["c1"].as<float>();
        b = data["c2"].as<float>();
        c = data["c3"].as<float>();
        d = data["c4"].as<float>();
        has_coefs = (a > 0 && b > 0 && c > 0 && d > 0);

        calibration_date = data["timestamp"].as<String>();
        zero = (data["zero"].as<int>() > 0) ? data["zero"].as<int>() : 20000;
        blows.update();
    }
    
    bool writeByte(int addr, byte val){
        Wire.beginTransmission(eeprom_addr);
        Wire.write((byte)(addr >> 8));   // MSB
        Wire.write((byte)(addr & 0xFF)); // LSB

        Wire.write(val);
        byte error = Wire.endTransmission();

        device->await(10);
        return (error == 0);
    }

    byte readByte(int addr){
        byte rData = 0xFF;
        
        Wire.beginTransmission(eeprom_addr);
        Wire.write((byte)(addr >> 8));   // MSB
        Wire.write((byte)(addr & 0xFF)); // LSB
        byte error = Wire.endTransmission(false);

        if(error != 0)
            return rData;
        
        Wire.requestFrom(eeprom_addr, 1);

        if(Wire.available())
            rData = Wire.read();

        device->await(10);
        return rData;
    }

    String read(int startIndex, int endIndex){
        String data = "";
        
        for(int i=startIndex; i<endIndex; i++){
            byte byteVal = readByte(i);
            char charVal = (char) byteVal;
            data += String(charVal);
        }

        return data;
    }

    bool write(String data, int startIndex) {
        for(int i=0; i<data.length(); i++) {
            byte val = (byte) data.charAt(i);

            if(!writeByte(startIndex + i, val))
                return false;
        }

        return true;
    }

    bool genCoefs(String data){
        auto& eeprom = device->sensors.alcohol.eeprom;
        data = data.substring(data.indexOf("$")+1, data.indexOf("!"));

        if(!eeprom.check(eeprom_addr, 1500))
            return false;
        
        int x = 0;
        while(!write(data, 0))
            if(x++ == 5)
                return false;

        setup();
        return true;
    }

};

#endif