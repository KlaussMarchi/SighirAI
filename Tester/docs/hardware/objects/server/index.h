#ifndef ESPSERVER_H
#define ESPSERVER_H
#include "../../device/lang/index.h"
#include <Arduino.h>
#include <esp_wifi.h>
#include <WiFi.h>
#include <WebServer.h>
#include <HTTPClient.h>
#include "../../utils/time/index.h"
#include "../../utils/text/index.h"
#include "../../utils/listener/index.h"
#include "routes/index.h"
#include "updater/index.h"
#include "sleeper/index.h"


template <typename Parent> class EspServer{
  private:
    Parent* device;

  public:
    ServerRoutes<Parent> routes;
    ServerSleeper<Parent> sleeper;
    Updater<Parent> updater;    
    
    WebServer network{80};
    Text<30> URL;
    int channel   = 1;
    bool enabled  = false;
    bool sleeping = false;

    Text<30> wifi_ssid, server_ssid;
    Text<30> wifi_passwd;

    EspServer(Parent* dev):
        device(dev),
        updater(dev),
        routes(dev),
        sleeper(dev){}
    
    void setup(){
        enabled = enabled ? true : device->settings.isEnabled("wifi");
        URL     = device->settings.template get<const char*>("server");
        wifi_ssid   = device->settings.template get<const char*>("ssid");
        wifi_passwd = device->settings.template get<const char*>("passwd");
        server_ssid = getSSID();

        if(!enabled)
            return;

        esp_wifi_set_ps(WIFI_PS_NONE);
        WiFi.setTxPower(WIFI_POWER_19_5dBm);
    }

    void set(const bool state){
        device->settings.params.set("wifi", state);
        device->settings.save();

        if(!state)
            return disable();

        connect(true);
    }

    void handle(){
        static Listener timer = Listener(100);
        sleeper.handle();

        if(!timer.ready())
            return;
        
        if(!enabled || sleeper.on)
            return;
        
        network.handleClient();
        updater.handleCheck();
    }

    void start(){
        IPAddress staticIP(192, 168, 1, 2);   // IP ESTÁTICO
        IPAddress gateway(192, 168, 1, 2);    // GATEWAY ESTÁTICO IP
        IPAddress subnet(255, 255, 255, 0);

        WiFi.softAPConfig(staticIP, gateway, subnet);
        device->await(50);

        WiFi.softAP(server_ssid.get(), "12345678", channel, 0);
        device->await(50);

        WiFi.begin(wifi_ssid.get(), wifi_passwd.get(), channel);
        device->await(50);

        routes.setup();
        network.begin();

        Serial.print("SERVER STARTED: ");
        Serial.println(WiFi.softAPIP());
        Serial.println("Channel: " + String(channel));
        Serial.println();
    }

    void enable(){
        enabled = true;
        WiFi.setSleep(false);
        WiFi.mode(WIFI_AP_STA);
        setup();
        start();

        if(!connected())
            WiFi.reconnect();

        device->await(50);
    }

    void disable(){
        enabled = false;
        WiFi.disconnect(true);
        WiFi.setSleep(true);
        WiFi.mode(WIFI_OFF);
        device->await(50);
    }
    
    void connect(bool show=false, bool tryChannel=true){
        if(!show)
            return enable();

        auto& display = device->display;
        display.interface.msg(MSG_WHITE, lang.connectingNetwork.get());
        enable();
        
        display.interface.centeredText(wifi_ssid.get(),   TFT_BLACK, display.height*0.65);
        display.interface.centeredText(wifi_passwd.get(), TFT_BLACK, display.height*0.72);
        
        device->sensors.warm(5000);
        bool ok = connected();
        
        display.interface.msg(ok ? MSG_GREEN : MSG_WHITE, ok ? lang.connected.get() : lang.notConnected.get());
        device->sensors.warm(1000);

        if(ok)
            return updater.handleCheck(true);
        else
            device->sensors.warm(1500);
        
        if(show && tryChannel)
            changeChannel();
    }

    void changeChannel(){
        device->display.interface.msg(MSG_WHITE, lang.configuringChannel.get());
        wait(1500);

        channel = (channel == 1)  ? 6  :
                  (channel == 6)  ? 3  :
                  (channel == 3)  ? 11 :
                  (channel == 11) ? 2  : 1;
        
        device->display.interface.alert(lang.changingChannel.get(), lang.configuringFor.get() + String(channel), MSG_WHITE);
        connect(true, false);
        wait(1500);
    }
    
    bool connected(){
        return (WiFi.status() == WL_CONNECTED);
    }

    void wait(const int timeout){
        const unsigned long startTime = Time::get();

        while(Time::get() - startTime < timeout)
            handle();
    }

    const char* getSSID(){
        static Text<20> ssid;

        if(device->id.equals("admin_sighir"))
            return "SIGHIR ADMIN";

        ssid.set("SIGHIR - ");
        for(int x=0; x<7; x++)
            ssid += device->id.buffer[x];
        
        return ssid.get(); 
    }

    void send(const char* response){
        network.sendHeader("Access-Control-Allow-Origin", "*");
        network.send(200, "text/plain", response);
    }

    String post(const String &route, const String &data, const int timeout=7000){
        String url = URL.toString() + route;
        HTTPClient http;

        http.begin(url);
        http.addHeader("Content-Type", "application/json");
        http.setTimeout(timeout);
        
        const int code = http.POST(data);
        const bool success = (code >= 200 && code < 700);
        String payload     = success ? http.getString() : "-1";

        if(!success)
            Serial.println("http error code: " + String(code));

        http.end();
        return payload;
    }

    String get(const String &route, const int timeout=7000){
        String url = URL.toString() + route;
        HTTPClient http;

        http.begin(url);
        http.setTimeout(timeout);

        const int code = http.GET();
        const bool success = (code >= 200 && code < 300);
        String payload     = success ? http.getString() : "-1";

        if(!success)
            Serial.println(url + " | http error code: " + String(code));
        
        http.end();
        Serial.println(payload);
        return payload;
    }
};


#endif