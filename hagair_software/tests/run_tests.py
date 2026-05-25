from __future__ import annotations

import sys
from pathlib import Path

# Allow running from hagair_software/tests without installing package.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hagair_software.main_pipeline import run_pipeline


def assert_true(name, condition, details=""):
    if condition:
        print(f"PASS: {name}")
    else:
        print(f"FAIL: {name} {details}")
        raise AssertionError(name)


def test_normal_low():
    r = run_pipeline(steps=3, scenario="normal", profile="general", dashboard=False)
    assert_true("normal produces records", len(r) == 3)
    assert_true("normal H below high", max(x["fusion"]["H"] for x in r) < 0.60)


def test_pollution_alert():
    r = run_pipeline(steps=3, scenario="pollution", profile="air_quality", dashboard=False)
    assert_true("pollution AQI high", max(x["aqi"]["aqi"] for x in r) >= 200)
    assert_true("pollution high or critical", max(x["fusion"]["H"] for x in r) >= 0.55)


def test_flood_critical():
    r = run_pipeline(steps=3, scenario="flood", profile="drainage", dashboard=False)
    assert_true("flood water score high", max(x["fusion"]["components"]["water"] for x in r) >= 0.70)
    assert_true("flood gets halt or alert", any("HALT_ROVER" in x["fusion"]["response"]["actions"] or "STOP_ALERT" in x["fusion"]["response"]["actions"] for x in r))


def test_fire_visual():
    r = run_pipeline(steps=3, scenario="fire", profile="night_ir", dashboard=False)
    assert_true("fire visual high", max(x["visual"]["visual_score"] for x in r) >= 0.80)
    assert_true("fire high or critical", max(x["fusion"]["H"] for x in r) >= 0.60)


def run_all():
    test_normal_low()
    test_pollution_alert()
    test_flood_critical()
    test_fire_visual()
    print("\nAll HAGAIR tests passed.")


if __name__ == "__main__":
    run_all()
