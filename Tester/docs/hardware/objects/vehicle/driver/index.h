#ifndef DRIVER_H
#define DRIVER_H
#include <Arduino.h>


template<typename Parent> class Driver{
  public:
    bool drunk;
    bool allowed;
    Parent* device;
  
    Driver(Parent* dev):
        device(dev){}

    void alert(){

    }

};

#endif