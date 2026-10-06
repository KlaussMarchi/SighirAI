#ifndef ALCOHOL_MODEL_H
#define ALCOHOL_MODEL_H
#include "../../../utils/time/index.h"
#include "../../../utils/listener/index.h"
#include "../../../utils/array/index.h"
#define MAX_SAMPLES 47


class AlcoholModel{
  public:
    Array<MAX_SAMPLES> data;
    Array<MAX_SAMPLES> data_diff;
    float min, median, mean, last, max, mean_diff, std, first, min_diff, first_diff, max_diff, std_diff, median_diff, last_diff;
    int decay;
    bool result, done;

    void reset(){
        data.reset();
        data.setTimeout(500);
        done = false;
    }

    void init(int value){
        reset();
        data.append(value);
    }

    void add(int value){
        if(value < ANALOG_INVALID)
            return;
        
        if(!data.ready())
            return;

        data.append(value);

        if(data.isFull)
            done = true;
    }

    void update(){
        min   = data.getMin();
        max   = data.getMax();
        mean  = data.getMean();
        std   = data.getStd();
        first = data.get(0);
        last  = data.get(-1);
        median = data.getMedian();

        data_diff.fill(0);
        for(int x=1; x<data.length-1; x++)
            data_diff.array[x] = (data.get(x+1) - data.get(x-1))/2.00f;

        data_diff.array[0]                  = (data.get(1) - data.get(0));
        data_diff.array[data_diff.length-1] = (data.get(-1) - data.get(-2));
        data_diff.index = 0;

        min_diff   = data_diff.getMin();
        max_diff   = data_diff.getMax();
        mean_diff  = data_diff.getMean();
        std_diff   = data_diff.getStd();
        first_diff = data_diff.get(0);
        last_diff  = data_diff.get(-1);
        median_diff = data_diff.getMedian();

        decay = data.get(0) - min; // debug somente
        result = get();
    }

    Text<350> getInfo(){
        Text<350> response = "\n[";

        for(int x=0; x<data.length; x++)
            response += (String((int) data.get(x)) + ",");
        
        response += "]";
        return response;
    }

    bool get(){
        static const int size     = 14;
        const float OFFSET[size]  = { 15136.355855855856, 16463.164334547313, 16047.705705705706, 16172.288288288288, -36.38607756692863, 1430.1513116404844, 20857.77027027027, -1703.533033033033, 1399.7935435435436, 428.8738738738739, 18102.36036036036, 483.2018019200206, 7.538288288288288, 10.97897897897898 };
        const float GAIN[size]    = { 0.00018477899343094888, 0.00019790949157551016, 0.00019061863483204155, 0.0001878060128720777, 0.011799908721902242, 0.0011081737491829898, 0.0002351039403579649, 0.0007543737911574769, 0.0009127861666831241, 0.000620087856482268, 0.0002198378768689942, 0.003771799807473492, 0.028104308500667183, 0.014713280771692715   };
        const float WEIGHTS[size] = { -9.524353039769611, -1.6767457683555176, 1.5971612323223774, 1.9246942283020063, -7.396942755051656, 3.887633657596146, -5.323022039217649, -3.173850322108974, 0.4121297173259488, 1.8629338721033488, 9.062461974431768, -2.2494178872345225, 5.325139124384128, 0.303015056932162 };
        const float BIAS       = 5.357616865427982;
        const float BEST_TRESH = 0.42564459038641034;

        float z = BIAS;
        float x[size];
        int index = 0;

        x[index++] = (float) min;
        x[index++] = (float) mean;
        x[index++] = (float) median;
        x[index++] = (float) last;
        x[index++] = (float) mean_diff;
        x[index++] = (float) std;
        x[index++] = (float) max;
        x[index++] = (float) min_diff;
        x[index++] = (float) max_diff;
        x[index++] = (float) first_diff;
        x[index++] = (float) first;
        x[index++] = (float) std_diff;
        x[index++] = (float) median_diff;
        x[index++] = (float) last_diff;

        for(int i=0; i<size; i++)
            z += WEIGHTS[i] * (x[i] - OFFSET[i]) * GAIN[i];

        const float prob = 1.0f / (1.0f + expf(-z));
        return (prob > BEST_TRESH);
    }
};

#endif