# Extracted required files for Hybrid Autonomous Ground-Air Inspection Rover

Extraction date: 2026-05-06

Source repository:
https://github.com/tronxi/papaya-pathfinder

This extraction keeps only the files immediately required to start firmware modification and controller testing for the larger Pathfinder rover.

## Files included

1. `pathfinder/firmware-wifi/firmware-wifi.ino`
   - Original WiFi firmware for the larger rover.
   - Handles ESP32 WiFi connection, HTTP `/controller` endpoint, 4 steering servos, and 2 BTS7960 motor-driver channels.
   - This is the first file to modify for safe demo mode, speed limiting, ultrasonic obstacle stop, and later sensor endpoints.

2. `pathfinder/firmware-wifi/wifi_config.h_TEMPLATE`
   - Template file because the original sketch includes `wifi_config.h`, but the public repo does not expose a credentials file.
   - Rename it to `wifi_config.h` before compiling.

3. `desktop-controller/src/controller.py`
   - Original Python controller.
   - Reads a gamepad using pygame and sends JSON to the ESP32 HTTP endpoint every 0.05 seconds.
   - It expects `config.json` to exist in the same folder.

4. `desktop-controller/src/config.json_TEMPLATE`
   - Template for the rover IP address.
   - Rename it to `config.json` and replace the IP after the ESP32 prints its IP in Serial Monitor.


5. `ia-controller/src/main.py`
   - Original image-analysis controller.
   - Fetches a camera frame from an ESP32 `/capture` URL, runs a vision-language model, and draws a rover navigation UI.
   - This is relevant for your image-analysis claim, but it must be simplified or changed for a Windows/noob demo because the original uses a heavy Qwen3-VL model and `device="mps"` for Apple Silicon.

## Not extracted yet

- Android controller source: optional for later; desktop/Python is easier for noob testing.
- ELRS firmware: optional; not needed for WiFi demo.
- 3D model STL/STEP files: required for printing, but not required for code modification.
- Schematics images/PDF: required during wiring verification; cited separately from the repo.

## Immediate next engineering changes

- Add `DEMO_SAFE_MODE` so motors stay disabled by default.
- Add `MAX_MOTOR_PWM` cap for 500 RPM 12V motors.
- Reduce steering angle from 35-45 degrees to 8-15 degrees for MG995/weak joints.
- Add `/status`, `/demo`, `/servo-test`, `/motor-test`, and `/stop` endpoints.
- Add ultrasonic sensor obstacle stop logic.
- Add fake/simulated AQI + image-analysis status endpoint for presentation if physical movement is unsafe.
