
#ifndef ALCOHOL_MODEL_H
#define ALCOHOL_MODEL_H
#include "../../../utils/time/index.h"
#include "../../../utils/listener/index.h"
#include "../../../utils/array/index.h"
#include "rf_model_data.h"
#define MAX_SAMPLES 47


class AlcoholModel{
  public:
    Array<MAX_SAMPLES> data;
    Array<MAX_SAMPLES> data_diff;
    float decay, min, mean_diff, mean, median, last, amplitude, std, rise, min_diff, max_diff, max, first_diff, median_diff, std_diff, first;
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
        //last_diff  = data_diff.get(-1);
        median_diff = data_diff.getMedian();

        decay = data.get(0) - min; // debug somente
        rise  = data.get(0) - max; // debug somente
        amplitude = max - min;
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
        static const int size     = 15;
        const float OFFSET[size]  = { 2930.689330543933, -32.18624810825247, 15000.916317991632, 16418.32077361346, 16030.688284518828, 16164.899581589958, -2891.166317991632, 1430.8112424576746, 5821.855648535565, 1473.4728033472804, -1723.897489539749, 20822.771966527198, 497.38598326359835, 7.924163179916318, 496.41853305654007 };
        const float GAIN[size]    = { 0.00027684289272103155, 0.011984886811866843, 0.0001952989495083152, 0.00020682528029483243, 0.00019796982600590112, 0.00019384606276085165, 0.0004514689554653688, 0.001167945198357715, 0.0003283705066469706, 0.0009354012859598361, 0.0008042089725396777, 0.0002445573745613286, 0.0006489103092041868, 0.02684929629534037, 0.0040965100915883075   };
        const float BEST_TRESH    = 0.7426470588;

        float x[size];
        int index = 0;

        x[index++] = (float) decay;
        x[index++] = (float) mean_diff;
        x[index++] = (float) min;
        x[index++] = (float) mean;
        x[index++] = (float) median;
        x[index++] = (float) last;
        x[index++] = (float) rise;
        x[index++] = (float) std;
        x[index++] = (float) amplitude;
        x[index++] = (float) max_diff;
        x[index++] = (float) min_diff;
        x[index++] = (float) max;
        x[index++] = (float) first_diff;
        x[index++] = (float) median_diff;
        x[index++] = (float) std_diff;

        for(int i=0; i<size; i++)
            x[i] = (x[i] - OFFSET[i]) * GAIN[i];

        float final_prob = evaluate_rf(x); 
        return (final_prob > BEST_TRESH);
    }
};

#endif
