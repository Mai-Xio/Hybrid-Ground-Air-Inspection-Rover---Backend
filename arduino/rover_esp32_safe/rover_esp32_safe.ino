/*
  HAGAIR / Papaya Pathfinder - ESP32 Fixed Firmware for YOUR wiring
  Board: normal ESP32 DevKit-style board, not ESP32-S3.

  YOUR WIRING USED HERE
  BTS7960 #1 for motors 1-2-3:
    RPWM -> GPIO 25
    LPWM -> GPIO 26
    R_EN -> 5V from UBEC
    L_EN -> 5V from UBEC

  BTS7960 #2 for motors 4-5-6:
    RPWM -> GPIO 27
    LPWM -> GPIO 14
    R_EN -> 5V from UBEC
    L_EN -> 5V from UBEC

  4 S3003 servos:
    Servo 1 orange/signal -> GPIO 16
    Servo 2 orange/signal -> GPIO 17
    Servo 3 orange/signal -> GPIO 18
    Servo 4 orange/signal -> GPIO 19

  IMPORTANT POWER RULES
  - ESP32 GND, UBEC GND, BTS7960 logic GND, servo GND and motor battery GND must be common.
  - Do NOT power servos from ESP32 3.3V.
  - Prefer servo +5V/+6V from UBEC directly to servo red wires.
  - BTS7960 motor power B+ / B- must come from the motor battery rail, not ESP32.

  SAFETY DEFAULTS FOR YOUR FRAGILE BIG-MOTOR PROTOTYPE
  - Motors are disabled until /arm is called.
  - Safe mode is ON by default.
  - Max PWM is capped low.
  - Servo steering movement is capped to +/-10 degrees.
  - Spin/pivot mode is blocked in safe mode.
  - Watchdog stops motors if commands stop arriving.

  Arduino IDE libraries needed:
  - ESP32 board package by Espressif
  - ArduinoJson by Benoit Blanchon
*/

#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <ArduinoJson.h>
#include <math.h>

#if __has_include(<esp_arduino_version.h>)
  #include <esp_arduino_version.h>
#endif

#ifndef ESP_ARDUINO_VERSION_MAJOR
  // If the version header is unavailable, assume Arduino-ESP32 2.x API.
  #define ESP_ARDUINO_VERSION_MAJOR 2
#endif

// ======================= EDIT YOUR WIFI HERE =======================
// Put your mobile hotspot/router name and password here.
// If both fail, ESP32 starts its own hotspot: HAGAIR_ROVER_AP / 12345678
const char* WIFI_SSID_1     = "Meow meow";
const char* WIFI_PASSWORD_1 = "meowme890";
const char* WIFI_SSID_2     = "Meow meow";
const char* WIFI_PASSWORD_2 = "meowme890";

const char* AP_SSID = "Meow meow";
const char* AP_PASS = "meowme890";

// ======================= PIN MAP: YOUR WIRING =======================
// BTS7960 #1, motors 1-2-3. Treat as LEFT side by default.
#define BTS1_RPWM_PIN 25
#define BTS1_LPWM_PIN 26

// BTS7960 #2, motors 4-5-6. Treat as RIGHT side by default.
#define BTS2_RPWM_PIN 27
#define BTS2_LPWM_PIN 14

// S3003 servo signal pins.
#define SERVO1_PIN 16
#define SERVO2_PIN 17
#define SERVO3_PIN 18
#define SERVO4_PIN 19

// Optional onboard LED. Many ESP32 DevKit boards have LED on GPIO2.
// Keep disabled if your board has no LED or boot becomes unstable.
#define STATUS_LED_ENABLED 0
#define STATUS_LED_PIN 2

// Optional ultrasonic obstacle stop. Disabled because your listed pins do not include it yet.
#define ULTRASONIC_ENABLED 0
#define US_TRIG_PIN 32
#define US_ECHO_PIN 33

