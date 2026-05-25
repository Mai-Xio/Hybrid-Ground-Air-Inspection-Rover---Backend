from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, Any
import math
import random
import time


@dataclass
class SensorSnapshot:
    timestamp: float
    step: int
    scenario: str
    temperature_c: float
    humidity_pct: float
    pressure_hpa: float
    pm25_ug_m3: float
    pm10_ug_m3: float
    co_mg_m3: float
    no2_ug_m3: float
    voc_index: float
    methane_lel_pct: float
    h2s_ppm: float
    nh3_ppm: float
    co2_ppm: float
    water_flow_lpm: float
    liquid_ph: float
    soil_ph: float
    soil_ec_ms_cm: float
    soil_moisture_pct: float
    soil_n_mgkg: float
    soil_p_mgkg: float
    soil_k_mgkg: float
    slope_deg: float
    obstacle_cm: float
    ambient_lux: float
    wind_speed_kmh: float
    battery_pct: float
    solar_watt: float
    gps_fix_quality: float
    signal_quality: float
    vision_certainty: float
    sensor_availability: float
    audio_level_db: float
    audio_distress_probability: float
    image_brightness: float
    ir_hotspot_probability: float
    terrain_hint: str

    def confidence(self) -> float:
        c = (
            self.sensor_availability
            * self.signal_quality
            * self.vision_certainty
            * self.gps_fix_quality
        )
        return max(0.0, min(1.0, c))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SimulatedSensorReader:
    """
    Generates repeatable-enough demonstration data for five patent scenarios.

    Scenarios:
    normal, pollution, flood, fire, night.
    """

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    def _jitter(self, value: float, amount: float) -> float:
        return value + self.rng.uniform(-amount, amount)

    def read(self, scenario: str = "normal", step: int = 0) -> SensorSnapshot:
        scenario = scenario.lower().strip()
        t = time.time()
        wave = math.sin(step / 4.0)

        # Normal baseline
        data = dict(
            timestamp=t,
            step=step,
            scenario=scenario,
            temperature_c=self._jitter(29.0, 1.0),
            humidity_pct=self._jitter(56.0, 4.0),
            pressure_hpa=self._jitter(1009.0, 1.2),
            pm25_ug_m3=self._jitter(38.0, 5.0),
            pm10_ug_m3=self._jitter(82.0, 8.0),
            co_mg_m3=self._jitter(0.8, 0.2),
            no2_ug_m3=self._jitter(32.0, 5.0),
            voc_index=self._jitter(110.0, 12.0),
            methane_lel_pct=self._jitter(0.5, 0.2),
            h2s_ppm=self._jitter(0.2, 0.1),
            nh3_ppm=self._jitter(0.4, 0.2),
            co2_ppm=self._jitter(520.0, 40.0),
            water_flow_lpm=self._jitter(5.0, 1.0),
            liquid_ph=self._jitter(7.1, 0.2),
            soil_ph=self._jitter(6.8, 0.2),
            soil_ec_ms_cm=self._jitter(0.8, 0.12),
            soil_moisture_pct=self._jitter(28.0, 4.0),
            soil_n_mgkg=self._jitter(55.0, 8.0),
            soil_p_mgkg=self._jitter(22.0, 4.0),
            soil_k_mgkg=self._jitter(160.0, 20.0),
            slope_deg=self._jitter(5.0, 2.0),
            obstacle_cm=self._jitter(120.0, 20.0),
            ambient_lux=self._jitter(450.0, 80.0),
            wind_speed_kmh=self._jitter(10.0, 3.0),
            battery_pct=max(15.0, 96.0 - step * 0.8),
            solar_watt=self._jitter(14.0 + 4.0 * max(0.0, wave), 2.0),
            gps_fix_quality=0.92,
            signal_quality=0.90,
            vision_certainty=0.86,
            sensor_availability=0.95,
            audio_level_db=self._jitter(42.0, 5.0),
            audio_distress_probability=0.02,
            image_brightness=0.70,
            ir_hotspot_probability=0.02,
            terrain_hint="pavement",
        )

        if scenario == "pollution":
            data.update(
                pm25_ug_m3=self._jitter(180.0, 18.0),
                pm10_ug_m3=self._jitter(260.0, 25.0),
                co_mg_m3=self._jitter(7.5, 1.2),
                no2_ug_m3=self._jitter(170.0, 20.0),
                voc_index=self._jitter(280.0, 30.0),
                methane_lel_pct=self._jitter(5.0, 1.0),
                h2s_ppm=self._jitter(8.0, 2.0),
                terrain_hint="pavement",
                obstacle_cm=self._jitter(80.0, 15.0),
            )
        elif scenario == "flood":
            data.update(
                water_flow_lpm=self._jitter(35.0, 5.0),
                liquid_ph=self._jitter(9.4, 0.4),
                soil_moisture_pct=self._jitter(78.0, 5.0),
                slope_deg=self._jitter(12.0, 2.5),
                obstacle_cm=self._jitter(45.0, 10.0),
                terrain_hint="flooded",
                vision_certainty=0.78,
            )
        elif scenario == "fire":
            data.update(
                co_mg_m3=self._jitter(12.0, 2.5),
                no2_ug_m3=self._jitter(210.0, 20.0),
                pm25_ug_m3=self._jitter(145.0, 22.0),
                pm10_ug_m3=self._jitter(230.0, 35.0),
                temperature_c=self._jitter(39.0, 3.0),
                ir_hotspot_probability=0.88,
                image_brightness=0.45,
                audio_level_db=self._jitter(65.0, 4.0),
                terrain_hint="rubble",
                obstacle_cm=self._jitter(35.0, 9.0),
            )
        elif scenario == "night":
            data.update(
                ambient_lux=self._jitter(4.0, 2.0),
                image_brightness=0.12,
                ir_hotspot_probability=0.40 if step % 5 == 0 else 0.08,
                terrain_hint="unknown",
                vision_certainty=0.62,
                audio_distress_probability=0.18 if step % 7 == 0 else 0.04,
            )
        elif scenario == "industrial":
            data.update(
                voc_index=self._jitter(360.0, 35.0),
                methane_lel_pct=self._jitter(14.0, 3.0),
                h2s_ppm=self._jitter(20.0, 3.0),
                nh3_ppm=self._jitter(14.0, 3.0),
                co2_ppm=self._jitter(1800.0, 250.0),
                soil_ec_ms_cm=self._jitter(8.5, 1.0),
                soil_ph=self._jitter(5.0, 0.4),
                terrain_hint="gravel",
            )

        return SensorSnapshot(**data)


