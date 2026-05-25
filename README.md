# HAGAIR v3.0 Complete Working Demo Pack

Project title:

**Hybrid Autonomous Ground-Air Inspection Rover with Integrated Drone Docking, Quadruped Docking, Obstacle Detection, Image Analysis, and AQI-Based Machine Learning for Hazardous Environment Monitoring**


## What is included in my project

1. `hagair_software/`  
   Complete Python demo software:
   - `main_pipeline.py`
   - sensor hub
   - AQI engine
   - soil analysis
   - terrain analysis
   - image/AI detection stub
   - audio hazard stub
   - hazard fusion
   - drone controller
   - lifting legs / quadruped standby logic
   - static HTML dashboard
   - tests

2. `arduino/rover_esp32_safe/`  
   ESP32-S3 safe firmware based on the Papaya Pathfinder pin map:
   - safe mode ON by default
   - motor PWM capped
   - steering angle capped
   - emergency stop endpoint
   - telemetry endpoint
   - HTTP command endpoint

3. `desktop_controller/`  
   Simple Python keyboard controller for the ESP32 firmware.

## Demo

Open a terminal inside this folder:

```bash
cd HAGAIR_v3_complete_working
python -m hagair_software.main_pipeline --steps 10 --scenario normal --profile general
python -m hagair_software.main_pipeline --steps 10 --scenario pollution --profile air_quality
python -m hagair_software.main_pipeline --steps 10 --scenario flood --profile drainage
python -m hagair_software.main_pipeline --steps 10 --scenario fire --profile night_ir
python -m hagair_software.tests.run_tests
```

After every run, open:

```text
hagair_software/data/latest_dashboard.html
```

This gives a dashboard for demonstration even when the rover is not moving.

## Install dependencies

The core software is intentionally dependency-light and runs on Python standard library only.

Optional scientific stack:

```bash
pip install -r hagair_software/requirements.txt
```

## Demo scenarios

| Scenario | What it demonstrates |
|---|---|
| `normal` | Low hazard, telemetry logging, dashboard |
| `pollution` | AQI engine, gas/biogas flags, high hazard alert |
| `flood` | water-flow risk, terrain risk, halt / drone deployment |
| `fire` | thermal/IR hotspot, smoke/CO proxy, high visual hazard |
| `night` | low-light/thermal inspection mode |
| `industrial` | VOC / CH4 / H2S / soil EC chemical hazard |

## Using with ESP32 rover

1. Flash the firmware in `arduino/rover_esp32_safe/`.
2. Open Serial Monitor at `115200`.
3. Copy the printed IP address.
4. Test telemetry:

```bash
python desktop_controller/keyboard_controller.py http://YOUR_ESP32_IP:8080
```

Here, The firmware defaults to safe mode, it was originally used for preventing hardware damage while making of hardware prototype integration.
