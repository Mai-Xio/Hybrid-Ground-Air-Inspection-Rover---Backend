from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict
from typing import Dict, Any, List

from hagair_software.sensor_hub.sensor_hub import SimulatedSensorReader, HardwareSensorReader, SensorValidator
from hagair_software.aqi_engine.aqi_engine import AQIEngine
from hagair_software.soil_analysis.soil_engine import SoilAnalysisEngine
from hagair_software.terrain_analysis.terrain_engine import TerrainAnalysisEngine
from hagair_software.ai_detection.detection_engine import AIDetectionEngine
from hagair_software.audio_module.audio_engine import AudioAnalysisEngine
from hagair_software.hazard_fusion.hazard_fusion import HazardFusionEngine
from hagair_software.ml_training.training_loop import OnlineTrainingLoop
from hagair_software.utils.data_logger import DataLogger
from hagair_software.utils.drone_controller import DroneController
from hagair_software.utils.lifting_legs import LiftingLegsController
from hagair_software.utils.rover_client import RoverClient
from hagair_software.dashboard.dashboard import DashboardRenderer
from hagair_software.config.settings import MISSION_PROFILES


def water_score_from_snapshot(snap) -> float:
    flow_risk = 0.0
    if snap.water_flow_lpm < 0.5:
        flow_risk = 0.45  # possible blockage if channel is expected to flow
    elif snap.water_flow_lpm > 30:
        flow_risk = 0.95
    elif snap.water_flow_lpm > 18:
        flow_risk = 0.65
    ph_risk = 0.0 if 5.5 <= snap.liquid_ph <= 8.5 else min(1.0, abs(snap.liquid_ph - 7.0) / 5.0)
    return round(min(1.0, 0.70 * flow_risk + 0.30 * ph_risk), 4)


def power_score_from_snapshot(snap) -> float:
    low_battery = 1.0 - min(1.0, snap.battery_pct / 100.0)
    solar_problem = 0.25 if snap.solar_watt < 3.0 else 0.0
    return round(min(1.0, 0.80 * low_battery + solar_problem), 4)


def command_from_fusion(fusion_result) -> str:
    tier = fusion_result.response.tier
    if tier == "CRITICAL":
        return "STOP"
    if tier == "HIGH":
        return "STOP"
    if tier == "MEDIUM":
        return "SCAN"
    return "FORWARD_SLOW"


def run_pipeline(
    steps: int = 20,
    scenario: str = "normal",
    profile: str = "general",
    hardware: bool = False,
    rover_url: str | None = None,
    send_commands: bool = False,
    dashboard: bool = True,
    sleep_s: float = 0.0,
) -> List[Dict[str, Any]]:
    reader = HardwareSensorReader() if hardware else SimulatedSensorReader()
    validator = SensorValidator()
    aqi_engine = AQIEngine()
    soil_engine = SoilAnalysisEngine()
    terrain_engine = TerrainAnalysisEngine()
    detection_engine = AIDetectionEngine()
    audio_engine = AudioAnalysisEngine()
    fusion_engine = HazardFusionEngine(profile=profile)
    trainer = OnlineTrainingLoop()
    logger = DataLogger(mission_name=f"{scenario}_{profile}")
    drone = DroneController()
    legs = LiftingLegsController()
    rover = RoverClient(rover_url) if rover_url else None

    records: List[Dict[str, Any]] = []

    print(f"\nHAGAIR v3.0 mission start | scenario={scenario} | profile={profile} | hardware={hardware}")
    print("STEP | AQI | E | T | V | S | W | A | H | TIER | ACTIONS")
    print("-" * 96)

    for step in range(steps):
        snap = reader.read(scenario=scenario, step=step)
        issues = validator.validate(snap)

        aqi = aqi_engine.compute(snap)
        soil = soil_engine.analyze(snap)
        terrain = terrain_engine.analyze(frame=None, snap=snap)
        visual = detection_engine.analyze(frame=None, scenario=scenario, snap=snap)
        audio = audio_engine.analyze(snap, scenario=scenario)
        W = water_score_from_snapshot(snap)
        P = power_score_from_snapshot(snap)

        fusion = fusion_engine.compute(
            visual=visual.visual_score,
            environment=aqi.environmental_score,
            terrain=terrain.terrain_score,
            confidence=snap.confidence(),
            soil=soil.soil_score,
            water=W,
            acoustic=audio.acoustic_score,
            power=P,
            wind_speed_kmh=snap.wind_speed_kmh,
        )

        drone_decision = drone.decide(fusion, wind_speed_kmh=snap.wind_speed_kmh)
        leg_decision = legs.decide(terrain, battery_pct=snap.battery_pct)

        command = command_from_fusion(fusion)
        rover_reply = None
        if rover and send_commands:
            try:
                rover_reply = rover.post_command(command=command, speed=0.15 if command == "FORWARD_SLOW" else 0.0)
            except Exception as e:
                rover_reply = {"ok": False, "error": str(e)}

        record = {
            "snapshot": snap.to_dict(),
            "validation_issues": issues,
            "aqi": asdict(aqi),
            "soil": asdict(soil),
            "terrain": asdict(terrain),
            "visual": {
                "visual_score": visual.visual_score,
                "scene": visual.scene,
                "detections": [asdict(d) for d in visual.detections],
                "recommended_motion": visual.recommended_motion,
            },
            "audio": asdict(audio),
            "fusion": fusion.to_dict(),
            "drone": asdict(drone_decision),
            "legs": asdict(leg_decision),
            "rover_command": command,
            "rover_reply": rover_reply,
        }
        logger.log(record)
        records.append(record)
        trainer.add_sample({"components": fusion.components}, fusion.H, source="auto")
        trainer.maybe_update_fusion_weights(fusion_engine, min_samples=30)

        print(
            f"{step:>4} | {aqi.aqi:>3} | {aqi.environmental_score:.2f} | "
            f"{terrain.terrain_score:.2f} | {visual.visual_score:.2f} | "
            f"{soil.soil_score:.2f} | {W:.2f} | {audio.acoustic_score:.2f} | "
            f"{fusion.H:.2f} | {fusion.response.tier:<8} | {','.join(fusion.response.actions)}"
        )
        if sleep_s > 0:
            time.sleep(sleep_s)

    print("-" * 96)
    print(f"Mission log: {logger.path}")

    if dashboard:
        dash_path = DashboardRenderer().render(records)
        print(f"Dashboard: {dash_path}")

    return records


def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="HAGAIR v3.0 complete working demo pipeline")
    p.add_argument("--steps", type=int, default=20)
    p.add_argument("--scenario", default="normal", choices=["normal", "pollution", "flood", "fire", "night", "industrial"])
    p.add_argument("--profile", default="general", choices=list(MISSION_PROFILES.keys()))
    p.add_argument("--hardware", action="store_true", help="use hardware reader; currently falls back safely if drivers unavailable")
    p.add_argument("--rover-url", default=None, help="ESP32 base URL, e.g. http://192.168.1.145:8080")
    p.add_argument("--send-commands", action="store_true", help="send safe commands to ESP32; use only with DEMO_SAFE_MODE on")
    p.add_argument("--no-dashboard", action="store_true")
    p.add_argument("--sleep", type=float, default=0.0)
    return p


def main():
    args = build_argparser().parse_args()
    run_pipeline(
        steps=args.steps,
        scenario=args.scenario,
        profile=args.profile,
        hardware=args.hardware,
        rover_url=args.rover_url,
        send_commands=args.send_commands,
        dashboard=not args.no_dashboard,
        sleep_s=args.sleep,
    )


if __name__ == "__main__":
    main()