// ======================= PWM CHANNELS =======================
// Used only on Arduino-ESP32 2.x. Arduino-ESP32 3.x auto-assigns channels.
#define CH_BTS1_RPWM 0
#define CH_BTS1_LPWM 1
#define CH_BTS2_RPWM 2
#define CH_BTS2_LPWM 3
#define CH_SERVO1    4
#define CH_SERVO2    5
#define CH_SERVO3    6
#define CH_SERVO4    7

#define MOTOR_PWM_FREQ 10000
#define MOTOR_PWM_RES  8       // 0..255
#define SERVO_PWM_FREQ 50
#define SERVO_PWM_RES  14      // 0..16383

// ======================= SAFETY SETTINGS =======================
static const bool DEMO_SAFE_MODE_DEFAULT = true;
static const int SAFE_PWM_LIMIT = 50;        // 0..255. Increase only with wheels lifted first.
static const int FULL_PWM_LIMIT = 180;       // Not 255 because 500 RPM 12V motors are aggressive.
static const int SAFE_SERVO_MAX_DELTA = 10;  // degrees from center in safe mode.
static const int FULL_SERVO_MAX_DELTA = 30;  // use only after joints are reinforced.
static const int SERVO_CENTER_ANGLE = 90;
static const int SERVO_HARDWARE_MIN = 35;    // protect S3003 mechanical end-stops.
static const int SERVO_HARDWARE_MAX = 145;   // protect S3003 mechanical end-stops.
static const int OBSTACLE_STOP_CM = 25;
static const unsigned long COMMAND_WATCHDOG_MS = 900;

// Motor side direction correction.
// Default: left forward uses LPWM, right forward uses RPWM.
// If the rover spins instead of moving forward, flip exactly ONE of these values.
// If both sides move backward when command is FORWARD, flip BOTH values.
static const bool BTS1_FORWARD_USES_LPWM = true;
static const bool BTS2_FORWARD_USES_RPWM = true;

// Servo roles and correction.
// Default roles:
// Servo1 = left front, Servo2 = right front, Servo3 = left rear, Servo4 = right rear.
// If any wheel steers opposite, change that servo's DIR sign.
int TRIM_S1 = 0;
int TRIM_S2 = 0;
int TRIM_S3 = 0;
int TRIM_S4 = 0;

int DIR_S1  = +1;
int DIR_S2  = +1;
int DIR_S3  = -1;
int DIR_S4  = -1;

WebServer server(8080);

bool demoSafeMode = DEMO_SAFE_MODE_DEFAULT;
bool armed = false;
bool estopLatched = false;
bool motorsEnabled = false;

float lastThrottle = 0.0f;
float lastSteer = 0.0f;
float hazardScore = 0.0f;
String lastCommand = "BOOT";
unsigned long lastCommandMs = 0;
long lastObstacleCm = 999;

// ======================= COMPATIBLE PWM HELPERS =======================
bool attachPwm(uint8_t pin, uint8_t channel, uint32_t freq, uint8_t resolution) {
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  (void)channel;
  return ledcAttach(pin, freq, resolution);
#else
  ledcSetup(channel, freq, resolution);
  ledcAttachPin(pin, channel);
  return true;
#endif
}

void writePwm(uint8_t pin, uint8_t channel, uint32_t duty) {
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  (void)channel;
  ledcWrite(pin, duty);
#else
  (void)pin;
  ledcWrite(channel, duty);
#endif
}

uint32_t servoDutyFromAngle(int angle) {
  angle = constrain(angle, SERVO_HARDWARE_MIN, SERVO_HARDWARE_MAX);

  // Conservative S3003 pulse range: 600 us to 2400 us.
  const uint32_t periodUs = 1000000UL / SERVO_PWM_FREQ; // 20000 us at 50 Hz
  const uint32_t maxDuty = (1UL << SERVO_PWM_RES) - 1;
  uint32_t pulseUs = map(angle, 0, 180, 600, 2400);

  return (pulseUs * maxDuty) / periodUs;
}

