#ifndef PRESSURE_H
#define PRESSURE_H
#include "../../../device/lang/index.h"
#include <Arduino.h>
#include <HX711.h>
#include "../../../utils/time/index.h"
#include "../../../utils/listener/index.h"
#include "blower/index.h"

#define LOADCELL_DOUT_PIN 4   // SENSOR DE PRESSÃO
#define LOADCELL_SCK_PIN  5   // SENSOR DE PRESSÃO


template <typename Parent> class Pressure{
  private:
    Parent* device;
    HX711 scale;

  public:
    float blowProb = 0.00;
    bool debug     = false;
    bool streaming = false;
    Blower<Pressure> blower;
       
    Pressure(Parent* dev):
        device(dev),
        blower(this){}

    void setup(){
        blowProb  = device->settings.template get<float>("blowProb");
        streaming = device->settings.isEnabled("presstream"); 

        if(blowProb == 0.0)
            blowProb = 0.10;
        
        if(!debug)
            scale.begin(LOADCELL_DOUT_PIN, LOADCELL_SCK_PIN);
        
        blower.setTolerance(blowProb);
        tare();
    }

    void stream(){
        static unsigned long startTime = Time::get();
        static Listener timer = Listener(100);
        blower.handle();

        if(!timer.ready())
            return;

        static char buffer[256];
        int n = snprintf(buffer, sizeof(buffer), "{\"time\":%.3f,\"pressure\":%.3f,\"blow\":%d}", 
                        float(Time::get() - startTime)/1000.00, 
                        get(), 
                        blower.state); 
                        
        device->telemetry.serial.uart->write(buffer, n);
        device->telemetry.serial.uart->write('\n');
    }
    
    bool check(int timeout=0){
        const unsigned long startTime = Time::get();
        
        do{
            if(scale.is_ready())
                return true;
        }
        while(Time::get() - startTime < timeout);

        return false;
    }

    float get(){
        static unsigned long startTime;
        static const byte xSize=2, ySize=3;
        static float Xn[xSize] = {0};
        static float Yn[ySize] = {0};
        static bool seeded = false;

        if(Time::get() - startTime < 100)
            return Yn[0];

        startTime = Time::get();

        if(!scale.is_ready())
            return Yn[0];

        const float reading = scale.read() / 10000.0;

        if(!seeded){
            for(byte n=0; n<xSize; n++) Xn[n] = reading;
            for(byte n=0; n<ySize; n++) Yn[n] = reading;

            seeded = true;
            return Yn[0];
        }

        for(byte n=xSize-1; n>0; n--)
            Xn[n] = Xn[n-1];

        for(byte n=ySize-1; n>0; n--)
            Yn[n] = Yn[n-1];

        Xn[0] = reading;
        Yn[0] = Xn[0]*(0.016239) + Xn[1]*(0.014858) + Yn[1]*(1.734903) + Yn[2]*(-0.766000);
        return Yn[0];
    }

    void warm(const int timeout=0){
        const unsigned long startTime = Time::get();

        do{
            device->server.handle();
            blower.handle();
        }
        while(Time::get() - startTime < timeout);
        blower.reset();
    }

    void tare(bool show=false){
        const unsigned long startTime = Time::get();
        const bool blowing = blower.state;
        blower.reset();
        
        if(debug || !blowing)
            return warm(400);

        if(show)
            device->display.interface.msg(MSG_BLACK, lang.calibratingPressure.get());
        
        while(Time::get() - startTime < 1500)
            device->sensors.warm();

        if(blower.state)
            return tare();
    }

    bool getFirstBreath(){
        const unsigned long startTime = Time::get();
    
        while(!blower.state && Time::get() - startTime < 25000)
            blower.handle();
        
        if(blower.state)
            device->display.sound.handleBeep();
        
        return blower.state;
    }
};

#endif