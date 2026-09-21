#ifndef MENU_H
#define MENU_H
#include "../../../../device/lang/index.h"
#include <LovyanGFX.hpp>
#include <WiFi.h>
#include "../../../../assets/logos/family_logo.h"

struct Page{
    String label;
    String icon;
    byte name;
    int maxPages;
    int startX;
    int startY;
    int width;
    int height;
};

template <typename Parent> class Menu{
  private:
    Parent* device;
    LGFX& lcd;

  public:
    int currPage, currSubpage, currMaxPages;
    int submenuContainerStartY;
    int submenuContainerHeight;
    int submenuItemListHeight;
    bool active;
    Page idPage;
    Page infoPage;
    Page configPage;
    Page exitPage;

    Menu(Parent* dev):
        device(dev),
        lcd(dev->display.lcd){}

    void setup(){
        auto& display = device->display;

        const int width  = lcd.width()  * 0.40;
        const int height = lcd.height() * 0.25;
        submenuContainerStartY = lcd.height() * 0.15;
        submenuContainerHeight = lcd.height() * 0.72;
        submenuItemListHeight  = lcd.height() * (0.72 / 5);
        
        idPage.name   = ID_PAGE;
        idPage.label  = "ID";
        idPage.icon   = u8"\uf02d";
        idPage.startX = lcd.width()  * 0.05; 
        idPage.startY = lcd.height() * 0.2; 
        idPage.width  = width;
        idPage.height = height;
        idPage.maxPages = 2;
        
        infoPage.name   = INFO_PAGE;
        infoPage.label  = "INFO";
        infoPage.icon   = u8"\uee59";
        infoPage.startX = lcd.width()  * 0.55;  
        infoPage.startY = lcd.height() * 0.2; 
        infoPage.width  = width;
        infoPage.height = height;
        infoPage.maxPages = 4;

        configPage.name   = CONFIG_PAGE;
        configPage.label  = "CONFIG";
        configPage.icon   = u8"\uf0e6";
        configPage.startX = lcd.width()  * 0.05; 
        configPage.startY = lcd.height() * 0.5; 
        configPage.width  = width;
        configPage.height = height;
        configPage.maxPages = 3;

        exitPage.name   = EXIT_PAGE;   
        exitPage.label  = lang.exitCaps.get();
        exitPage.icon   = u8"\ueb97";
        exitPage.startX = lcd.width()  * 0.55; 
        exitPage.startY = lcd.height() * 0.5;
        exitPage.width  = width;
        exitPage.height = height;

        currPage    = MENU_PAGE;
        currSubpage = 0;
    }
    
    void handle(){
        auto& display = device->display;

        if(!display.touch.click())
            return;

        if(!active && device->vehicle.maneuver.active)
            return draw();

        if(!display.on && display.touch.screenClick(false))
            return draw();

        if(currPage != MENU_PAGE)
            return handleSubmenuTouch();

        handleMenuTouch();
    }
    
    void reset(){
        currPage    = MENU_PAGE;
        currSubpage = 0;
        active = false;
    }

    void handleMenuTouch(){
        static auto& display = device->display;
        
        if(device->test.pass.required() && display.touch.areaClick(display.width*.1, display.height*.8, display.width*.8, display.height*.1))
            return device->test.pass.start();

        if(device->vehicle.valet.enabled && display.touch.areaClick(display.width*.15, display.height*.08, display.width*0.7, 45))
            return device->vehicle.valet.start();

        if(pageClicked(idPage))
            return setSubpage(ID_PAGE, 1);

        if(pageClicked(infoPage))
            return setSubpage(INFO_PAGE, 1);

        if(pageClicked(configPage))
            return setSubpage(CONFIG_PAGE, 1);

        if(pageClicked(exitPage))
            return device->display.turnOFF();
    }

    void handleSubmenuTouch(){
        if(nextClick())
            return increasePage();

        if(previousClick())
            return decreasePage();
        
        if(currPage == ID_PAGE && currSubpage == 1)
            return handleID1Touch();

        if(currPage == CONFIG_PAGE && currSubpage == 1)
            return handleConfig1Touch();

        if(currPage == CONFIG_PAGE && currSubpage == 2)
            return handleConfig2Touch();

        if(currPage == CONFIG_PAGE && currSubpage == 3)
            return handleConfig3Touch();
    }

    void handleID1Touch(){
        static auto& display = device->display;
        static int family    = 0;
        
        if(display.touch.areaClick(0, display.height*0.15, display.width, 65)){
            //handleFamily();
        }
        
        if(display.touch.areaClick(0, display.height*0.6, display.width, display.height*0.4)) {
            if(!display.interface.inputs.boolean(lang.askConfigWifi.get()))
                return display.turnOFF();
            
            Text<30> response;
            display.interface.keyboard.draw(lang.wifiConfig.get(), lang.networkName.get(), true);
            response = display.interface.keyboard.get();
            device->settings.params.set("ssid", response.get());

            display.interface.keyboard.draw(lang.wifiConfig.get(), lang.networkPassword.get());
            response = display.interface.keyboard.get();
            device->settings.params.set("passwd", response.get());
            device->settings.save();
            device->server.connect(true);

            display.interface.menu.draw();
            return;
        }
    }

    void handleConfig1Touch(){
        static auto& display = device->display;

        if(display.touch.areaClick(display.width*0.61, display.height*0.18, 40, 40)) {
            display.sound.increase(-10);
            return drawConfigPage1();
        }

        if(display.touch.areaClick(display.width*0.61 + 60, display.height*0.18, 40, 40)) {
            display.sound.increase(10);
            return drawConfigPage1();
        }
        
        if(display.touch.areaClick(display.width*0.61, display.height*0.325, 40, 40)) {
            display.brightness.increase(-10);
            return drawConfigPage1(); 
        }

        if(display.touch.areaClick(display.width*0.61 + 60, display.height*0.325, 40, 40)) {
            display.brightness.increase(10);
            return drawConfigPage1();
        }

        if(display.touch.areaClick(display.width*0.65, display.height*0.45, 65, 65)){
            device->server.set(!device->server.enabled);
            drawConfigPage1();
            return device->server.wait(2000);
        }

        if(display.touch.areaClick(0, display.height*0.6, display.width, 65)){
            device->server.changeChannel();
            return display.turnOFF();
        }
        
        if(display.touch.areaClick(0, display.height*0.75, display.width, 40)){
            device->server.updater.start();
            display.turnOFF();
        }
    }

    void handleConfig2Touch(){
        static auto& display = device->display;

        if(display.touch.areaClick(0, display.height*0.15, display.width, 65)){
            lcd.clear();
            device->server.wait(1000);
            device->diagnostic.start();
            return display.turnOFF();
        }

        if(display.touch.areaClick(0, display.height*0.30, display.width, 65)){
            device->test.start(true);
        }

        if(display.touch.areaClick(0, display.height*0.45, display.width, 65)){
            lcd.clear();
            device->server.wait(1000);
            device->diagnostic.serial();
            device->server.wait(2000);
            return display.turnOFF();
        }

        if(display.touch.areaClick(0, display.height*0.6, display.width, 65)){
            if(!device->server.connected())
                device->server.connect(true);
            
            const bool worked = device->server.updater.config();
            
            if(!worked)
                return device->display.turnOFF();

            device->display.interface.msg(MSG_GREEN, lang.restarting.get());
            device->display.sound.goodBeep();
            device->reset();
        }
        
        if(display.touch.areaClick(0, display.height*0.75, display.width, 40)){
            if(!display.interface.inputs.boolean(lang.askContinue.get(), lang.warningBlockTravel.get()))
                return device->display.turnOFF();

            display.interface.msg(MSG_WHITE, lang.restartingCaps.get());
            display.sound.volume = 255;
            display.sound.set(BUZZER_BAD_SOUND, 6000);
            display.sound.reset();
            ESP.restart();    
        }
    }
    
    void handleConfig3Touch(){
        static auto& display = device->display;

        if(display.touch.areaClick(0, display.height*0.15, display.width, 65)){
            if(!device->display.interface.inputs.boolean(lang.askContinue.get(), "mudança de idioma"), false)
                return device->display.turnOFF();

            int option = device->display.interface.inputs.trichoices("Português", "English", "Español");

            if (option == 0)
                device->settings.params.set("lang", "pt");
            else if (option == 1)
                device->settings.params.set("lang", "en");
            else if (option == 2)
                device->settings.params.set("lang", "es");

            device->settings.save();
            
            if(!device->display.interface.inputs.boolean(lang.askContinue.get(), lang.warningBlockTravel.get()))
                return device->display.turnOFF();

            device->reset();
        }
    }

    bool pageClicked(Page& page){
        return device->display.touch.areaClick(page.startX, page.startY, page.width, page.height);
    }

    bool previousClick(){
        return device->display.touch.areaClick(lcd.width()*0.50, lcd.height()*0.85, lcd.width()*0.32, 80);
    }

    bool nextClick(){
        return device->display.touch.areaClick(lcd.width()*0.83, lcd.height()*0.85, lcd.width()*0.20, 80);
    }

    void draw(){
        static auto& display = device->display;
        active = true;

        if(!display.on)
            display.turnON();

        if(device->server.connected() && device->server.updater.needed)
            device->server.updater.requestUpdate();

        currPage    = MENU_PAGE;
        currSubpage = 0;
        display.lcd.fillScreen(BG_COLOR);
        drawHeaderBar("MENU", u8"\uee1d");
        drawButton(idPage.label, idPage.icon, idPage.startX, idPage.startY, idPage.width, idPage.height);
        drawButton(infoPage.label, infoPage.icon, infoPage.startX, infoPage.startY, infoPage.width, infoPage.height);
        drawButton(configPage.label, configPage.icon, configPage.startX, configPage.startY, configPage.width, configPage.height);
        drawButton(exitPage.label, exitPage.icon, exitPage.startX, exitPage.startY, exitPage.width, exitPage.height);
        drawLastAlcohol();

        if(device->vehicle.valet.enabled)
            device->vehicle.valet.drawButton();

        if(device->test.pass.required())
            display.interface.label(lang.unlockVehicle.get(), lcd.width()*.1, lcd.height()*.8, lcd.width()*.8, lcd.height()*.1, TFT_BLACK, GREEN, true);

        device->await(500);
    }

    void drawButton(const String& label, const String& icon, int startX, int startY, int width, int height){
        static auto& display = device->display;

        display.lcd.fillRoundRect(startX, startY, width, height, 8, LIGHT_GREY);
        display.interface.font.setStyle(&Roboto_Bold10pt8b, DARK_GREY);
        int posX = 0, posY = 0;
    
        display.lcd.setTextSize(1);
        posX = startX + (width - display.lcd.textWidth(label)) / 2;
        posY = startY + height * 0.7;
        display.lcd.setTextColor(DARK_GREY);
        display.lcd.setCursor(posX, posY);
        display.lcd.print(label);
    
        display.lcd.setFont(&remixicon64pt8b);
        display.lcd.setColor(DARK_GREY);
        display.lcd.setTextSize(0.5);
        posX = startX + (width  - display.lcd.textWidth(icon)) / 2;
        posY = startY + (height - display.lcd.fontHeight())    / 2.5;
        display.lcd.setCursor(posX, posY);
        display.lcd.print(icon);
    }

    void drawHeaderBar(String text, String icon){
        static auto& display = device->display; 

        display.lcd.setFont(&Roboto_Bold10pt8b);
        display.lcd.setTextSize(1);
        display.interface.label(text, 0, 0, lcd.width(), lcd.height()*.05, DARK_GREY, YELLOW, false);
        display.interface.label(device->sensors.dht.temperature.toString(), 40, 0, 60, lcd.height()*.05, DARK_GREY, YELLOW, false);
        display.interface.printIcon(icon, 0.18, DARK_GREY, lcd.width() * 0.05, 4.2);

        if(device->server.connected())
            display.interface.printIcon(u8"\uf2c0", 0.16, DARK_GREY, lcd.width() * 0.84, 4.5);
        else
            display.interface.printIcon(u8"\uf2c2", 0.16, DARK_GREY, lcd.width() * 0.84, 4.5);

        display.interface.printIcon(u8"\ueaca", 0.16, DARK_GREY, lcd.width() * 0.9, 4.5);
    }

    void drawLastAlcohol(){
        static auto& display = device->display; 

        String footerText = lang.lastTest.get() + String(device->test.last_alcohol) + " mg/L";
        display.interface.font.setStyle(&Roboto_Regular10pt8b, LIGHT_GREY);
        display.lcd.setCursor((lcd.width() - display.lcd.textWidth(footerText)) / 2, lcd.height() * 0.85);
        display.lcd.print(footerText);
    }

    void increasePage(){
        if(currSubpage == currMaxPages)
            return;

        setSubpage(currPage, currSubpage + 1);
    }

    void decreasePage(){
        if(currSubpage <= 0)
            draw();

        setSubpage(currPage, currSubpage - 1);
    }
    
    void setSubpage(int page, int subpage){
        currPage    = page;
        currSubpage = subpage;

        if(currSubpage < 0)
            currSubpage = 0;

        if(currPage == INFO_PAGE){
            currMaxPages = infoPage.maxPages;

            if(currSubpage == 1)
                drawInfoPage1();
            
            if(currSubpage == 2)
                drawInfoPage2();

            if(currSubpage == 3)
                drawInfoPage3();

            if(currSubpage == 4)
                drawInfoPage4();
        }

        if(currPage == ID_PAGE){
            currMaxPages = idPage.maxPages;

            if(currSubpage == 1)
                drawIdPage1();

            if(currSubpage == 2)
                drawIdPage2();
        }
        
        if(currPage == CONFIG_PAGE){
            currMaxPages = configPage.maxPages;

            if(currSubpage == 1)
                drawConfigPage1();

            if(currSubpage == 2)
                drawConfigPage2();

            if(currSubpage == 3)
                drawConfigPage3();
        }

        device->await(400);
        device->display.touch.reset();
    }

    void drawSubmenu(Page& page, String labels[], String values[], int numItens=NULL){
        static auto& display = device->display; 

        lcd.fillScreen(BG_COLOR);
        drawHeaderBar(page.label, page.icon);

        float lineY = submenuContainerStartY + submenuItemListHeight;
        float textY = submenuContainerStartY;
        int16_t textPos;
        
        lcd.fillRoundRect(
            lcd.width() * .05, submenuContainerStartY, lcd.width() * .9,
            submenuContainerHeight - ((5 - numItens) * submenuItemListHeight),
            8, LIGHT_GREY
        );  

        for(int i=0; i<numItens; i++){
            display.interface.font.setStyle(&Roboto_Bold10pt8b, DARK_GREY);
            textPos = textY + (submenuItemListHeight - lcd.fontHeight()) / 3.8;
            lcd.setCursor(lcd.width()*0.1, textPos);
            lcd.print(labels[i]);

            if(values != NULL){
                display.interface.font.setStyle(&Roboto_Regular10pt8b, DARK_GREY);
                textPos = textY + (submenuItemListHeight - lcd.fontHeight()) / 1.2;
                lcd.setCursor(lcd.width() * 0.1, textPos);
                lcd.print(values[i]);
            }

            if(i != numItens-1)
                lcd.drawLine(lcd.width() * 0.05, lineY, lcd.width() * 0.95, lineY, DARK_GREY);

            textY = lineY;
            lineY += submenuItemListHeight;
        }

        display.interface.font.setStyle(&Roboto_Regular10pt8b, LIGHT_GREY);
        lcd.setCursor(lcd.width() * 0.08, lcd.height() * 0.91);
        lcd.print(lang.pageStr.get() + String(currSubpage) + "/" + String(currMaxPages));

        if(currSubpage == currMaxPages){
            display.interface.printIcon(u8"\uea5c", 0.3, LIGHT_GREY, lcd.width() * 0.6, lcd.height() * 0.9);
            display.interface.printIcon(u8"\uea68", 0.3, DARK_GREY, lcd.width() * 0.83, lcd.height() * 0.9);
            return;
        }

        display.interface.printIcon(u8"\uea5c", 0.3, LIGHT_GREY, lcd.width() * 0.6, lcd.height() * 0.9);
        display.interface.printIcon(u8"\uea68", 0.3, LIGHT_GREY, lcd.width() * 0.83, lcd.height() * 0.9);
    }

    void drawIdPage1(){
        String labels[] = {
            lang.firmwareVersion.get(),
            lang.serialNumber.get(),
            lang.sensorId.get(),
            lang.networkSsid.get(),
            lang.networkPassword.get()
        };
        
        String values[] = {
            String(device->firmware),
            device->settings.template get<String>("esp_id"),
            device->settings.template get<String>("sensor_id"),
            device->server.wifi_ssid.get(),
            device->server.wifi_passwd.get()
        };

        const int size = sizeof(labels) / sizeof(labels[0]);
        drawSubmenu(idPage, labels, values, size);
    }

    void drawIdPage2(){
        String labels[] = {
            lang.travelTime.get(),
            lang.telemetryId.get(),
            lang.calibrationDate.get(),
            lang.macAddress.get(),
            lang.vehicleType.get()
        };

        const byte telType = device->telemetry.type; 
        const char* telID  = (telType == SUNTECH_TEL) ? device->telemetry.suntech.id.get() : 
                             (telType == ENTRACK_TEL) ? device->telemetry.entrack.id.get() : "N/A";

        String values[] = {
            formatTimeString(device->vehicle.ignition.getTime()),
            telID,
            device->sensors.alcohol.storage.calibration_date.toString(),
            String(WiFi.macAddress()),
            device->vehicle.type == 0 ? lang.truck.get() : lang.carStr.get()
        };

        const int size = sizeof(labels) / sizeof(labels[0]);
        drawSubmenu(idPage, labels, values, size);
    }
    
    void drawInfoPage1(){
        String labels[] = {
            lang.companyStr.get(),
            lang.travelStatus.get(),
            lang.lastReading.get(),
            lang.upTime.get(),
            lang.routerSsid.get()
        };

        String values[] = {
            String(device->company.name) + " - " + String(device->telemetry.toText()),
            (device->vehicle.blocked ? lang.blockedStr.get() : lang.unblockedStr.get()) + String(" - ") + String(device->vehicle.driving ? lang.drivingStr.get() : lang.offStr.get()),
            String(device->test.last_alcohol, 3) + " mg/L",
            formatTimeString(Time::get()) + " - " + String(device->server.sleeper.frequency) + " MHz",
            device->server.server_ssid.toString()
        };

        const int size = sizeof(labels) / sizeof(labels[0]);
        drawSubmenu(infoPage, labels, values, size);
    }

    void drawInfoPage2(){ 
        String labels[] = {
            lang.maneuverTime.get(),
            lang.cameraTime.get(),
            lang.maxPostpones.get(),
            lang.randomMode.get(),
            lang.valetModeStr.get()
        };
        
        String values[] = {
            String(device->vehicle.maneuver.timeout/60000) + " min",
            device->vehicle.camera.toString(),
            device->settings.template get<String>("max_postpone") + lang.postponesSuffix.get(),
            device->test.randomic.toString(),
            String(device->vehicle.valet.enabled ? lang.enabledStr.get() : lang.disabledStr.get()) + " - " + String(device->vehicle.valet.active ? lang.activeMStr.get() : "N/A")
        };
        
        const int size = sizeof(labels) / sizeof(labels[0]);
        drawSubmenu(infoPage, labels, values, size);
    }

    void drawInfoPage3(){
        String labels[] = {
            lang.timeOfTravel.get(),
            lang.numberOfBlows.get(),
            lang.blowSmoothing.get(),
            lang.telemetryPrefix.get() + String(device->telemetry.working() ? lang.activeFStr.get() : lang.inactiveFStr.get()) ,
            lang.testsPerTravel.get()
        };

        String values[] = {
            formatTimeString(device->test.randomic.travels.getMeanTime()),
            String(device->sensors.alcohol.storage.blows.value) + lang.testsSuffix.get(), 
            String(device->sensors.pressure.blowProb) + " seg",
            "Time Check: " + formatTimeString(Time::get() - device->telemetry.serial.lastAckTime), 
            String(device->test.randomic.max_tests) + lang.testsSuffix.get()
        };

        const int size = sizeof(labels) / sizeof(labels[0]);
        drawSubmenu(infoPage, labels, values, size);
    }
    
     void drawInfoPage4(){
        auto& sensor = device->sensors.alcohol;

        String labels[] = {
            lang.heaterPin.get(),
            lang.sensorCalibration.get(),
            lang.sensorStability.get()
        };
        
        String values[] = {
            sensor.heater.toString(),
            String(sensor.calibration.newZero) + " (" + String(sensor.calibration.getPercent(sensor.calibration.data.mean)) + "%)",
            String((int) sensor.calibration.data.mean)  + " (" + String(sensor.calibration.data.rel)  + ") - " + String(sensor.calibration.data.rel < 0.15 ? lang.stable.get() : lang.stabilizing.get())
        };

        const int size = sizeof(labels) / sizeof(labels[0]);
        drawSubmenu(infoPage, labels, values, size);
    }

    void drawConfigPage1(){
        static auto& display = device->display; 
        
        String labels[] = { 
            lang.beepVolume.get(),
            lang.displayBrightness.get(),
            lang.wifiStr.get(),
            lang.reconnect.get(), 
            lang.firmwareUpdate.get()
        };

        String values[] = {
            device->display.sound.toString(),
            device->display.brightness.toString(),
            device->server.enabled ? lang.onStr.get() : lang.offStr.get(),
            lang.wifiChannelConfig.get(),
            ""
        };
        
        const int size = sizeof(labels) / sizeof(labels[0]);
        drawSubmenu(configPage, labels, values, size);

        drawAdjustButtons(lcd.width() * 0.61, lcd.height() * 0.180, 40, 40);
        drawAdjustButtons(lcd.width() * 0.61, lcd.height() * 0.325, 40, 40);

        if(device->server.enabled)
            display.interface.printIcon(u8"\uf218", 0.4, GREEN, lcd.width() * 0.65, lcd.height() * 0.45);
        else
            display.interface.printIcon(u8"\uf219", 0.4, DARK_GREY, lcd.width() * 0.65, lcd.height() * 0.45);
    }

    void drawConfigPage2(){
        static auto& display = device->display; 

        String labels[] = {
            lang.selfDiagnostic.get(),
            lang.alcoholTest.get(),
            lang.telemetryTest.get(),
            lang.remoteConfig.get(),
            lang.emergencyRestart.get()
        };

        String values[] = {
            lang.clickToStart.get(),
            lang.simpleVerification.get(),
            lang.testTelemetry.get(),
            lang.clickToVerify.get(),
            lang.clickToStart.get()
        };

        const int size = sizeof(labels) / sizeof(labels[0]);
        drawSubmenu(configPage, labels, values, size);

        const auto y = submenuContainerStartY + (submenuItemListHeight - lcd.fontHeight()) / 2;
        display.interface.printIcon(u8"\uea68", 0.3, YELLOW, lcd.width() * 0.8, y);
    }

     void drawConfigPage3(){
        static auto& display = device->display; 
        
        String labels[] = { 
            "Change Language"
        };

        String values[] = {
            "Current: " + String(getLang())
        };
        
        const int size = sizeof(labels) / sizeof(labels[0]);
        drawSubmenu(configPage, labels, values, size);
    }

    
    void drawAdjustButtons(int x, int y, float width, float height){
        static auto& display = device->display; 
        

        int txt_x = 0;
        int txt_y = y + (height - lcd.fontHeight()) / 2;
        display.interface.font.setStyle(&Roboto_Regular10pt8b, DARK_GREY);
        
        // BOTÃO -
        txt_x = x + (width - lcd.textWidth("-")) / 2;
        lcd.fillRoundRect(x, y, width, height, 8, YELLOW);
        lcd.setCursor(txt_x, txt_y);
        lcd.print("-");

        // BOTÃO +
        x += 60;
        txt_x = x + (width - lcd.textWidth("+")) / 2;
        lcd.fillRoundRect(x, y, width, height, 8, YELLOW);
        lcd.setCursor(txt_x, txt_y);
        lcd.print("+");
    }

    void handleFamily(){
        static int family = 0;
        auto &display = device->display;
        family += 1;

        if(family < 1500)
            return device->await(100);

        display.interface.msg(MSG_WHITE, "");
        display.lcd.drawJpg(family_logo, sizeof(family_logo), 0, 0, device->display.width, device->display.height, 0, 0, 1.0);
        display.interface.centeredText(lang.devFamily.get(), TFT_BLACK, device->display.height*0.15);
        family = 0;
        display.touch.enableDraw(4000);
        return device->display.turnOFF();
    }
};

#endif