// ======================= FORWARD DECLARATIONS =======================
bool connectToWiFi(const char* ssid, const char* pass, uint32_t timeoutMs);
void startFallbackAP();
void handleRoot();
void handleController();
void handleCommand();
void handleTelemetry();
void handleArm();
void handleDisarm();
void handleEstop();
void handleMode();
void sendJsonStatus(const char* status);
void stopMotors();
void setMotor(float throttle);
void setSteering(float steer);
void writeServoAngle(uint8_t pin, uint8_t channel, int angle);
void setSpin(float spinVal);
long readObstacleCm();
void statusLed(bool on);

// ======================= SETUP =======================
void setup() {
  Serial.begin(115200);
  delay(500);

#if STATUS_LED_ENABLED
  pinMode(STATUS_LED_PIN, OUTPUT);
  statusLed(false);
#endif

#if ULTRASONIC_ENABLED
  pinMode(US_TRIG_PIN, OUTPUT);
  pinMode(US_ECHO_PIN, INPUT);
#endif

  Serial.println();
  Serial.println("==============================================");
  Serial.println("HAGAIR ESP32 Fixed BTS7960 Safe Firmware");
  Serial.println("Pins: BTS1 25/26, BTS2 27/14, Servos 16/17/18/19");
  Serial.println("==============================================");

  attachPwm(BTS1_RPWM_PIN, CH_BTS1_RPWM, MOTOR_PWM_FREQ, MOTOR_PWM_RES);
  attachPwm(BTS1_LPWM_PIN, CH_BTS1_LPWM, MOTOR_PWM_FREQ, MOTOR_PWM_RES);
  attachPwm(BTS2_RPWM_PIN, CH_BTS2_RPWM, MOTOR_PWM_FREQ, MOTOR_PWM_RES);
  attachPwm(BTS2_LPWM_PIN, CH_BTS2_LPWM, MOTOR_PWM_FREQ, MOTOR_PWM_RES);

  attachPwm(SERVO1_PIN, CH_SERVO1, SERVO_PWM_FREQ, SERVO_PWM_RES);
  attachPwm(SERVO2_PIN, CH_SERVO2, SERVO_PWM_FREQ, SERVO_PWM_RES);
  attachPwm(SERVO3_PIN, CH_SERVO3, SERVO_PWM_FREQ, SERVO_PWM_RES);
  attachPwm(SERVO4_PIN, CH_SERVO4, SERVO_PWM_FREQ, SERVO_PWM_RES);

  stopMotors();
  setSteering(0.0f);

  bool connected = false;

  if (String(WIFI_SSID_1).length() > 0 && String(WIFI_SSID_1) != "YOUR_WIFI_NAME") {
    Serial.print("Trying WiFi 1: ");
    Serial.println(WIFI_SSID_1);
    connected = connectToWiFi(WIFI_SSID_1, WIFI_PASSWORD_1, 10000);
  }

  if (!connected && String(WIFI_SSID_2).length() > 0) {
    Serial.print("Trying WiFi 2: ");
    Serial.println(WIFI_SSID_2);
    connected = connectToWiFi(WIFI_SSID_2, WIFI_PASSWORD_2, 10000);
  }

  if (!connected) {
    startFallbackAP();
  } else {
    Serial.print("Connected. Open: http://");
    Serial.print(WiFi.localIP());
    Serial.println(":8080");
  }

  server.on("/", HTTP_GET, handleRoot);
  server.on("/controller", HTTP_POST, handleController);
  server.on("/command", HTTP_POST, handleCommand);
  server.on("/telemetry", HTTP_GET, handleTelemetry);
  server.on("/arm", HTTP_ANY, handleArm);
  server.on("/disarm", HTTP_ANY, handleDisarm);
  server.on("/estop", HTTP_ANY, handleEstop);
  server.on("/mode", HTTP_ANY, handleMode);

  server.begin();

  lastCommandMs = millis();
  statusLed(true);

  Serial.println("READY. Motors are DISARMED by default.");
}

