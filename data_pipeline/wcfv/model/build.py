"""
Build the final player projections.

This is where every strand comes together. For each player we:
  1. build their rate + minutes features,
  2. look up their three group-stage opponents,
  3. simulate each of those three matches (Monte Carlo) to get xP and a distribution,
  4. sum to a group-stage projection,
  5. divide by price to get value (points per unit cost).

Output: data/output/fantasy_values_2026.csv, one row per player.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from wcfv.paths import (MERGED_STATS_CSV, STRENGTH_CSV, FIXTURES_CSV, GROUPS_CSV,
                        PRICES_CSV, VALUES_CSV, ensure_dirs)
from wcfv.model.features import build_features
from wcfv.model.matchmodel import team_goals, attack_multiplier
from wcfv.model.simulate import simulate
from wcfv.model.pricing import synthetic_prices

SEED = 2026


def _load_prices(features: pd.DataFrame) -> tuple[pd.Series, str]:
    """Use official prices if a scraped file exists, otherwise synthetic ones."""
    if PRICES_CSV.exists():
        official = pd.read_csv(PRICES_CSV, encoding="utf-8")
        merged = features.merge(official[["name", "nation_code", "price"]],
                                on=["name", "nation_code"], how="left")
        if merged["price"].notna().mean() > 0.5:      # decent coverage -> trust it
            return merged["price"].fillna(synthetic_prices(features)), "official"
    return synthetic_prices(features), "synthetic"


def build_projections() -> pd.DataFrame:
    ensure_dirs()
    print("Building player projections...")
    merged = pd.read_csv(MERGED_STATS_CSV, encoding="utf-8")
    strength = pd.read_csv(STRENGTH_CSV, encoding="utf-8")
    fixtures = pd.read_csv(FIXTURES_CSV, encoding="utf-8")
    groups = pd.read_csv(GROUPS_CSV, encoding="utf-8")

    features = build_features(merged, strength)
    features["price"], price_source = _load_prices(features)
    print(f"  prices: {price_source}")

    rating = dict(zip(strength["nation_code"], strength["rating"]))
    group_by_code = dict(zip(groups["nation_code"], groups["group"]))
    opponents = fixtures.groupby("nation_code")["opponent_code"].apply(list).to_dict()

    rng = np.random.default_rng(SEED)
    records = []
    for _, feat in features.iterrows():
        code = feat["nation_code"]
        team_rating = feat["team_rating"]
        if pd.isna(team_rating):
            continue

        matches = []
        for opp in opponents.get(code, []):
            opp_rating = rating.get(opp)
            if opp_rating is None:
                continue
            mg = team_goals(team_rating, opp_rating)
            mult = attack_multiplier(team_rating, opp_rating)
            sim = simulate(feat, mult, mg.clean_sheet_prob, mg.goals_against, rng=rng)
            matches.append({
                "opponent": opp, "opponent_rating": round(float(opp_rating), 1),
                "xp": round(sim["xp"], 2), "floor": round(sim["floor"], 2),
                "ceiling": round(sim["ceiling"], 2), "p_haul": round(sim["p_haul"], 3),
            })

        if not matches:
            continue
        xps = [m["xp"] for m in matches]
        group_xp = float(np.sum(xps))
        price = float(feat["price"])

        records.append({
            "name": feat["name"], "nation": feat["nation"], "nation_code": code,
            "group": group_by_code.get(code), "position": feat["position"],
            "club": feat["club"], "age": feat["age"], "caps": feat["caps"],
            "team_rating": round(float(team_rating), 1),
            "price": round(price, 1),
            "xp_per_match": round(float(np.mean(xps)), 2),
            "group_xp": round(group_xp, 2),
            "value": round(group_xp / price, 3),
            "ceiling": round(float(np.mean([m["ceiling"] for m in matches])), 2),
            "floor": round(float(np.mean([m["floor"] for m in matches])), 2),
            "p_start": round(float(feat["p_start"]), 2),
            "goals90": round(float(feat["goals90"]), 3),
            "assists90": round(float(feat["assists90"]), 3),
            "sample_90s": feat["sample_90s"],
            "matches": matches,
        })

    df = pd.DataFrame(records).sort_values("group_xp", ascending=False).reset_index(drop=True)
    df["xp_rank"] = df["group_xp"].rank(ascending=False, method="min").astype(int)
    df["value_rank"] = df["value"].rank(ascending=False, method="min").astype(int)

    # Persist a flat CSV (drop the nested per-match column, which lives in the JSON).
    df.drop(columns=["matches"]).to_csv(VALUES_CSV, index=False)
    print(f"  built {len(df)} player projections -> {VALUES_CSV.name}")
    return df


if __name__ == "__main__":
    build_projections()
