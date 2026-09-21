#ifndef LOGS_H
#define LOGS_H
#include <Arduino.h>
#include "../../utils/notes/index.h"


template<typename Parent> class Logs{
  private:
    Parent* device;

  public:
    Notes notes = Notes("/logs.txt");

    Logs(Parent* dev):
        device(dev){}

    void setup(){
        notes.setup();
    }

    void erase(){
        notes.erase();
    }

    void add(const char* log){
        if(strlen(log) < 6)
            return;
        
        notes.append(log);

        if(notes.length() > 5000)
            notes.droplines(5);
    }

    String get(){
        String response = notes.readlines(10);
        notes.droplines(10);
        return response;
    }
};

#endif