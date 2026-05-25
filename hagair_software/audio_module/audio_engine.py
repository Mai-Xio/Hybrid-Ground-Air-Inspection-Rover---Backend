from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AudioResult:
    acoustic_score: float
    event: str
    confidence: float


class AudioAnalysisEngine:
    """
    Spectral/audio placeholder that works from simulated features.

    Later replacement can extract mel-spectrograms and use a real classifier.
    """

    def analyze(self, snap, scenario: str) -> AudioResult:
        score = 0.05
        event = "ambient"
        conf = 0.70

        if snap.audio_distress_probability > 0.5:
            score = 1.0
            event = "human_distress_possible"
            conf = snap.audio_distress_probability
        elif snap.audio_distress_probability > 0.12:
            score = 0.48
            event = "possible_distress_or_alert_sound"
            conf = snap.audio_distress_probability
        elif snap.audio_level_db > 70:
            score = 0.42
            event = "loud_environment"
            conf = 0.62

        if scenario == "flood" and snap.water_flow_lpm > 25:
            score = max(score, 0.50)
            event = "high_water_flow_audio_proxy"
            conf = max(conf, 0.66)

        return AudioResult(round(min(1.0, score), 4), event, round(conf, 4))
