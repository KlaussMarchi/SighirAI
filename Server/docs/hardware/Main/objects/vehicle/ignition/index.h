#ifndef IGNITION_H
#define IGNITION_H
#include "../../../globals/functions.h"
#include "../../../utils/time/index.h"


class Ignition{
  public:
    unsigned long startTime;
    bool changed;
    bool on, off;

    Ignition(){
        changed = false;
        on  = false;
        off = true;
        startTime = Time::get();
    }

    void set(const bool value){
        changed = (value != on);
        on  = value;
        off = !value;

        if(changed)
            startTime = Time::get();
    }

    unsigned long getTime(){
        return (Time::get() - startTime);
    }

    void resetTime(){
        startTime = Time::get();
    }

    void reset(){
        changed = false;
    }
};


#endif