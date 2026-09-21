#ifndef LANGUAGES_H
#define LANGUAGES_H
#include <Arduino.h>




typedef struct Language{
    const char* PT;
    const char* EN;
    const char* ES;

    Language(const char* pt, const char* en, const char* es): 
        PT(pt), EN(en), ES(es) {}

    const char* get(){
        return (strcmp(vars.idiom, "EN") == 0) ? EN :
               (strcmp(vars.idiom, "ES") == 0) ? ES : PT;
    }
} Lang;

struct Languages {
     char idiom[3];

    Lang alcoholTest = Lang(
        "Teste de Álcool",
        "Alcohol Test",
        "Prueba de Alcoholemia"
    );
};


#endif