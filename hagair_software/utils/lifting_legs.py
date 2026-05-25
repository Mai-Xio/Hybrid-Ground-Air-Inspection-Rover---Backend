from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LegDecision:
    state: str
    reason: str


class LiftingLegsController:
    def decide(self, terrain_result, battery_pct: float) -> LegDecision:
        if battery_pct < 15:
            return LegDecision("LOCKED_LOW_BATTERY", "battery too low for recovery sequence")
        if terrain_result.entrapment_risk >= 0.70:
            return LegDecision("DEPLOY_RECOVERY_STANDBY", "entrapment risk high")
        if terrain_result.terrain_class in {"rubble", "flooded", "stairs"}:
            return LegDecision("STANDBY", f"terrain class {terrain_result.terrain_class} may need leg/quadruped support")
        return LegDecision("STOWED", "terrain within rover-only demonstration limit")
