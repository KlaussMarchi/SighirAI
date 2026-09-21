#include "device/index.h"
#include "device/lang/index.h"
Device device{"v6.4.0"};

const char* getLang(){
    return device.settings.template get<const char*>("lang");
}

void setup(){
    Serial.begin(115200);
    delay(700);

    device.sensors.pressure.debug = false;
    device.sensors.dht.debug      = false;
    device.sensors.alcohol.debug  = true;
    device.sensors.alcohol.bypass = true;
    device.test.alcohol_debug     = false;
    device.setup();
}

void loop(){
    device.tasks.handle();
}
