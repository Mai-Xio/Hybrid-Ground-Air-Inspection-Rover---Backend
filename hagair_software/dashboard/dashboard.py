from __future__ import annotations

import html
import json
from pathlib import Path
from typing import List, Dict, Any

from hagair_software.config.settings import DATA_DIR


class DashboardRenderer:
    """
    Generates a static HTML dashboard after a run.
    Works without Flask/Streamlit so it is presentation-safe.
    """

    def __init__(self, out_path: Path | None = None):
        self.out_path = out_path or (DATA_DIR / "latest_dashboard.html")

    def render(self, records: List[Dict[str, Any]]) -> Path:
        self.out_path.parent.mkdir(parents=True, exist_ok=True)
        rows = []
        for r in records:
            f = r["fusion"]
            snap = r["snapshot"]
            rows.append(f"""
            <tr class="{html.escape(f['response']['tier'].lower())}">
              <td>{snap['step']}</td>
              <td>{html.escape(snap['scenario'])}</td>
              <td>{f['H']:.3f}</td>
              <td>{html.escape(f['response']['tier'])}</td>
              <td>{r['aqi']['aqi']} / {html.escape(r['aqi']['category'])}</td>
              <td>{html.escape(r['terrain']['terrain_class'])} ({r['terrain']['terrain_score']:.2f})</td>
              <td>{html.escape(r['soil']['soil_class'])} ({r['soil']['soil_score']:.2f})</td>
              <td>{html.escape(', '.join(f['response']['actions']))}</td>
            </tr>
            """)
        last = records[-1] if records else {}
        chart_points = [
            {"step": r["snapshot"]["step"], "H": r["fusion"]["H"], "E": r["aqi"]["environmental_score"], "T": r["terrain"]["terrain_score"]}
            for r in records
        ]
        html_text = f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>HAGAIR v3.0 Operator Dashboard</title>
<style>
body {{ font-family: Arial, sans-serif; background:#0d1117; color:#e6edf3; margin:0; padding:24px; }}
h1 {{ margin-top:0; }}
.cards {{ display:grid; grid-template-columns: repeat(4, minmax(160px,1fr)); gap:12px; margin-bottom:18px; }}
.card {{ background:#161b22; border:1px solid #30363d; border-radius:14px; padding:16px; }}
.big {{ font-size:30px; font-weight:bold; }}
.low {{ background:#102a1c; }}
.medium {{ background:#302a10; }}
.high {{ background:#301a10; }}
.critical {{ background:#3a1010; }}
table {{ width:100%; border-collapse:collapse; background:#161b22; border-radius:12px; overflow:hidden; }}
th, td {{ padding:10px; border-bottom:1px solid #30363d; vertical-align:top; }}
th {{ text-align:left; background:#21262d; }}
pre {{ white-space:pre-wrap; background:#010409; padding:12px; border-radius:12px; overflow:auto; }}
.badge {{ display:inline-block; padding:4px 8px; border-radius:999px; background:#30363d; }}
</style>
</head>
<body>
<h1>HAGAIR v3.0 Hybrid Inspection Rover Dashboard</h1>
<p class="badge">Static presentation dashboard generated from mission logs</p>
<div class="cards">
  <div class="card"><div>Last Hazard H</div><div class="big">{last.get('fusion',{}).get('H','-')}</div></div>
  <div class="card"><div>Last Tier</div><div class="big">{html.escape(str(last.get('fusion',{}).get('response',{}).get('tier','-')))}</div></div>
  <div class="card"><div>Last AQI</div><div class="big">{last.get('aqi',{}).get('aqi','-')}</div></div>
  <div class="card"><div>Drone State</div><div class="big">{html.escape(str(last.get('drone',{}).get('state','-')))}</div></div>
</div>
<h2>Mission Timeline</h2>
<table>
<thead><tr><th>Step</th><th>Scenario</th><th>H</th><th>Tier</th><th>AQI</th><th>Terrain</th><th>Soil</th><th>Actions</th></tr></thead>
<tbody>
{''.join(rows)}
</tbody>
</table>
<h2>Chart Data</h2>
<pre>{html.escape(json.dumps(chart_points, indent=2))}</pre>
<h2>Presentation Tip</h2>
<p>Show the rover on a stand, keep DEMO_SAFE_MODE enabled, then run flood / pollution / fire scenarios to show automatic halt, drone standby/deploy decisions, quadruped/leg standby, AQI, soil, water-flow and hazard fusion.</p>
</body>
</html>
"""
        self.out_path.write_text(html_text, encoding="utf-8")
        return self.out_path
