from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from hagair_software.config.settings import TERRAIN_RISK


@dataclass
class TerrainResult:
    terrain_class: str
    terrain_score: float
    entrapment_risk: float
    obstacle_risk: float


class TerrainAnalysisEngine:
    """
    Terrain analysis demo.

    If an OpenCV frame is available, you can add color/texture analysis here.
    In the guaranteed demo path, terrain_hint and numeric sensors drive the
    result so the software works on any laptop.
    """

    def analyze(self, frame: Optional[object], snap) -> TerrainResult:
        terrain = snap.terrain_hint if snap.terrain_hint in TERRAIN_RISK else "unknown"
        base = TERRAIN_RISK.get(terrain, TERRAIN_RISK["unknown"])

        slope_risk = min(1.0, max(0.0, snap.slope_deg / 35.0))
        moisture_risk = min(1.0, max(0.0, (snap.soil_moisture_pct - 30.0) / 55.0))
        obstacle_risk = 0.0
        if snap.obstacle_cm < 20:
            obstacle_risk = 1.0
        elif snap.obstacle_cm < 50:
            obstacle_risk = 0.75
        elif snap.obstacle_cm < 90:
            obstacle_risk = 0.35

        entrapment = min(1.0, 0.45 * moisture_risk + 0.35 * slope_risk + 0.20 * obstacle_risk)
        T = min(1.0, 0.55 * base + 0.25 * entrapment + 0.20 * obstacle_risk)

        return TerrainResult(
            terrain_class=terrain,
            terrain_score=round(T, 4),
            entrapment_risk=round(entrapment, 4),
            obstacle_risk=round(obstacle_risk, 4),
        )
