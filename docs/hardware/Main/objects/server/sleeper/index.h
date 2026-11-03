#ifndef SERVER_SLEEPER_H
#define SERVER_SLEEPER_H
#include <Arduino.h>
#include <esp_wifi.h>
#include <WiFi.h>

// 80MHz é a menor frequência que mantém o APB em 80MHz: I2C, PWM do buzzer, SPI da tela e UARTs seguem
// iguais. O esp_pm_configure() não serve: o gerenciamento de energia vem desligado no core do Arduino
#define SLEEP_CPU_MHZ 80


template <typename Parent> class ServerSleeper{
  private:
    Parent* device;
    bool wifi = false;   // Wi-Fi estava ligado quando dormiu: volta ligado ao acordar

  public:
    bool on = false;
    int frequency = F_CPU / 1000000;
    unsigned long lastRequest = 0;

    ServerSleeper(Parent* dev):
        device(dev){}

    // dorme após 5 min com a tela apagada e sem o app conectado (ele consulta /STATUS a cada 5s)
    void handle(){
        static const int timeout = 5*60*1000;
        static auto& display     = device->display;
        const unsigned long idle = (lastRequest > display.timeOff) ? lastRequest : display.timeOff;

        if(on)
            delay(10);

        if(on && display.on)
            return end();

        if(!on && !display.on && Time::get() - idle > timeout)
            return start();
    }

    void touch(){
        lastRequest = Time::get();
    }

    void start(){
        on   = true;   // antes do disable(): o await() dele chama o handle() de novo
        wifi = device->server.enabled;

        if(wifi)
            device->server.disable();

        setCpuFrequencyMhz(SLEEP_CPU_MHZ);
        frequency = getCpuFrequencyMhz();
        Serial.println("Sleeper Started: " + String(frequency) + " MHz");
    }

    void end(){
        on = false;    // antes do enable(): o await() dele chama o handle() de novo
        setCpuFrequencyMhz(F_CPU / 1000000);
        frequency = getCpuFrequencyMhz();

        if(wifi && !device->server.enabled)
            device->server.enable();

        Serial.println("Sleeper Endded: " + String(frequency) + " MHz");
    }
};

#endif
