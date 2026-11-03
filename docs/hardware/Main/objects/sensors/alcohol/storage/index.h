#ifndef STORAGE_SENSOR_H
#define STORAGE_SENSOR_H
#include <Arduino.h>
#include <Wire.h>
#include "../eeprom/index.h"
#include "blows/index.h"
#include "../../../../utils/text/index.h"


template <typename Parent> class Storage{
  private:
    Parent* device;

  public:
    int sensor_addr = (0x48);
    int eeprom_addr = (0x50);

    // faixa realmente ocupada: id (0-19), coefs (19-170), sopros (210-220)
    static const int data_size = 256;

    Blows<Parent> blows;
    Text<25> calibration_date;
    Text<256> coefs;
    Text<25> id;
    bool has_coefs;
    float a, b, c, d;
    int zero;

    Storage(Parent* dev):
        device(dev),
        blows(dev){}

    void setup(){
        update();
        Serial.println("id: "    + id.toString());
        Serial.println("coefs: " + coefs.toString());
        Serial.println("blows: " + String(blows.value));
        Serial.println("zero: "  + String(zero));
        Serial.println("a: " + String(a));
        Serial.println("b: " + String(b));
        Serial.println("c: " + String(c));
        Serial.println("d: " + String(d));

        if(id.length() < 10)
            return;

        if(!id.equals(device->settings.template get<String>("sensor_id")))
            device->telemetry.event("$ETEV36" + id.toString() + "!");

        device->settings.params.set("sensor_id", id.get());
        device->settings.save();
    }

    void update(){
        if(device->sensors.alcohol.debug)
            return;

        // ID de 19 bytes (ETL + 16 dígitos); o legado de 18 (ETL + 15) já emenda o '{' no byte 18
        String raw = read(0, 170);
        const int split = (raw.indexOf('{') == 18) ? 18 : 19;
        const int open  = raw.indexOf('{', split);
        const int close = (open == -1) ? -1 : raw.indexOf(';', open);

        id.set(raw.substring(0, split));
        id.set(0, 'E');
        coefs.set((close == -1) ? String() : raw.substring(open, close));

        StaticJsonDocument<256> data;
        deserializeJson(data, coefs.buffer);
        a = data["c1"].as<float>();
        b = data["c2"].as<float>();
        c = data["c3"].as<float>();
        d = data["c4"].as<float>();
        has_coefs = (a > 0 && b > 0 && c > 0 && d > 0);

        calibration_date = data["timestamp"].as<String>();
        zero = (data["zero"].as<int>() > 0) ? data["zero"].as<int>() : 20000;
        blows.update();
    }
    
    bool writeByte(int addr, byte val){
        SENSOR_WIRE.beginTransmission(eeprom_addr);
        SENSOR_WIRE.write((byte)(addr >> 8));   // MSB
        SENSOR_WIRE.write((byte)(addr & 0xFF)); // LSB

        SENSOR_WIRE.write(val);
        byte error = SENSOR_WIRE.endTransmission();

        device->await(10);
        return (error == 0);
    }

    byte readByte(int addr){
        byte rData = 0xFF;
        
        SENSOR_WIRE.beginTransmission(eeprom_addr);
        SENSOR_WIRE.write((byte)(addr >> 8));   // MSB
        SENSOR_WIRE.write((byte)(addr & 0xFF)); // LSB
        byte error = SENSOR_WIRE.endTransmission(false);

        if(error != 0)
            return rData;
        
        SENSOR_WIRE.requestFrom(eeprom_addr, 1);

        if(SENSOR_WIRE.available())
            rData = SENSOR_WIRE.read();

        device->await(10);
        return rData;
    }

    // Cada byte espera 10ms num await(), que atende o servidor web: se uma rota HTTP estiver lendo o
    // sensor, o handleClient() aninhado derrubaria a conexão dela. Por isso o servidor fica pausado
    String read(int startIndex, int endIndex){
        const bool busy = device->server.busy;
        device->server.busy = true;
        String data = "";

        for(int i=startIndex; i<endIndex; i++){
            byte byteVal = readByte(i);
            char charVal = (char) byteVal;
            data += String(charVal);
        }

        device->server.busy = busy;
        return data;
    }

    bool write(String data, int startIndex) {
        const bool busy = device->server.busy;
        device->server.busy = true;
        bool ok = true;

        for(int i=0; i<data.length() && ok; i++)
            ok = writeByte(startIndex + i, (byte) data.charAt(i));

        device->server.busy = busy;
        return ok;
    }

    bool genCoefs(String data){
        auto& eeprom = device->sensors.alcohol.eeprom;
        data = data.substring(data.indexOf("$")+1, data.indexOf("!"));

        if(!eeprom.check(eeprom_addr, 1500))
            return false;
        
        int x = 0;
        while(!write(data, 0))
            if(x++ == 5)
                return false;

        setup();
        return true;
    }

    // POST /CF_SENSOR do app: "$<ID><JSON>;!". Grava no mesmo formato do cf_coefs do desktop:
    // ID + {"c1".."c4","timestamp","zero"} + ';'. Devolve nullptr ou o motivo do erro
    const char* configure(const String& request){
        const int start = request.indexOf('$');
        const int open  = request.indexOf('{');
        const int close = request.lastIndexOf('}');

        if(device->sensors.alcohol.debug)
            return "sensor em modo debug";

        if(start == -1 || open < start || close < open)
            return "formato invalido";

        String newID = request.substring(start+1, open);
        newID.trim();

        if(!isSensorID(newID))
            return "ID do sensor invalido";

        StaticJsonDocument<256> received;

        if(deserializeJson(received, request.substring(open, close+1)) || !received.is<JsonObject>())
            return "JSON invalido";

        if(!device->sensors.alcohol.eeprom.check(eeprom_addr, 1500))
            return "sensor nao encontrado";

        update();
        StaticJsonDocument<256> blob;
        const char* error = merge(received, blob, newID.equals(id.get()));

        if(error != nullptr)
            return error;

        String json;
        serializeJson(blob, json);

        if(newID.length() + json.length() + 1 > 170)   // do byte 170 em diante é o contador de sopros
            return "dados grandes demais";

        int x = 0;
        while(!write(newID + json + ";", 0))
            if(x++ == 5)
                return "falha ao gravar na EEPROM";

        setup();
        return (id.equals(newID) && coefs.equals(json)) ? nullptr : "falha na verificacao da EEPROM";
    }

    // Junta o pedido com o que já está no sensor. Sem coeficientes (o app manda {} ao gerar um ID
    // novo) mantém a calibração; para atualizar, os 4 precisam vir e ser maiores que zero
    const char* merge(JsonDocument& received, JsonDocument& blob, const bool sameID){
        static const char* keys[] = {"c1", "c2", "c3", "c4"};
        StaticJsonDocument<256> current;
        deserializeJson(current, coefs.get());
        blob.to<JsonObject>();   // sensor sem calibração ganhando ID novo grava {} (e não "null")
        int given = 0;

        for(const char* key : keys){
            JsonVariant value = received[key];
            double number;

            if(value.isNull() || (value.is<const char*>() && strlen(value.as<const char*>()) == 0))
                continue;

            if(!jsonToNumber(value, number) || number <= 0)
                return "coeficientes devem ser numeros maiores que zero";

            blob[key] = number;
            given++;
        }

        if(given > 0 && given < 4)
            return "informe os 4 coeficientes";

        if(given == 0 && sameID)
            return "nenhum coeficiente enviado";

        if(given == 0)
            for(const char* key : keys)
                if(!current[key].isNull())
                    blob[key] = current[key];

        const char* timestamp = received["timestamp"] | "";

        if(strlen(timestamp) > 0 && !isTimestamp(timestamp))
            return "data invalida";

        if(strlen(timestamp) > 0)
            blob["timestamp"] = timestamp;
        else if(!current["timestamp"].isNull())
            blob["timestamp"] = current["timestamp"];

        double zeroValue;

        if(jsonToNumber(received["zero"], zeroValue) && zeroValue > 0)
            blob["zero"] = (int) zeroValue;
        else if(!current["zero"].isNull())
            blob["zero"] = current["zero"];

        return nullptr;
    }
};

#endif