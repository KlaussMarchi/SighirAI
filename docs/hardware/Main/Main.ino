#include "device/index.h"
#include "device/lang/index.h"
Device device{"v6.4.8"};

const char* getLang(){
    return device.settings.params.template get<const char*>("lang");
}

void setup(){
    Serial.begin(115200);
    delay(700);

    device.sensors.pressure.debug = false;
    device.sensors.dht.debug      = false;
    device.sensors.alcohol.debug  = false;
    device.sensors.alcohol.bypass = false;
    device.test.alcohol_debug     = false;
    device.setup();
}

void loop(){
    device.tasks.handle();
}
