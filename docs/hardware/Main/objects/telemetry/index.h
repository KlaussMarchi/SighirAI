#ifndef TELEMETRY_H
#define TELEMETRY_H
#include <Arduino.h>
#include "../../globals/constants.h"
#include "../../globals/functions.h"
#include "protocol/index.h"
#include "serial/index.h"

#include "modes/suntech/index.h"
#include "modes/mix/index.h"
#include "modes/mix2/index.h"
#include "modes/entrack/index.h"

#define CMD_MAX_SIZE 256
#define TX_PIN 26
#define RX_PIN 33


template <typename Parent> class Telemetry{
  private:
    Parent* device;
    
  public:
    NextSerial<CMD_MAX_SIZE> serial = NextSerial<CMD_MAX_SIZE>(RX_PIN, TX_PIN);
    Text<CMD_MAX_SIZE> last_cmd;
    Protocol<Parent> protocol;
    Text<64> response;
    byte type  = 0;
    
    Suntech<Parent> suntech;
    Entrack<Parent> entrack;
    MIX2<Parent> mix2;
    MIX<Parent> mix;
    
    Telemetry(Parent* dev):
        device(dev),
        protocol(dev),
        suntech(dev),
        entrack(dev),
        mix(dev),
        mix2(dev){}
    
    void setup(){
        type  = device->settings.template get<byte>("telemetry");
        serial.setup();
        
        if(type == SUNTECH_TEL)
            suntech.setup();

        if(type == MIX_TEL)
            mix.setup();

        if(type == MIX_TEL_NEW)
            mix2.setup();

        if(type == ENTRACK_TEL)
            entrack.setup();

        event("$ETEV08!");
        response.reset();
    }
    
    void handle(){
        serial.listen();
        handleProtocol();
        handleRequest();
        
        if(response.length() > 0)
            event(response.get());
        
        if(serial.available)
            last_cmd = serial.command.get();
        
        handleOperation(); 
        serial.reset();
    }

    void handleProtocol(){
        if(type == SUNTECH_TEL)
            suntech.check();

        if(type == MIX_TEL)
            mix.check();

        if(type == MIX_TEL_NEW)
            mix2.check();

        if(type == ENTRACK_TEL)
            entrack.check();

        if(serial.available)
            protocol.check();
    }

    void handleRequest(){
        if(type == SUNTECH_TEL)
            suntech.request();

        if(type == MIX_TEL)
            mix.request();

        if(type == MIX_TEL_NEW)
            mix2.request();

        if(type == ENTRACK_TEL)
            entrack.request();
    }
    
    void handleOperation(){
        if(type == SUNTECH_TEL)
            suntech.handle();

        if(type == MIX_TEL)
            mix.handle();

        if(type == MIX_TEL_NEW)
            mix2.handle();

        if(type == ENTRACK_TEL)
            entrack.handle();
    }
    
    void event(const char* value, bool onlyApp=false){
        device->logs.add(value);

        if(!onlyApp)
            serial.send(value, true);
        
        response.reset();
    }
    
    void event(const String& value, bool onlyApp=false){
        device->logs.add(value.c_str());

        if(!onlyApp)
            serial.send(value.c_str(), true);
        
        response.reset();
    }

    const char* toText(){
        if(type == SUNTECH_TEL)
            return "Suntech";

        if(type == MIX_TEL)
            return "MIX";

        if(type == MIX_TEL_NEW)
            return "MIX 2.0";

        if(type == ENTRACK_TEL)
            return "Entrack";

        return "None";
    }

    bool working(){
        return (Time::get() - serial.lastAckTime < 15000);
    }
};

#endif 
