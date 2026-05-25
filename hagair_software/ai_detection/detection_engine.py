from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Detection:
    label: str
    confidence: float
    bbox: tuple = (0, 0, 0, 0)


@dataclass
class DetectionResult:
    visual_score: float
    scene: str
    detections: List[Detection]
    recommended_motion: str


class AIDetectionEngine:
    """
    Lightweight visual hazard demo.

    This is not pretending to run YOLO without weights. If model files are added
    later, you can route frames to YOLOv8/TFLite. For now it produces stable,
    explainable detections from scenario + sensor inputs.
    """

    def analyze(self, frame: Optional[object], scenario: str, snap) -> DetectionResult:
        scenario = scenario.lower()
        detections: List[Detection] = []
        scene = "clear inspection path"
        motion = "FORWARD_SLOW"
        V = 0.10

        if snap.obstacle_cm < 25:
            detections.append(Detection("blocking_obstacle", 0.88))
            scene = "near obstacle in front"
            motion = "STOP"
            V = max(V, 0.80)
        elif snap.obstacle_cm < 55:
            detections.append(Detection("obstacle_ahead", 0.72))
            scene = "obstacle close, scan before moving"
            motion = "PAUSE_AND_SCAN"
            V = max(V, 0.55)

        if scenario == "flood" or snap.water_flow_lpm > 25:
            detections.append(Detection("water_body_or_flooding", 0.82))
            scene = "water/flood risk visible"
            motion = "STOP"
            V = max(V, 0.78)

        if scenario == "fire" or snap.ir_hotspot_probability > 0.65:
            detections.append(Detection("thermal_hotspot_or_smoke", max(0.75, snap.ir_hotspot_probability)))
            scene = "thermal/fire anomaly"
            motion = "STOP_ALERT"
            V = max(V, 0.88)

        if scenario == "night":
            detections.append(Detection("low_light_scene", 0.80))
            scene = "low-light thermal inspection mode"
            V = max(V, 0.45)

        if snap.image_brightness < 0.18:
            V = max(V, 0.40)
            motion = "LIGHTS_ON_SCAN" if motion == "FORWARD_SLOW" else motion

        return DetectionResult(
            visual_score=round(min(1.0, V), 4),
            scene=scene,
            detections=detections,
            recommended_motion=motion,
        )