// ======================= LOOP =======================
void loop() {
  server.handleClient();

  lastObstacleCm = readObstacleCm();

  if (ULTRASONIC_ENABLED && lastObstacleCm > 0 && lastObstacleCm < OBSTACLE_STOP_CM && lastThrottle > 0.0f) {
    stopMotors();
    lastCommand = "AUTO_STOP_OBSTACLE";
  }

  if (millis() - lastCommandMs > COMMAND_WATCHDOG_MS) {
    stopMotors();
  }
}

// ======================= WIFI =======================
bool connectToWiFi(const char* ssid, const char* pass, uint32_t timeoutMs) {
  WiFi.disconnect(true);
  WiFi.mode(WIFI_OFF);
  delay(200);

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, pass);
  WiFi.setSleep(false);

  uint32_t start = millis();

  while (WiFi.status() != WL_CONNECTED && millis() - start < timeoutMs) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  return WiFi.status() == WL_CONNECTED;
}

void startFallbackAP() {
  WiFi.disconnect(true);
  WiFi.mode(WIFI_AP);
  WiFi.softAP(AP_SSID, AP_PASS);

  IPAddress ip = WiFi.softAPIP();

  Serial.println("WiFi router failed or not configured.");
  Serial.print("Started ESP32 hotspot: ");
  Serial.println(AP_SSID);
  Serial.print("Password: ");
  Serial.println(AP_PASS);
  Serial.print("Open: http://");
  Serial.print(ip);
  Serial.println(":8080");
}

// ======================= HTTP HANDLERS =======================
void handleRoot() {
  String msg =
    "HAGAIR ESP32 Fixed BTS7960 Safe Firmware\n\n"
    "Pins used:\n"
    "BTS1 motors 1-2-3: RPWM=25, LPWM=26\n"
    "BTS2 motors 4-5-6: RPWM=27, LPWM=14\n"
    "Servos: S1=16, S2=17, S3=18, S4=19\n\n"
    "Endpoints:\n"
    "GET  /telemetry\n"
    "GET  /arm      or POST /arm\n"
    "GET  /disarm   or POST /disarm\n"
    "GET  /estop    or POST /estop\n"
    "POST /controller  JSON: {\"axes\":[spin, throttle, steer]}\n"
    "POST /command     JSON: {\"command\":\"FORWARD\",\"speed\":0.25,\"steer\":0.0}\n"
    "POST /mode        JSON: {\"safe\":true}\n\n"
    "Safety: motors disabled until /arm. Safe mode ON by default.\n";

  server.send(200, "text/plain", msg);
}

void handleController() {
  if (!server.hasArg("plain")) {
    server.send(400, "text/plain", "Missing body");
    return;
  }

  StaticJsonDocument<1024> doc;
  DeserializationError err = deserializeJson(doc, server.arg("plain"));

  if (err) {
    server.send(400, "text/plain", "Bad JSON");
    return;
  }

  float spinVal = doc["axes"][0] | 0.0f;
  float throttleVal = doc["axes"][1] | 0.0f;
  float steeringVal = doc["axes"][2] | 0.0f;

  lastCommandMs = millis();
  lastCommand = "CONTROLLER";

  const float deadzone = 0.10f;

  if (fabs(spinVal) > deadzone && fabs(throttleVal) < deadzone && fabs(steeringVal) < deadzone) {
    setSpin(spinVal);
  } else {
    setSteering(steeringVal);
    setMotor(throttleVal);
  }

  sendJsonStatus("ok");
}