class HardwareSensorReader:
    """
    Placeholder for real sensor polling.

    For a noob-friendly undergrad demo, keep this class as a thin layer that can be
    filled later with actual drivers for SPS30, BMP390, SHT40, MQ sensors, etc.
    The rest of the pipeline already works with the same SensorSnapshot object.
    """

    def __init__(self):
        self.sim = SimulatedSensorReader(seed=123)

    def read(self, scenario: str = "normal", step: int = 0) -> SensorSnapshot:
        # Until physical sensors are wired and verified, hardware mode falls back
        # to simulation so the project never crashes during presentation.
        snap = self.sim.read(scenario=scenario, step=step)
        snap.scenario = "hardware-fallback-" + scenario
        return snap


class SensorValidator:
    def validate(self, snap: SensorSnapshot) -> Dict[str, str]:
        issues = {}
        if not (0 <= snap.humidity_pct <= 100):
            issues["humidity_pct"] = "outside 0..100"
        if snap.pm25_ug_m3 < 0 or snap.pm10_ug_m3 < 0:
            issues["particulate"] = "negative particulate value"
        if not (0 <= snap.liquid_ph <= 14) or not (0 <= snap.soil_ph <= 14):
            issues["ph"] = "pH outside 0..14"
        if snap.obstacle_cm < 0:
            issues["obstacle_cm"] = "negative distance"
        return issues
