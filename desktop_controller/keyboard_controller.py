"""
Keyboard controller for the ESP32 rover firmware.

Use only when:
1. Rover is lifted on a stand, OR
2. DEMO_SAFE_MODE is enabled in firmware.

Controls:
  w = forward slow
  s = backward slow
  a = steer/turn left
  d = steer/turn right
  x = stop
  e = emergency stop
  q = quit
  
"""

from __future__ import annotations

import json
import urllib.request
import sys
import time


def post_json(url: str, payload: dict):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=1) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    base_url = sys.argv[1] if len(sys.argv) > 1 else " http://10.67.166.248:8080"
    print(f"Rover URL: {base_url}")
    print("Commands: w/s/a/d/x/e/q")

    while True:
        key = input("cmd> ").strip().lower()
        if key == "q":
            break
        if key == "e":
            print(post_json(base_url + "/estop", {}))
            continue
        mapping = {
            "w": {"command": "FORWARD", "speed": 0.20, "steer": 0.0},
            "s": {"command": "BACKWARD", "speed": 0.20, "steer": 0.0},
            "a": {"command": "TURN_LEFT", "speed": 0.0, "steer": -0.5},
            "d": {"command": "TURN_RIGHT", "speed": 0.0, "steer": 0.5},
            "x": {"command": "STOP", "speed": 0.0, "steer": 0.0},
        }
        if key not in mapping:
            print("unknown key")
            continue
        try:
            print(post_json(base_url + "/command", mapping[key]))
        except Exception as exc:
            print("ERROR:", exc)
        time.sleep(0.05)


if __name__ == "__main__":
    main()
