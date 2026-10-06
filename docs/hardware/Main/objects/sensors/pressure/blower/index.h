#ifndef BLOWER_H
#define BLOWER_H
#include <Arduino.h>
#include "../../../../utils/time/index.h"
#include "../../../../utils/listener/index.h"
#include "../../../../utils/filters/index.h"
#include "model.h"


template <typename Parent> class Blower{
  private:
    Smoother<BlowerModel::WINDOW> tare;
    float states[BlowerModel::STATES] = {0};
    bool seeded = false;
    Parent* pressure;

  public:
    unsigned long startBlow = Time::get();
    BlowerModel model;
    bool state    = true;
    int tolerance = BlowerModel::TOLERANCE;
    int confirm   = BlowerModel::CONFIRM;
    int counter   = 0;

    Blower(Parent* press):
        pressure(press){}

    void setTolerance(float value){
        tolerance = value*1000.00;
    }

    bool update(float value){
        if(!seeded){
            seeded = true;

            for(int i=0; i<BlowerModel::WINDOW; i++)
                tare.update(value);
        }

        for(int i=BlowerModel::STATES-1; i>0; i--)
            states[i] = states[i-1];

        states[0] = value - tare.update(value);
        return model.get(states);
    }

    void handle(){
        static Listener timer = Listener(100);

        if(!timer.ready())
            return;

        if(pressure->debug)
            {state = true; return;}

        const bool blowing = update(pressure->get());

        if(blowing){
            startBlow = Time::get();

            if(++counter >= confirm)
                state = true;
        }
        else
            counter = 0;

        if(!blowing && Time::get() - startBlow > tolerance)
            state = false;
    }

    bool get(){
        handle();
        return state;
    }

    void reset(){
        startBlow = Time::get();
        counter = 0;
        state = false;
    }
};

#endif
