#ifndef STORAGE_SCREENS_H
#define STORAGE_SCREENS_H
#include "../../../../device/lang/index.h"

template <typename Parent> class StorageScreens{
  private:
    Parent* device;

  public:
    StorageScreens(Parent* dev):    
        device(dev){}

    void sensorFail(){
        device->display.interface.alert(lang.sensorBadContact.get(), lang.checkConnection.get(), 2, 6000);
        device->await(3000);
    }
    
    void eepromFail(){
        device->display.interface.alert(lang.sensorNoEeprom.get(), lang.maintenanceReq.get(), 2, 6000);
        device->await(3000);
    }
};

#endif