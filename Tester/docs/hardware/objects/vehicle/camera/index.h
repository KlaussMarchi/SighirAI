#ifndef CAMERA_H
#define CAMERA_H


template <typename Parent> class Camera{
  private:
    Parent* device;

  public:
    int timeout;
    bool enabled;

    Camera(Parent* dev):
        device(dev){}

    void setup(){
        timeout = device->settings.template get<int>("camera")*1000;
        enabled = (timeout > 0); 
    }

    bool load(){
        auto& loader   = device->display.interface.loading;
        const int left = timeout - (Time::get() - device->test.startRequestTime);

        if(!enabled || left < 1000)
            return false;
        
        device->test.screens.inmetro();
        loader.start(lang.waitingCamera.get(), "", left, 30);
        
        while(!loader.done()){
            loader.step();

            if(!device->test.postpone.allowed())
                continue;

            if(device->display.touch.screenClick(true))
                return true;
        }
        
        return false;
    }

    String toString(){
        return String(timeout/1000) + " seg";
    }
};

#endif