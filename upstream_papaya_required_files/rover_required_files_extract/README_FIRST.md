# How to use this extracted folder

## Arduino firmware
Open:
`pathfinder/firmware-wifi/firmware-wifi.ino`

Before compiling:
1. Copy `wifi_config.h_TEMPLATE`.
2. Rename the copy to `wifi_config.h`.
3. Put your WiFi/hotspot name and password inside it.

## Desktop controller
Open:
`desktop-controller/src/controller.py`

Before running:
1. Copy `config.json_TEMPLATE`.
2. Rename the copy to `config.json`.
3. Change the IP to the IP printed by the ESP32 Serial Monitor, keeping `http://` at the start.

## First safe test
Do not connect the 12V motor power yet.
First upload the firmware with ESP32 powered only from USB, then check Serial Monitor.
