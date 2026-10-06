#ifndef SETTINGS_H
#define SETTINGS_H
#include "../../utils/json/index.h"
#include "../../globals/functions.h"


class Settings{
  public:
    Json<2048> params;

    void import(){
        params.download("preferences");
        
        if(params.empty())
            erase();
        
        params.print();
    }
    
    template<typename T> T get(const char* key) const {
        return params.template get<T>(key);
    }
    
    void save(){
        params.save("preferences");
    }

    bool isEnabled(const char* key){
        String value = params.template get<String>(key);
        value.trim();
        
        return (value == "false") ? false : 
               (value == "true")  ? true  : (value.toInt() > 0);
    }

    void erase(){
        Serial.println("Standard Settings Imported");
        params.clear();
        reset();
        save();
    }
    
    void reset(){
        params.data["esp_id"]    = generateID();
        params.data["sensor_id"] = "None";
        params.data["server"]  = "https://sighir.com:8000/";
        params.data["company"] = "sighir";
        params.data["telemetry"] = 2;
        params.data["last_alcohol"] = 0.0;
        params.data["last_analog"]  = 0;
        params.data["max_postpone"] = 3;
        params.data["postpone_time"] = 5;
        params.data["maneuver_time"] = 5;
        params.data["ssid"] = "Etilometro";
        params.data["passwd"] = "12345678";
        params.data["time_of_travel"]  = 10;
        params.data["number_of_tests"] = 1;
        params.data["rand_ppn_time"] = 5;
        params.data["rand_min_time"] = 2;
        params.data["enable_random"] = true;
        params.data["brightness"]   = 127;
        params.data["volume"]       = 255;
        params.data["vehicle_type"] = 0;
        params.data["camera"] = 5;
        params.data["bypass"] = false;
        params.data["blowProb"] = 0.1;
        params.data["temp_debug"] = false;
        params.data["presstream"] = false;
        params.data["lang"]  = "PT";
        params.data["wifi"]  = false;
        params.data["reset"] = 0;
    }
};

#endif