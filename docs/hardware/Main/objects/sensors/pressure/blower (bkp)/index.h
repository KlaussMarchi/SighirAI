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

    float SCALER_MEAN[STATES] = { 0.011171408315891513, 0.012140872459921065, 0.013173837164200156, 0.014270965855033247, 0.015433693710034602 };
    float SCALER_STD[STATES]  = { 4.276303846653115, 4.2799427860051935, 4.284047656842635, 4.288645554822134, 4.293763201181655 };

    float centroids[CLASSES][STATES] = {
        { -0.2500208453364381, -0.255404187181547, -0.25699824071427047, -0.2548229276215755, -0.24911336882536037 },
        { 1.5331191835738258, 1.5661296497346222, 1.5759043309111995, 1.5625653861996005, 1.527554568967777 },
    };

    float buffer[STATES] = {0};

    unsigned long startBlow = Time::get();
    bool state    = true;
    int tolerance = 200;

    Blower(Parent* press):
        pressure(press){}

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

            if(currentDistance >= minDistance)
                continue;

            // ATUALIZANDO MELHOR CLUSTER JA QUE A DISTANCIA DIMINUIU
            minDistance = currentDistance;
            bestCluster = k;
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