void handleCommand() {
  if (!server.hasArg("plain")) {
    server.send(400, "text/plain", "Missing body");
    return;
  }

  StaticJsonDocument<512> doc;
  DeserializationError err = deserializeJson(doc, server.arg("plain"));

  if (err) {
    server.send(400, "text/plain", "Bad JSON");
    return;
  }

  String command = doc["command"] | "STOP";
  command.toUpperCase();

  float speed = doc["speed"] | 0.0f;
  float steer = doc["steer"] | 0.0f;
  hazardScore = doc["hazard"] | hazardScore;

  lastCommand = command;
  lastCommandMs = millis();

  if (command == "STOP" || command == "EMERGENCY_STOP") {
    stopMotors();
    setSteering(0.0f);
  } else if (command == "FORWARD" || command == "FORWARD_SLOW") {
    setSteering(steer);
    setMotor(fabs(speed));
  } else if (command == "BACKWARD") {
    setSteering(steer);
    setMotor(-fabs(speed));
  } else if (command == "TURN_LEFT") {
    setSteering(-0.6f);
    setMotor(0.0f);
  } else if (command == "TURN_RIGHT") {
    setSteering(0.6f);
    setMotor(0.0f);
  } else if (command == "SCAN") {
    stopMotors();
    setSteering(0.0f);
  } else {
    stopMotors();
  }

  sendJsonStatus("ok");
}

void handleTelemetry() {
  StaticJsonDocument<900> doc;

  doc["ip"] = (WiFi.getMode() == WIFI_AP) ? WiFi.softAPIP().toString() : WiFi.localIP().toString();
  doc["wifi_mode"] = (WiFi.getMode() == WIFI_AP) ? "AP" : "STA";
  doc["safe_mode"] = demoSafeMode;
  doc["armed"] = armed;
  doc["estop"] = estopLatched;
  doc["motors_enabled"] = motorsEnabled;
  doc["last_command"] = lastCommand;
  doc["last_throttle"] = lastThrottle;
  doc["last_steer"] = lastSteer;
  doc["obstacle_cm"] = lastObstacleCm;
  doc["hazard"] = hazardScore;
  doc["max_pwm"] = demoSafeMode ? SAFE_PWM_LIMIT : FULL_PWM_LIMIT;
  doc["max_steer_deg"] = demoSafeMode ? SAFE_SERVO_MAX_DELTA : FULL_SERVO_MAX_DELTA;

  doc["bts1_rpwm"] = BTS1_RPWM_PIN;
  doc["bts1_lpwm"] = BTS1_LPWM_PIN;
  doc["bts2_rpwm"] = BTS2_RPWM_PIN;
  doc["bts2_lpwm"] = BTS2_LPWM_PIN;

  doc["servo1"] = SERVO1_PIN;
  doc["servo2"] = SERVO2_PIN;
  doc["servo3"] = SERVO3_PIN;
  doc["servo4"] = SERVO4_PIN;

  doc["millis"] = millis();

  String out;
  serializeJson(doc, out);

  server.send(200, "application/json", out);
}

void handleArm() {
  estopLatched = false;
  armed = true;
  motorsEnabled = true;

  lastCommand = "ARMED";
  lastCommandMs = millis();

  sendJsonStatus("armed");
}

void handleDisarm() {
  armed = false;
  motorsEnabled = false;

  stopMotors();

  lastCommand = "DISARMED";
  lastCommandMs = millis();

  sendJsonStatus("disarmed");
}

void handleEstop() {
  estopLatched = true;
  armed = false;
  motorsEnabled = false;

  stopMotors();
  setSteering(0.0f);

  lastCommand = "ESTOP";
  lastCommandMs = millis();

  sendJsonStatus("estop");
}

void handleMode() {
  if (server.hasArg("plain")) {
    StaticJsonDocument<256> doc;
    DeserializationError err = deserializeJson(doc, server.arg("plain"));

    if (!err) {
      demoSafeMode = doc["safe"] | true;
    }
  } else {
    // Browser-friendly: /mode?safe=1 or /mode?safe=0
    if (server.hasArg("safe")) {
      demoSafeMode = server.arg("safe") != "0";
    }
  }

  stopMotors();
  setSteering(0.0f);

  lastCommand = demoSafeMode ? "SAFE_MODE_ON" : "SAFE_MODE_OFF";
  lastCommandMs = millis();

  sendJsonStatus("mode_updated");
}

