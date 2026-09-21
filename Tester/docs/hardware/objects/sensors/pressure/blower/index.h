#ifndef BLOWER_H
#define BLOWER_H
#include <Arduino.h>
#include <HX711.h>
#include "../../../../utils/time/index.h"
#include "../../../../utils/filters/index.h"


template <typename Parent> class Blower{
  private:
    Smoother<20> TareFilter;
    Parent* pressure;

  public:
    static const int STATES  = 5;
    static const int CLASSES = 2;
    float buffer[STATES] = {0};

    unsigned long startBlow = Time::get();
    bool state    = true;
    int tolerance = 200;

    Blower(Parent* press):
        pressure(press){}

    float SCALER_MEAN[STATES] = { 0.0018389100739659044, 0.0030949022176906776, 0.004429431722804109, 0.005842514536957158, 0.007334352102099594 };
    float SCALER_STD[STATES]  = { 4.400394120593558, 4.40497188140637, 4.410134473103949, 4.415915658021759, 4.422348784563995 };

    float centroids[CLASSES][STATES] = {
        { -0.25719673289801204, -0.263008668861697, -0.26479906358047023, -0.2625961369098391, -0.2566773353614246 },
        { 1.4624568747232007, 1.495504361795721, 1.5056847985199178, 1.4931586469717437, 1.4595035071219191 },
    };

    void setTolerance(float value){
        tolerance = value*1000.00;
    }

    int update(float value){
        for(int i = STATES - 1; i > 0; i--)
            buffer[i] = buffer[i - 1];

        float minDistance = 3.4028235E38; 
        int bestCluster   = -1;
        buffer[0] = value;

        for(int k = 0; k < CLASSES; k++){
            float currentDistance = 0;
            
            for(int i = 0; i < STATES; i++){
                float normalized = (buffer[i] - SCALER_MEAN[i]) / SCALER_STD[i];
                float diff       = (normalized - centroids[k][i]);
                currentDistance += diff * diff;
            }

            if (currentDistance < minDistance) {
                minDistance = currentDistance;
                bestCluster = k;
            }
        }
        
        return bestCluster;
    }

    void handle(){
        static Listener timer = Listener(100);

        if(!timer.ready())
            return;

        if(pressure->debug)
            {state = true; return;}
        
        const float value  = pressure->get();
        const float mean   = TareFilter.update(value);

        const int cluster  = update(value - mean);
        const bool blowing = (cluster == 1);
        
        if(blowing){
            startBlow = Time::get();
            state = true;
        }
        
        if(!blowing && Time::get() - startBlow > tolerance){
            state = false;
        }
    }

    bool get(){
        handle();
        return state;   
    }

    void reset(){
        startBlow = Time::get();
        state = false;
    }
};

#endif