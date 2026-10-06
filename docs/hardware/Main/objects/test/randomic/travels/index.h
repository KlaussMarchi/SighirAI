#ifndef TRAVELS_H
#define TRAVELS_H
#include "../../../../utils/array/index.h"


template <typename Parent> class Travels{
  private:
    Parent* device;

  public:
    Array<10> buffer;
    int baseTime, minTime;
    int mean, timeout;
    bool started, endded;

    Travels(Parent* dev):
        device(dev){}

    void setup(){
        buffer.download("random");
        mean = getMeanTime();
        baseTime = device->settings.template get<int>("time_of_travel")*60*1000;
        minTime  = device->settings.template get<int>("rand_min_time")*60*1000;
        timeout  = device->settings.template get<int>("maneuver_time")*60*1000;
    }

    void update(){
        auto& vehicle = device->vehicle;
        started = (vehicle.driving  && vehicle.ignition.getTime() > 60000);
        endded  = (!vehicle.driving && vehicle.ignition.getTime() > timeout);
    }

    void increment(){
        auto drivingTime = device->vehicle.ignition.getTime();
        
        if(drivingTime < minTime)
            return;

        buffer.append(drivingTime/60/1000);
        buffer.save("random");
        mean = getMeanTime();
    }

    int getMeanTime(){
        if(!buffer.isFull || baseTime == 5*60*1000)
            return baseTime;

        return (int) buffer.getMean()*60*1000;
    }
};

#endif