void sendJsonStatus(const char* status) {
  StaticJsonDocument<512> doc;

  doc["status"] = status;
  doc["safe_mode"] = demoSafeMode;
  doc["armed"] = armed;
  doc["estop"] = estopLatched;
  doc["last_command"] = lastCommand;

  String out;
  serializeJson(doc, out);

  server.send(200, "application/json", out);
}

// ======================= MOTOR CONTROL =======================
void stopMotors() {
  writePwm(BTS1_RPWM_PIN, CH_BTS1_RPWM, 0);
  writePwm(BTS1_LPWM_PIN, CH_BTS1_LPWM, 0);
  writePwm(BTS2_RPWM_PIN, CH_BTS2_RPWM, 0);
  writePwm(BTS2_LPWM_PIN, CH_BTS2_LPWM, 0);

  lastThrottle = 0.0f;
}

void setMotor(float throttle) {
  throttle = constrain(throttle, -1.0f, 1.0f);

  if (estopLatched || !armed || !motorsEnabled) {
    stopMotors();
    return;
  }

  if (ULTRASONIC_ENABLED && lastObstacleCm > 0 && lastObstacleCm < OBSTACLE_STOP_CM && throttle > 0.0f) {
    stopMotors();
    lastCommand = "OBSTACLE_BLOCKED_FORWARD";
    return;
  }

  int limit = demoSafeMode ? SAFE_PWM_LIMIT : FULL_PWM_LIMIT;
  int pwmValue = (int)(fabs(throttle) * limit);

  if (fabs(throttle) < 0.05f) {
    pwmValue = 0;
  }

  if (pwmValue == 0) {
    stopMotors();
    return;
  }

  bool forward = throttle > 0.0f;

  // BTS1 = motors 1-2-3, default left side.
  if (BTS1_FORWARD_USES_LPWM) {
    if (forward) {
      writePwm(BTS1_RPWM_PIN, CH_BTS1_RPWM, 0);
      writePwm(BTS1_LPWM_PIN, CH_BTS1_LPWM, pwmValue);
    } else {
      writePwm(BTS1_RPWM_PIN, CH_BTS1_RPWM, pwmValue);
      writePwm(BTS1_LPWM_PIN, CH_BTS1_LPWM, 0);
    }
  } else {
    if (forward) {
      writePwm(BTS1_RPWM_PIN, CH_BTS1_RPWM, pwmValue);
      writePwm(BTS1_LPWM_PIN, CH_BTS1_LPWM, 0);
    } else {
      writePwm(BTS1_RPWM_PIN, CH_BTS1_RPWM, 0);
      writePwm(BTS1_LPWM_PIN, CH_BTS1_LPWM, pwmValue);
    }
  }

  // BTS2 = motors 4-5-6, default right side.
  if (BTS2_FORWARD_USES_RPWM) {
    if (forward) {
      writePwm(BTS2_RPWM_PIN, CH_BTS2_RPWM, pwmValue);
      writePwm(BTS2_LPWM_PIN, CH_BTS2_LPWM, 0);
    } else {
      writePwm(BTS2_RPWM_PIN, CH_BTS2_RPWM, 0);
      writePwm(BTS2_LPWM_PIN, CH_BTS2_LPWM, pwmValue);
    }
  } else {
    if (forward) {
      writePwm(BTS2_RPWM_PIN, CH_BTS2_RPWM, 0);
      writePwm(BTS2_LPWM_PIN, CH_BTS2_LPWM, pwmValue);
    } else {
      writePwm(BTS2_RPWM_PIN, CH_BTS2_RPWM, pwmValue);
      writePwm(BTS2_LPWM_PIN, CH_BTS2_LPWM, 0);
    }
  }

  lastThrottle = throttle;
}

