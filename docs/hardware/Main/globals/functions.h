#ifndef FUNCTIONS_H
#define FUNCTIONS_H
#include <ArduinoJson.h>


float mapFloat(float x, float Xo, float X, float Yo, float Y){
    float minVal = min(Yo, Y);
    float maxVal = max(Yo, Y);
    float func = (Y-Yo)/(X-Xo)*(x-Xo)+Yo;

    if(func < minVal)
        return minVal;

    if(func > maxVal)
        return maxVal;

    return func;
}

int parsePassword(int num){
    if (num == 0)
        return 1784;
    
    num = num*2 + 3;

    if(num > 9999)
        num = int(num / 10);

    if(num < 1000)
        num = int(num/2 + 1784);
    
    return num;
}

String randomIntegers(int size, int numTries){
    String response;
    response.reserve(size + 2);
    
    for(int x=0; x<size; x++)
        response.concat(random(10));
    
    return (numTries == 0) ? response : randomIntegers(size, numTries - 1);
}

void warmRandomSeed(){
    randomSeed(esp_timer_get_time());
    for(int x=0; x<30; x++) rand();
    for(int x=0; x<30; x++) random(100);
    delay(100);
}

String generateID(){
    warmRandomSeed();
    const int numTries = random(10, 25);
    String id = "MIC" + randomIntegers(12, numTries);

    const int senha = id.substring(3, 7).toInt();
    const int contrassenha = parsePassword(senha);
    return id + String(contrassenha);
}

String jsonToString(const JsonDocument& jsonObj){
    String jsonString;
    serializeJson(jsonObj, jsonString); 
    return jsonString;
}

bool stringToJson(String &jsonString, JsonDocument& doc){
    DeserializationError error = deserializeJson(doc, jsonString);

    if(error)
        return false;

    return true;
}

size_t base64Decode(const char* input, uint8_t* output, const int size){
    auto decodeChar = [](char c) -> int {
        if (c >= 'A' && c <= 'Z') return c - 'A';
        if (c >= 'a' && c <= 'z') return c - 'a' + 26;
        if (c >= '0' && c <= '9') return c - '0' + 52;
        if (c == '+') return 62;
        if (c == '/') return 63;
        return -1;
    };

    size_t outputIndex = 0;
    int val  = 0;
    int valb = -8; 

    for (size_t i = 0; i<size; i++){
        if (isspace(static_cast<unsigned char>(input[i])))
            continue;

        if (input[i] == '=')
            break;

        int d = decodeChar(input[i]);

        if (d == -1)
            continue;

        val  = (val << 6) + d;
        valb += 6;

        if (valb < 0)
            continue;
            
        output[outputIndex++] = static_cast<uint8_t>((val >> valb) & 0xFF);
        valb -= 8;
    }

    return outputIndex;
}

String formatTimeString(unsigned long timeMs){
    const int activeTime = ((float) timeMs)/1000.00;

    if(activeTime < 60)
        return String(activeTime) + " seg";

    if(activeTime < 3600)
        return String(activeTime / 60) + " min";
    
    return String(activeTime / 3600) + " h";
}

int roundDecimal(float number) {
    return round(number / 10.0) * 10;
}

#endif