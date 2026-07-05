"""
Export the finished projections to JSON for the React front-end.

Writes data/output/players.json and copies it into frontend/public/data/ so the app
can load it as a static asset. The payload is a single object with a small `meta`
block and a `players` array (each player carries its nested per-match breakdown).
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from wcfv.paths import PLAYERS_JSON, FRONTEND_DATA_DIR, PRICES_CSV
from wcfv.model.build import build_projections


def _clean(obj):
    """Recursively convert numpy types to plain Python and NaN/inf to None so the
    result is valid JSON."""
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        return None if (math.isnan(obj) or math.isinf(obj)) else float(obj)
    if isinstance(obj, np.ndarray):
        return _clean(obj.tolist())
    if pd.isna(obj) if np.isscalar(obj) else False:
        return None
    return obj


def export_json() -> dict:
    df = build_projections()

    meta = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n_players": int(len(df)),
        "n_nations": int(df["nation_code"].nunique()),
        "price_source": "official" if PRICES_CSV.exists() else "synthetic",
        "scoring": "FIFA World Cup 2022 Fantasy ruleset",
        "horizon": "group stage (3 matches), fixture- and opponent-adjusted",
        "positions": ["GK", "DF", "MF", "FW"],
        "groups": sorted(df["group"].dropna().unique().tolist()),
    }
    payload = _clean({"meta": meta, "players": df.to_dict(orient="records")})

    PLAYERS_JSON.parent.mkdir(parents=True, exist_ok=True)
    PLAYERS_JSON.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    FRONTEND_DATA_DIR.mkdir(parents=True, exist_ok=True)
    (FRONTEND_DATA_DIR / "players.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    print(f"Exported {len(df)} players -> {PLAYERS_JSON.name} (+ frontend copy)")
    return payload


if __name__ == "__main__":
    export_json()
