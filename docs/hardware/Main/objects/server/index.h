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

#define WIFI_CONNECT_TIMEOUT 15000   // associar + pegar IP em 2,4 GHz cheio passa de 5 s
#define WIFI_CHANNEL_RETRIES 1       // NÃO CONECTOU: TROCA O CANAL DO PRÓPRIO AP E TENTA DE NOVO (AP E ROTEADOR DIVIDEM UM RÁDIO)

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
    bool busy     = false;  // EEPROM do sensor em uso (ver Storage::read): sem handleClient() aninhado

    Text<33> wifi_ssid;    
    Text<65> wifi_passwd;
    Text<30> server_ssid;

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

    // SÓ ATÉ REINICIAR: NO BOOT VALE A CONFIG "WIFI" (WIFI AUTOMÁTICO, CONFIG PÁGINA 3)
    void set(const bool state){
        if(!state)
            return disable();

        connect(true);
    }

    void handle(){
        static Listener timer = Listener(100);
        sleeper.handle();

        if(!timer.ready())
            return;
        
        if(!enabled || sleeper.on || busy)
            return;

        network.handleClient();
        updater.handleCheck();
    }

    void start(){
        IPAddress staticIP(192, 168, 1, 2);   // IP ESTÁTICO
        IPAddress gateway(192, 168, 1, 2);    // GATEWAY ESTÁTICO IP
        IPAddress subnet(255, 255, 255, 0);

        WiFi.disconnect();   // NO CORE 3.X O STA AINDA TENTANDO A REDE ANTIGA RECUSA A NOVA (ESP_ERR_WIFI_STATE)
        WiFi.softAPConfig(staticIP, gateway, subnet);
        device->await(50);

        WiFi.softAP(server_ssid.get(), "12345678", channel, 0);
        device->await(50);

        WiFi.begin(wifi_ssid.get(), wifi_passwd.get());   // sem canal: conectado, o AP vai para o canal do roteador
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
        device->await(50);
    }

    void disable(){
        enabled = false;
        WiFi.disconnect(true);
        WiFi.setSleep(true);
        WiFi.mode(WIFI_OFF);
        device->await(50);
    }
    
    void connect(bool show=false, int retries=WIFI_CHANNEL_RETRIES){
        if(!show)
            return enable();

        auto& display = device->display;
        display.interface.msg(MSG_BLACK, lang.connectingNetwork.get());
        enable();
        showNetwork();

        const unsigned long startTime = Time::get();

        while(!connected() && Time::get() - startTime < WIFI_CONNECT_TIMEOUT)
            device->sensors.warm(100);

        bool ok = connected();

        display.interface.msg(ok ? MSG_GREEN : MSG_BLACK, ok ? lang.connected.get() : lang.notConnected.get());
        device->sensors.warm(1000);

        if(ok)
            return updater.handleCheck();

        if(retries > 0)
            return changeChannel(retries - 1);

        device->sensors.warm(1500);
    }

    // retries=0 NA TROCA PEDIDA PELO USUÁRIO: UM TOQUE, UM CANAL
    void changeChannel(int retries=0){
        auto& display = device->display;

        channel = (channel == 1)  ? 6  :
                  (channel == 6)  ? 3  :
                  (channel == 3)  ? 11 :
                  (channel == 11) ? 2  : 1;

        display.interface.msg(MSG_BLACK, lang.reconnecting.get());
        display.interface.centeredText(String(lang.configuringChannel.get()) + " " + channel, TFT_RED, display.height*0.65);
        device->await(2000);
        connect(true, retries);
    }

    void changeNetwork(){
        auto& keyboard = device->display.interface.keyboard;
        Text<65> response;   // SENHA WPA2 TEM ATÉ 64

        keyboard.draw(lang.wifiConfig.get(), lang.networkName.get(), true);
        response = keyboard.get();
        device->settings.params.set("ssid", response.get());

        keyboard.draw(lang.wifiConfig.get(), lang.networkPassword.get());
        response = keyboard.get();
        device->settings.params.set("passwd", response.get());
        device->settings.save();
        connect(true);
    }

    void showNetwork(){
        auto& display = device->display;
        display.interface.centeredText(wifi_ssid.get(),   TFT_WHITE, display.height*0.65);
        display.interface.centeredText(wifi_passwd.get(), TFT_WHITE, display.height*0.72);
    }

    bool connected(){
        return (WiFi.status() == WL_CONNECTED);
    }

    // GENERATE_204 SO DEVOLVE 204 COM INTERNET DE VERDADE: PORTAL CATIVO E ROTEADOR SEM LINK RESPONDEM OUTRA COISA
    int ping(const int timeout=2500){
        if(!connected())
            return -1;

        const unsigned long startTime = Time::get();
        HTTPClient http;

        http.begin("http://connectivitycheck.gstatic.com/generate_204");
        http.setConnectTimeout(timeout);
        http.setTimeout(timeout);

        const int code = http.GET();
        http.end();
        return (code == 204) ? (int) (Time::get() - startTime) : -1;
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

    void send(const char* response, const int code=200){
        sleeper.touch();
        network.sendHeader("Access-Control-Allow-Origin", "*");
        network.send(code, "text/plain", response);
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