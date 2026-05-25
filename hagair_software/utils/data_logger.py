from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict

from hagair_software.config.settings import LOG_DIR


class DataLogger:
    def __init__(self, mission_name: str = "demo"):
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in mission_name)
        self.path = LOG_DIR / f"{stamp}_{safe_name}.jsonl"

    def log(self, record: Dict[str, Any]) -> None:
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
