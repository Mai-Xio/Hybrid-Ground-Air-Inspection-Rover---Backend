from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, Any, List

from hagair_software.config.settings import DATA_DIR, MODEL_DIR


class OnlineTrainingLoop:
    """
    Lightweight online buffer + validation-gated update placeholder.

    It is safe for demo because it does not silently replace mission behavior
    unless a minimum buffer size is met. The hazard fusion engine handles the
    actual dependency-free weight update.
    """

    def __init__(self, buffer_path: Path | None = None, version_path: Path | None = None):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        self.buffer_path = buffer_path or (DATA_DIR / "training_buffer.jsonl")
        self.version_path = version_path or (MODEL_DIR / "model_versions.json")
        self.samples_since_update = 0

    def add_sample(self, sample: Dict[str, Any], label: float, source: str = "auto") -> None:
        record = {
            "timestamp": time.time(),
            "source": source,
            "label": max(0.0, min(1.0, float(label))),
            "sample": sample,
        }
        with open(self.buffer_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        self.samples_since_update += 1

    def load_samples(self) -> List[Dict[str, Any]]:
        if not self.buffer_path.exists():
            return []
        out = []
        with open(self.buffer_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
        return out

    def maybe_update_fusion_weights(self, fusion_engine, min_samples: int = 30) -> bool:
        if self.samples_since_update < min_samples:
            return False
        samples = self.load_samples()[-min_samples:]
        for s in samples:
            fusion_engine.add_feedback(s["sample"].get("components", {}), s["label"])
        ok = fusion_engine.update_weights_from_feedback(min_samples=min_samples)
        if ok:
            self._log_model_version(fusion_engine)
            self.samples_since_update = 0
        return ok

    def _log_model_version(self, fusion_engine):
        history = []
        if self.version_path.exists():
            try:
                history = json.loads(self.version_path.read_text(encoding="utf-8"))
            except Exception:
                history = []
        history.append({
            "timestamp": time.time(),
            "profile": fusion_engine.profile,
            "weights": fusion_engine.weights,
            "note": "dependency-free adaptive fusion-weight update"
        })
        self.version_path.write_text(json.dumps(history, indent=2), encoding="utf-8")
