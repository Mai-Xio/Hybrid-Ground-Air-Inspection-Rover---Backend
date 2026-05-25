from __future__ import annotations

import json
import urllib.request
from typing import Dict, Any


class RoverClient:
    """
    Minimal HTTP client for ESP32 firmware endpoints.

    Use only when the rover is on a stand or DEMO_SAFE_MODE is enabled.
    """

    def __init__(self, base_url: str, timeout: float = 1.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def post_command(self, command: str, speed: float = 0.0, steer: float = 0.0) -> Dict[str, Any]:
        payload = {"command": command, "speed": speed, "steer": steer}
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.base_url + "/command",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def get_telemetry(self) -> Dict[str, Any]:
        with urllib.request.urlopen(self.base_url + "/telemetry", timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def estop(self) -> Dict[str, Any]:
        req = urllib.request.Request(self.base_url + "/estop", data=b"{}", headers={"Content-Type":"application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
