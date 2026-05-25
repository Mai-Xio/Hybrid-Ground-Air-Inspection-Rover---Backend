"""
Global configuration for the HAGAIR v3.0 demo software.

This module is intentionally simulation-first:
- It runs on a normal laptop with no sensors.
- Hardware integrations are behind flags and small client wrappers.
- Values can be replaced later with real sensor drivers.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models"
LOG_DIR = DATA_DIR / "logs"

LOW_ALERT = 0.35
HIGH_ALERT = 0.60
CRITICAL_ALERT = 0.85
MAX_SAFE_WIND_KMH = 25.0

# Current student-prototype safety defaults.
# The ESP32 firmware also defaults to safe demonstration mode.
MOTION_SAFE_DEFAULT = True
MAX_DEMO_PWM = 65            # 0..255, low enough for wheel-lift tests only
MAX_DEMO_STEERING_DEG = 10   # protects weak steering joints
MIN_OBSTACLE_STOP_CM = 25

MISSION_PROFILES = {
    # a,b,c,d,e,w,s,aud map to visual, environmental, terrain,
    # confidence, soil, water, solar/power, acoustic.
    "general": {
        "visual": 0.18, "environment": 0.18, "terrain": 0.16, "confidence": 0.08,
        "soil": 0.14, "water": 0.14, "acoustic": 0.08, "power": 0.04
    },
    "drainage": {
        "visual": 0.14, "environment": 0.28, "terrain": 0.12, "confidence": 0.06,
        "soil": 0.10, "water": 0.24, "acoustic": 0.04, "power": 0.02
    },
    "road_safety": {
        "visual": 0.30, "environment": 0.10, "terrain": 0.34, "confidence": 0.08,
        "soil": 0.04, "water": 0.08, "acoustic": 0.04, "power": 0.02
    },
    "flood_zone": {
        "visual": 0.20, "environment": 0.20, "terrain": 0.18, "confidence": 0.06,
        "soil": 0.08, "water": 0.22, "acoustic": 0.04, "power": 0.02
    },
    "air_quality": {
        "visual": 0.08, "environment": 0.58, "terrain": 0.08, "confidence": 0.06,
        "soil": 0.06, "water": 0.08, "acoustic": 0.04, "power": 0.02
    },
    "night_ir": {
        "visual": 0.46, "environment": 0.16, "terrain": 0.10, "confidence": 0.07,
        "soil": 0.05, "water": 0.06, "acoustic": 0.08, "power": 0.02
    },
    "soil_survey": {
        "visual": 0.08, "environment": 0.16, "terrain": 0.08, "confidence": 0.07,
        "soil": 0.47, "water": 0.08, "acoustic": 0.04, "power": 0.02
    },
    "industrial_chemical": {
        "visual": 0.14, "environment": 0.38, "terrain": 0.08, "confidence": 0.06,
        "soil": 0.14, "water": 0.08, "acoustic": 0.06, "power": 0.06
    },
}

# CPCB India-style AQI breakpoints used for demo computation.
# Concentration units:
# PM2.5, PM10, NO2: ug/m3. CO: mg/m3.
AQI_BREAKPOINTS = {
    "pm25": [
        (0, 30, 0, 50, "Good"),
        (31, 60, 51, 100, "Satisfactory"),
        (61, 90, 101, 200, "Moderate"),
        (91, 120, 201, 300, "Poor"),
        (121, 250, 301, 400, "Very Poor"),
        (251, 500, 401, 500, "Severe"),
    ],
    "pm10": [
        (0, 50, 0, 50, "Good"),
        (51, 100, 51, 100, "Satisfactory"),
        (101, 250, 101, 200, "Moderate"),
        (251, 350, 201, 300, "Poor"),
        (351, 430, 301, 400, "Very Poor"),
        (431, 600, 401, 500, "Severe"),
    ],
    "no2": [
        (0, 40, 0, 50, "Good"),
        (41, 80, 51, 100, "Satisfactory"),
        (81, 180, 101, 200, "Moderate"),
        (181, 280, 201, 300, "Poor"),
        (281, 400, 301, 400, "Very Poor"),
        (401, 800, 401, 500, "Severe"),
    ],
    "co": [
        (0, 1.0, 0, 50, "Good"),
        (1.1, 2.0, 51, 100, "Satisfactory"),
        (2.1, 10.0, 101, 200, "Moderate"),
        (10.1, 17.0, 201, 300, "Poor"),
        (17.1, 34.0, 301, 400, "Very Poor"),
        (34.1, 50.0, 401, 500, "Severe"),
    ],
}

TERRAIN_RISK = {
    "flat": 0.10,
    "pavement": 0.16,
    "gravel": 0.32,
    "rubble": 0.60,
    "mud": 0.70,
    "flooded": 0.85,
    "stairs": 0.76,
    "unknown": 0.55,
}

SOIL_CLASSES = [
    "Uncontaminated",
    "Agricultural Runoff",
    "Industrial Discharge",
    "Acidic Contamination",
    "Saline Intrusion",
    "Heavy Metal Indicator",
]

COMMAND_MAP = {
    "LOW": "FORWARD_SLOW",
    "MEDIUM": "PAUSE_AND_SCAN",
    "HIGH": "STOP_ALERT",
    "CRITICAL": "EMERGENCY_STOP_DEPLOY",
}
