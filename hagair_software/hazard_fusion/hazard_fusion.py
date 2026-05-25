from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List

from hagair_software.config.settings import (
    MISSION_PROFILES,
    LOW_ALERT,
    HIGH_ALERT,
    CRITICAL_ALERT,
    MAX_SAFE_WIND_KMH,
)


@dataclass
class FusionResponse:
    tier: str
    actions: List[str]
    reason: str


@dataclass
class FusionResult:
    H: float
    components: Dict[str, float]
    weights: Dict[str, float]
    response: FusionResponse

    def to_dict(self):
        d = asdict(self)
        return d


class HazardFusionEngine:
    """
    Composite hazard score:
    H = αV + βE + γT + δC + εW + ζS + ηA + θP

    Here confidence is converted to confidence-risk (1-C) so poor sensing
    increases caution instead of falsely lowering the score.
    """

    def __init__(self, profile: str = "general"):
        if profile not in MISSION_PROFILES:
            raise ValueError(f"Unknown profile: {profile}. Options: {list(MISSION_PROFILES)}")
        self.profile = profile
        self.weights = self._normalise(MISSION_PROFILES[profile])
        self.feedback = []

    def _normalise(self, weights: Dict[str, float]) -> Dict[str, float]:
        s = sum(max(0.0, float(v)) for v in weights.values())
        if s <= 0:
            raise ValueError("weight sum must be >0")
        return {k: max(0.0, float(v)) / s for k, v in weights.items()}

    def compute(
        self,
        visual: float,
        environment: float,
        terrain: float,
        confidence: float,
        soil: float,
        water: float,
        acoustic: float,
        power: float = 0.0,
        wind_speed_kmh: float = 0.0,
    ) -> FusionResult:
        components = {
            "visual": self._clip(visual),
            "environment": self._clip(environment),
            "terrain": self._clip(terrain),
            "confidence": 1.0 - self._clip(confidence),
            "soil": self._clip(soil),
            "water": self._clip(water),
            "acoustic": self._clip(acoustic),
            "power": self._clip(power),
        }
        H = sum(self.weights.get(k, 0.0) * components[k] for k in components)
        H = self._clip(H)

        # Safety escalation rules:
        # - if two dimensions are very high, elevate to critical.
        # - if air-quality/environment alone is high, force at least HIGH alert
        #   for the student demonstration and operator dashboard.
        high_dims = [k for k, v in components.items() if k != "confidence" and v >= 0.75]
        if len(high_dims) >= 2:
            H = max(H, 0.86)
        if components.get("environment", 0.0) >= 0.55:
            H = max(H, 0.62)
        if components.get("visual", 0.0) >= 0.85:
            H = max(H, 0.66)
        if components.get("water", 0.0) >= 0.75 and components.get("terrain", 0.0) >= 0.55:
            H = max(H, 0.86)

        response = self._determine_response(H, components, wind_speed_kmh)
        return FusionResult(
            H=round(H, 4),
            components={k: round(v, 4) for k, v in components.items()},
            weights={k: round(v, 4) for k, v in self.weights.items()},
            response=response,
        )

    def _determine_response(self, H: float, components: Dict[str, float], wind_speed_kmh: float) -> FusionResponse:
        actions: List[str] = []
        reason_bits = []

        if H >= CRITICAL_ALERT:
            tier = "CRITICAL"
            actions += ["HALT_ROVER", "ALERT_CRITICAL", "LOG_LOCATION"]
            reason_bits.append("composite hazard at/above critical threshold")
            if wind_speed_kmh <= MAX_SAFE_WIND_KMH:
                actions.append("DEPLOY_DRONE")
            else:
                actions.append("DRONE_LOCKED_WIND_TOO_HIGH")
        elif H >= HIGH_ALERT:
            tier = "HIGH"
            actions += ["STOP_ALERT", "REQUEST_OPERATOR_CONFIRMATION", "LOG_LOCATION"]
            reason_bits.append("composite hazard at/above high threshold")
            if wind_speed_kmh <= MAX_SAFE_WIND_KMH:
                actions.append("DRONE_STANDBY")
        elif H >= LOW_ALERT:
            tier = "MEDIUM"
            actions += ["PAUSE_AND_SCAN", "LOG_LOCATION"]
            reason_bits.append("composite hazard above low alert threshold")
        else:
            tier = "LOW"
            actions += ["CONTINUE_SLOW", "LOG_TELEMETRY"]
            reason_bits.append("hazard below low threshold")

        if components.get("terrain", 0) >= 0.70:
            actions.append("LEG_STANDBY")
            reason_bits.append("terrain/entrapment risk high")
        if components.get("water", 0) >= 0.70:
            actions.append("WATER_FLOW_ALERT")
            reason_bits.append("water/drainage risk high")
        if components.get("acoustic", 0) >= 0.90:
            actions.append("HUMAN_DISTRESS_PRIORITY")
            reason_bits.append("acoustic distress priority")
        if components.get("soil", 0) >= 0.70:
            actions.append("SOIL_SAMPLE_SEQUENCE")

        # preserve order without duplicates
        seen = set()
        actions = [a for a in actions if not (a in seen or seen.add(a))]

        return FusionResponse(tier=tier, actions=actions, reason="; ".join(reason_bits))

    def add_feedback(self, components: Dict[str, float], operator_h: float):
        self.feedback.append((dict(components), self._clip(operator_h)))

    def update_weights_from_feedback(self, min_samples: int = 30) -> bool:
        """
        Simple dependency-free adaptive update.

        This is not a full Ridge regression solver, but it keeps the file working
        everywhere. It increases weights for components that correlate with the
        operator hazard label, then renormalises. Replace with sklearn Ridge when
        dependency availability is confirmed.
        """
        if len(self.feedback) < min_samples:
            return False
        accum = {k: 0.001 for k in self.weights}
        for comps, h in self.feedback[-min_samples:]:
            for k in accum:
                accum[k] += self._clip(comps.get(k, 0.0)) * h
        self.weights = self._normalise(accum)
        return True

    def _clip(self, x: float) -> float:
        return max(0.0, min(1.0, float(x)))
