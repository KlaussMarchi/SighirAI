#ifndef CONSTANTS_H
#define CONSTANTS_H

#define MIX_TEL  0
#define AUTO_TEL 1
#define SUNTECH_TEL 2
#define MIX_TEL_NEW 5 
#define ENTRACK_TEL 6

#define TRUCK_TYPE 0
#define CAR_TYPE   1

#define TEST_OK 0
#define TEST_POSTPONED 1
#define TEST_BLOW_TIMEOUT 2
#define TEST_ALCOHOL 3
#define TEST_STARTED 4
#define TEST_CALIBRATION_FAIL 5

#define BUZZER_NO_SOUND   0
#define BUZZER_BLOW       2600
#define BUZZER_BAD_SOUND  500
#define BUZZER_RND_SOUND  800
#define BUZZER_GOOD_SOUND 2800
#define BUZZER_SIGNAL     2600

#define MSG_BLACK  0
#define MSG_WHITE  1
#define MSG_RED    2
#define MSG_GREEN  3
#define MSG_ORANGE 4

#define MENU_PAGE   0
#define ID_PAGE     1
#define INFO_PAGE   2
#define CONFIG_PAGE 3
#define EXIT_PAGE   4

#define BLUE  0x0c1f
#define GREEN 0x4ecc
#define YELLOW   0x24eb
#define BG_COLOR 0x18e3
#define DARK_GREY  0x2104
#define LIGHT_GREY 0xc5d5

#define EEPROM_FAIL 1
#define SENSOR_FAIL 2
#define SENSOR_OK   3

#define HEAT_MIN_TIME 5000
#define MIN_ANALOG 5000
#define ANALOG_INVALID 1000
#endif