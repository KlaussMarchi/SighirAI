#ifndef PASS_H
#define PASS_H
#include "../../../device/lang/index.h"
#define MAX_TRIES 3


template <typename Parent> class Pass{
  private:
    Parent* device;
  
  public:
    int index = 0;
    bool bypass = false;
    bool active   = false;
    bool enabled  = true;
    bool liberated = false;

    Pass(Parent* dev):
        device(dev){}

    void setup(){
        bypass = device->settings.isEnabled("bypass");
        reset();
    }

    void reset(){
        active = false;
        index  = 0;
    }

    bool required(){
        return (device->test.had_alcohol);
    }
    
    void start(){
        const int option = device->display.interface.inputs.trichoices("Contrassenha", lang.performAnotherTest.get(), lang.turnOffDisplayStr.get());
        active   = true;
        Serial.println(option);

        if(option == 1) // outro teste
            return device->test.start(true);

        if(option == 2) // desligar display
            return device->display.turnOFF();
        
        while(!bypass)
            if(handleStandard())
                break;

        while(bypass)
            if(handleBypass())
                break;

        active = false;
    }

    bool handleStandard(){
        auto& display = device->display;
        const int generated = gen();

        display.interface.keyboard.draw("Contrassenha", String(generated).c_str());
        const int written = display.interface.keyboard.get().toInt();

        device->telemetry.event("$ETEV40" + String(written) + "!");
        index = (index + 1);
        
        if(check(generated, written)){
            liberate();
            return true;
        }
        
        display.interface.font.reset();
        display.interface.msg(MSG_RED, lang.incorrectPassword.get());
        display.sound.badBeep();

        if(index < MAX_TRIES && display.interface.inputs.boolean(lang.tryAgain.get()))
            return false;

        display.turnOFF();
        return true;
    }
    
    bool handleBypass(){
        auto& display = device->display;
        const int written = display.interface.keyboard.get().toInt();

        device->telemetry.event("$ETEV40" + String(written) + "!");
        index = (index + 1);
        
        if(written == 5){
            liberate();
            return true;
        }
        
        display.interface.font.reset();
        display.interface.msg(MSG_RED, lang.invalidValue.get());
        display.sound.badBeep();

        if(index == MAX_TRIES)
            return false;

        if(display.interface.inputs.boolean(lang.tryAgain.get()))
            return false;

        return true;
    }

    void liberate(){
        device->telemetry.event("$ETEV26!");
        device->vehicle.unblock();
        device->vehicle.driving  = true;
        device->test.had_alcohol = false;
        device->test.postpone.reset();
        liberated = true;
        reset();
    }

    bool check(int pass, int counter){
        int reverse = (counter - 3) / 2;
    
        if(reverse != pass)
            reverse = ((counter * 10) - 3) / 2;
        
        if(reverse != pass){
            counter = (counter * 10); 
    
            for(int i = 0; i < 9; ++i){
                counter = (counter + 1);
                reverse = (counter - 3) / 2;
    
                if(reverse == pass)
                    return true;
            }
    
            return false; 
        }
    
        return true; 
    }

    int gen(){
        warmRandomSeed();
        return 1000 + rand() % 9000;
    }
};

#endif