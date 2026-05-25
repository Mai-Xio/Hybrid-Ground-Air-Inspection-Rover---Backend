from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from hagair_software.config.settings import SOIL_CLASSES


@dataclass
class SoilResult:
    soil_score: float
    soil_class: str
    probabilities: Dict[str, float]
    flags: Dict[str, bool]


class SoilAnalysisEngine:
    """
    Guaranteed-working rule classifier for soil/pH/EC/moisture.

    It behaves like a simple transparent classifier; later you can replace this
    class internally with a RandomForest model while keeping the same API.
    """

    def analyze(self, snap) -> SoilResult:
        flags = {
            "ACIDIC": snap.soil_ph < 5.5,
            "ALKALINE": snap.soil_ph > 8.5,
            "SALINE": snap.soil_ec_ms_cm > 4.0,
            "WATERLOGGED": snap.soil_moisture_pct > 65,
            "LOW_NUTRIENT": snap.soil_n_mgkg < 25 or snap.soil_p_mgkg < 8 or snap.soil_k_mgkg < 80,
            "HIGH_EC": snap.soil_ec_ms_cm > 8.0,
        }

        scores = {name: 0.02 for name in SOIL_CLASSES}

        if flags["ACIDIC"]:
            scores["Acidic Contamination"] += min(0.65, (5.5 - snap.soil_ph) / 2.0)
        if flags["SALINE"] or flags["HIGH_EC"]:
            scores["Saline Intrusion"] += min(0.75, snap.soil_ec_ms_cm / 12.0)
        if flags["WATERLOGGED"] and snap.liquid_ph > 8.5:
            scores["Agricultural Runoff"] += 0.45
        if snap.voc_index > 250 or snap.h2s_ppm > 10 or snap.methane_lel_pct > 10:
            scores["Industrial Discharge"] += 0.55
        if snap.soil_ec_ms_cm > 7.5 and snap.soil_ph < 5.8 and snap.voc_index > 220:
            scores["Heavy Metal Indicator"] += 0.62

        if not any(flags.values()):
            scores["Uncontaminated"] += 0.72

        total = sum(scores.values())
        probs = {k: round(v / total, 4) for k, v in scores.items()}
        soil_class = max(probs, key=probs.get)
        hazard = 1.0 - probs.get("Uncontaminated", 0.0)

        # Make unsafe pH and high EC visibly contribute.
        if snap.soil_ph < 5.5 or snap.soil_ph > 8.5:
            hazard = max(hazard, 0.55)
        if snap.soil_ec_ms_cm > 4:
            hazard = max(hazard, min(1.0, snap.soil_ec_ms_cm / 10.0))

        return SoilResult(
            soil_score=round(min(1.0, hazard), 4),
            soil_class=soil_class,
            probabilities=probs,
            flags=flags,
        )
