from __future__ import annotations

from dataclasses import dataclass
from hagair_software.config.settings import MAX_SAFE_WIND_KMH


@dataclass
class DroneDecision:
    state: str
    reason: str


class DroneController:
    def decide(self, fusion_result, wind_speed_kmh: float) -> DroneDecision:
        actions = fusion_result.response.actions
        if "DEPLOY_DRONE" in actions and wind_speed_kmh <= MAX_SAFE_WIND_KMH:
            return DroneDecision("DEPLOY", "critical/high hazard and wind is within safe limit")
        if "DRONE_LOCKED_WIND_TOO_HIGH" in actions:
            return DroneDecision("LOCKED", "wind speed too high for safe drone demonstration")
        if "DRONE_STANDBY" in actions:
            return DroneDecision("STANDBY", "high alert but operator confirmation recommended")
        return DroneDecision("DOCKED", "no drone deployment required")