// ======================= SERVO CONTROL =======================
void writeServoAngle(uint8_t pin, uint8_t channel, int angle) {
  uint32_t duty = servoDutyFromAngle(angle);
  writePwm(pin, channel, duty);
}

void setSteering(float steer) {
  steer = constrain(steer, -1.0f, 1.0f);

  int maxDelta = demoSafeMode ? SAFE_SERVO_MAX_DELTA : FULL_SERVO_MAX_DELTA;
  int delta = (int)(steer * maxDelta);

  int s1 = SERVO_CENTER_ANGLE + TRIM_S1 + DIR_S1 * delta;
  int s2 = SERVO_CENTER_ANGLE + TRIM_S2 + DIR_S2 * delta;
  int s3 = SERVO_CENTER_ANGLE + TRIM_S3 + DIR_S3 * delta;
  int s4 = SERVO_CENTER_ANGLE + TRIM_S4 + DIR_S4 * delta;

  writeServoAngle(SERVO1_PIN, CH_SERVO1, s1);
  writeServoAngle(SERVO2_PIN, CH_SERVO2, s2);
  writeServoAngle(SERVO3_PIN, CH_SERVO3, s3);
  writeServoAngle(SERVO4_PIN, CH_SERVO4, s4);

  lastSteer = steer;
}

void setSpin(float spinVal) {
  // Pivot/spin is dangerous for your current weak frame and steering joints.
  if (demoSafeMode) {
    stopMotors();
    setSteering(0.0f);
    lastCommand = "SPIN_BLOCKED_SAFE_MODE";
    return;
  }

  // Even outside safe mode, do not overdo spin. This is for wheel-lift tests only.
  spinVal = constrain(spinVal, -1.0f, 1.0f);

  int pwm = (int)(fabs(spinVal) * 120);

  if (pwm < 10) {
    stopMotors();
    return;
  }

  // Simple opposite-side spin without extreme steering angles.
  if (spinVal > 0) {
    // BTS1 backward, BTS2 forward.
    setSteering(0.0f);

    writePwm(BTS1_RPWM_PIN, CH_BTS1_RPWM, pwm);
    writePwm(BTS1_LPWM_PIN, CH_BTS1_LPWM, 0);

    writePwm(BTS2_RPWM_PIN, CH_BTS2_RPWM, pwm);
    writePwm(BTS2_LPWM_PIN, CH_BTS2_LPWM, 0);
  } else {
    // BTS1 forward, BTS2 backward.
    setSteering(0.0f);

    writePwm(BTS1_RPWM_PIN, CH_BTS1_RPWM, 0);
    writePwm(BTS1_LPWM_PIN, CH_BTS1_LPWM, pwm);

    writePwm(BTS2_RPWM_PIN, CH_BTS2_RPWM, 0);
    writePwm(BTS2_LPWM_PIN, CH_BTS2_LPWM, pwm);
  }
}

// ======================= OPTIONAL OBSTACLE SENSOR =======================
long readObstacleCm() {
#if ULTRASONIC_ENABLED
  digitalWrite(US_TRIG_PIN, LOW);
  delayMicroseconds(2);

  digitalWrite(US_TRIG_PIN, HIGH);
  delayMicroseconds(10);

  digitalWrite(US_TRIG_PIN, LOW);

  long duration = pulseIn(US_ECHO_PIN, HIGH, 25000);

  if (duration <= 0) {
    return 999;
  }

  return duration / 58;
#else
  return 999;
#endif
}

// ======================= STATUS LED =======================
void statusLed(bool on) {
#if STATUS_LED_ENABLED
  digitalWrite(STATUS_LED_PIN, on ? HIGH : LOW);
#else
  (void)on;
#endif
}