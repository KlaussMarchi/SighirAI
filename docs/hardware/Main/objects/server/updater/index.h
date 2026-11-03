#ifndef UPDATER_H
#define UPDATER_H
#include "../../../device/lang/index.h"
#include <Update.h>
#include <SPI.h>
#include "../../../utils/time/index.h"
#include "../../../utils/text/index.h"
#include "../../../globals/functions.h"


template <typename Parent> class Updater{
  private:
    Parent* device;
    bool connecting = false;   // RECONECTAR CHAMA O HANDLECHECK: O AVISO DE VERSÃO NOVA NÃO ABRE POR CIMA

  public:
    static const int CHUNK_SIZE  = 1.4*2048;   // BASE64 (4/3) DE 2048 BYTES MAIS OFFSET E CRC
    static const int FIRST_DATA  = 35000;      // ms ATÉ O PRIMEIRO BLOCO
    static const int SILENCE     = 10000;      // ms SEM DADOS ENCERRA A ATUALIZAÇÃO
    static const int MAX_INVALID = 5;          // AS TENTATIVAS DO SIGHIRTESTER POR BLOCO
    static const int ASK_TIMEOUT = 20000;      // ms SEM TOQUE NA ESCOLHA DE REDE VALE SAIR
    bool needed;

    Updater(Parent* dev):
        device(dev){}

    void start(){
        if(!connect())
            return;

        const bool configured = config();
        download();

        if(configured)
            return device->reset();

        handleCheck(true);
    }

    // SÓ ATUALIZA OU CONFIGURA COM INTERNET: SEM ELA REESTABELECE A CONEXÃO E OFERECE TROCAR DE REDE
    bool connect(){
        auto& server = device->server;
        int option   = 1;   // 0 OUTRA REDE, 1 TENTAR NOVAMENTE, 2 SAIR
        connecting   = true;

        if(!server.connected())
            server.connect(true);

        bool online = (server.ping() >= 0);

        while(!online && option != 2){
            if(option == 0)
                server.changeNetwork();

            if(option == 1)
                server.changeChannel();

            online = (server.ping() >= 0);

            if(!online)
                option = device->display.interface.inputs.trichoices(lang.otherNetwork.get(), lang.tryAgainStr.get(), lang.exitStr.get(), 2, ASK_TIMEOUT);
        }

        connecting = false;
        return online;
    }

    // TODA CONEXAO NOVA (BOOT, ROTEADOR VOLTOU, FIM DO SLEEPER) REPORTA FIRMWARE, IDS E SE O SENSOR TEM COEFICIENTES; SEM RESPOSTA TENTA DE NOVO EM 2 MIN
    void handleCheck(bool force=false){
        static unsigned long lastCheck = 0;
        static bool pending = true;
        static bool synced  = false;

        const bool connected = device->server.connected();
        pending |= !connected;

        if(!connected)
            return;

        const unsigned long interval = synced ? 30*60*1000UL : 2*60*1000UL;

        if(!force && !pending && Time::get() - lastCheck < interval)
            return;

        if(!force && device->test.active)
            return;

        Text<64> response = device->server.get(
            "api/v2/devices/check-update/?id=" + device->id.toString()    + 
            "&sensor_id=" + device->sensors.alcohol.storage.id.toString() +
            "&firmware="  + String(device->firmware) +
            "&calib="     + (device->sensors.alcohol.storage.has_coefs ? "true" : "false")
        );

        lastCheck = Time::get();
        pending   = false;
        synced    = !response.equals("-1");

        if(!response.contains("true"))
            return;

        if(!connecting && (device->in_setup || device->display.interface.menu.active))
            requestUpdate();

        needed = true;
    }

    // NO MENU A TELA APAGA AO RECUSAR OU QUANDO A ATUALIZAÇÃO VOLTA SEM REINICIAR (FALHA OU SAIR)
    void requestUpdate(){
        auto& display = device->display;
        needed = (bool) display.interface.inputs.boolean(lang.newVersionAvail.get(), lang.askUpdate.get());

        if(needed)
            start();

        if(display.interface.menu.active)
            display.turnOFF();
    }

    bool config(){
        device->display.interface.alert(lang.remoteConfig.get(), lang.checkingStr.get(), MSG_BLACK, 0);
        Text<512> request = "{\"esp_id\": \"" + device->id.toString() + "\"}";

        const String response = device->server.post("checkSettings/", request.toString(), 10000);
        Serial.println("update response: " + response);
        Json<512> settings;

        if(response == "-1"){
            device->display.interface.alert(lang.configError.get(), lang.noServerRes.get());
            return false;
        }

        if(!settings.parse(response.c_str())){
            device->display.interface.alert(lang.configError.get(), response.c_str());
            return false;
        }

        if(!settings.data.containsKey("status") || !settings.data.containsKey("data")){
            device->display.interface.alert(lang.configError.get(), lang.invalidKeys.get());
            return false;
        }

        if(settings.data["data"].as<String>().indexOf("doesnt") != -1){
            device->display.interface.alert(lang.verified.get(), lang.noConfigNeeded.get(), MSG_BLACK);
            return false;
        }

        if(settings.data["status"].as<String>() != "success"){
            device->display.interface.alert(lang.configError.get(), settings.data["data"].as<String>());
            return false;
        }

        if(settings.data["data"].as<String>() == "None"){
            device->display.interface.alert(lang.verified.get(), lang.noConfigNeeded.get(), MSG_BLACK);
            return false;
        }

        if(!apply(settings.data["data"].as<String>())){   // lido pela metade não grava nada
            device->display.interface.alert(lang.configError.get(), lang.invalidKeys.get());
            return false;
        }

        device->settings.save();
        device->display.interface.alert(lang.deviceConfigured.get(), "", MSG_BLACK);
        device->telemetry.event("$ETEV07!");
        return true;
    }

    // GUARDADA EM "REMOTE" PARA VOLTAR POR CIMA DO CONFIGPARAMS QUANDO O FIRMWARE NOVO É DE OUTRA EMPRESA
    bool apply(const String& received){
        Json<512> remote;

        if(!remote.parse(received) || !remote.data.template is<JsonObject>())
            return false;

        for(JsonPair data: remote.data.template as<JsonObject>())
            device->settings.params.data[data.key()] = data.value().as<String>();

        device->settings.params.data["remote"] = received;
        return true;
    }

    void download(){
        auto& display = device->display;
        display.interface.msg(MSG_BLACK, lang.firmwareUpdate.get());
        display.interface.centeredText(device->id.toString(), TFT_WHITE, display.height*0.65);
        device->await(2000);

        if(!device->server.connected())
            return;
        
        device->await(500);
        String data = "{\"esp_id\":\"" + device->id.toString() + "\"}";
        Serial.println(data);
        
        HTTPClient http;
        http.begin(device->server.URL.toString() + "update/");
        http.addHeader("Content-Type", "application/json");
        device->await(700);

        int httpCode = http.POST(data);
        bool success = false;

        if(httpCode != 200){
            http.end();
            display.interface.msg(MSG_RED, lang.invalidServerRes.get());
            return display.sound.badBeep();
        }   
        
        WiFiClient *client   = http.getStreamPtr();
        size_t contentLength = http.getSize();
        bool canBegin = Update.begin(contentLength);

        if(canBegin){
            display.interface.loading.start(lang.updatingDevice.get(), lang.keepPowered.get());

            Update.onProgress([this](size_t progress, size_t total){
                device->display.interface.loading.step(progress * 100 / total, false);
            });

            if(Update.writeStream(*client) != contentLength)
                success = false;

            if(Update.end()){
                if(Update.isFinished())
                    success = true;
                else
                    success = false;
            }
            else{
                success = false;
            }
        }
        else {
            success = false;
        }

        http.end();
        finish(success);
    }

    // ATUALIZAÇÃO PELO SERIAL (SIGHIRTESTER): "__updt__<TAMANHO>" E DEPOIS OS BLOCOS EM BASE64
    void local(){
        const char* command = device->telemetry.serial.command.get();
        const size_t size   = strtoul(command + strcspn(command, "0123456789"), nullptr, 10);
        const size_t total  = (size > 0) ? size : ESP.getSketchSize();   // TESTER ANTIGO NÃO MANDA O TAMANHO: A BARRA ESTIMA PELO FIRMWARE ATUAL

        device->display.interface.loading.start(lang.updatingDevice.get(), lang.keepPowered.get());
        Update.onProgress([this, total](size_t progress, size_t){
            device->display.interface.loading.step(std::min<size_t>(99, progress * 100 / total), false);
        });

        const bool success = Update.begin(size > 0 ? size : UPDATE_SIZE_UNKNOWN) && receive(size) && Update.end(size == 0);   // SEM TAMANHO, O FIM É O SILÊNCIO
        device->telemetry.serial.send(success ? "_UPDATE_OK_" : "_UPDATE_FAIL_");
        finish(success);
    }

    // BLOCOS "$BASE64=#OFFSET:CRC32!" (CRC DO TEXTO ATÉ O ':') RESPONDIDOS COM "written" OU "resend"; O TESTER ANTIGO MANDA SÓ "$BASE64!"
    bool receive(const size_t size){
        static char chunk[CHUNK_SIZE];        // FORA DA PILHA: O LOOP TEM 8 KB
        static uint8_t decoded[CHUNK_SIZE];
        auto& serial = device->telemetry.serial;

        unsigned long lastData = Time::get();
        size_t received = 0;
        int invalid     = 0;
        int index       = -1;
        serial.send("_STARTING_UPDATE_");

        while(Time::get() - lastData < (received > 0 ? SILENCE : FIRST_DATA)){
            if(!serial.uart->available())
                continue;

            const char c = serial.uart->read();
            lastData = Time::get();

            if(c == '$'){   // RECOMEÇA O BLOCO: É O REENVIO QUANDO O '!' SE PERDEU
                index = 0;
                continue;
            }

            if(index < 0)
                continue;

            if(c != '!' && index < CHUNK_SIZE-1){
                chunk[index++] = c;
                continue;
            }

            chunk[index] = '\0';
            index = -1;

            char* hash          = strchr(chunk, '#');
            char* colon         = strchr(chunk, ':');
            const bool framed   = (hash && colon && colon > hash);
            const size_t offset = framed ? strtoul(hash + 1, nullptr, 10) : received;
            const uint32_t crc  = framed ? strtoul(colon + 1, nullptr, 16) : 0;
            const size_t length = base64Decode(chunk, decoded, hash ? hash - chunk : strlen(chunk));

            const bool valid = (c == '!') && (length > 0) && (size == 0 || (framed && crc == crc32((uint8_t*) chunk, colon - chunk)));   // COM TAMANHO, SÓ COM CRC: O "$ETKA!" DE UM TESTER REABERTO NÃO É GRAVADO

            if(!valid && ++invalid >= MAX_INVALID)   // O TESTER DESISTIU OU NÃO É ATUALIZAÇÃO
                return false;

            if(!valid){
                serial.send("resend");
                continue;
            }

            invalid = 0;

            if(offset > received)   // FALTOU UM BLOCO
                return false;

            if(offset == received && Update.write(decoded, length) != length)
                return false;

            received = std::max(received, offset + length);   // OFFSET JÁ GRAVADO: O "written" ANTERIOR SE PERDEU
            serial.send("written");

            if(size > 0 && received >= size)
                return true;
        }

        return (size == 0 && received > 0);
    }

    // FIM DA ATUALIZAÇÃO PELA INTERNET OU PELO SERIAL: VERDE E REINICIA, OU VERMELHO E SEGUE NA VERSÃO ATUAL
    void finish(const bool success){
        auto& display = device->display;

        if(!success){
            Update.abort();
            display.interface.msg(MSG_RED, lang.updateFailed.get());
            return display.sound.badBeep();
        }

        display.interface.msg(MSG_GREEN, lang.completed.get());
        display.interface.centeredText(lang.restartingDevice.get(), TFT_WHITE, display.height*0.70);
        device->telemetry.event("$ETEV10!");
        display.sound.goodBeep();
        device->reset();
    }
};

#endif