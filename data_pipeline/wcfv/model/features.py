"""
Feature building: turn raw matched stats into the per-player parameters the
simulator needs.

Three ideas do the heavy lifting here:

1. Recency-weighted blending. A player's club form comes from two seasons and their
   international form from two tournaments; more recent data is weighted higher, and
   the two competitions are pooled (World Cup minutes up-weighted, since they are
   played at the tournament's level).

2. Empirical-Bayes shrinkage. A raw per-90 rate from a small sample is unreliable —
   3 goals in 200 minutes is not a 1.35-per-90 striker. We shrink every rate toward
   a position baseline (learned from the data itself), by an amount that depends on
   sample size: rate = (events + K * baseline) / (nineties + K). Small samples pull
   hard toward the baseline; large samples barely move.

3. A minutes model. Points require pitch time, so we estimate the probability a
   player starts / appears / lasts 60+ minutes, blending club playing time with
   international pedigree (caps).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Recency weights for blending the two club seasons and two tournaments.
CLUB_WEIGHTS = {"c2425": 0.6, "c2526": 1.0}
INTL_WEIGHTS = {"i2018": 0.5, "i2022": 1.0}
INTL_RELEVANCE = 1.5   # up-weight World Cup minutes relative to club minutes

# Shrinkage strength (in "equivalent 90s of prior"). Higher = trust the baseline more.
SHRINK_K = 8.0

# Fixed low-rate priors (per 90) for rare events we don't learn a baseline for.
RARE_PRIORS = {"yellow": 0.16, "red": 0.006, "own_goals": 0.004,
               "pens_won": 0.02, "pen_miss": 0.004}
RARE_K = 6.0

# Counting stats we blend, mapped from the merged-column semantic name.
COUNT_COLS = ["minutes", "nineties", "matches", "starts", "goals", "assists",
              "shots", "shots_on_target", "yellows", "reds", "own_goals",
              "pens_won", "pens_att", "pens_scored"]


def _weighted_sum(row, sources, weights, stat):
    """Recency-weighted sum of one stat across a set of source tables."""
    total = 0.0
    for tag in sources:
        val = row.get(f"{tag}_{stat}")
        if pd.notna(val):
            total += weights[tag] * float(val)
    return total


def _pos_baselines(pooled: pd.DataFrame) -> dict:
    """Learn minutes-weighted per-90 baselines for goals & assists, per position,
    from players with a meaningful sample. This is the empirical prior."""
    baselines = {}
    solid = pooled[pooled["nineties"] >= 5]
    for pos in ["GK", "DF", "MF", "FW"]:
        grp = solid[solid["position"] == pos]
        n90 = grp["nineties"].sum()
        baselines[pos] = {
            "goals": grp["goals"].sum() / n90 if n90 > 0 else 0.05,
            "assists": grp["assists"].sum() / n90 if n90 > 0 else 0.05,
        }
    return baselines


def _shrink(events, nineties, baseline, k=SHRINK_K):
    """Empirical-Bayes shrinkage of a per-90 rate toward a baseline."""
    return (events + k * baseline) / (nineties + k)


def _age_from_dob(dob: str) -> float:
    try:
        return 2026 - int(str(dob).split("/")[-1])
    except Exception:
        return np.nan


# Sources to draw a clean display name from, best (highest match score) first.
_NAME_SOURCES = ["c2526", "c2425", "i2022", "i2018"]


def _clean_squad_name(raw: str) -> str:
    """Fallback for unmatched players: turn the garbled ALL-CAPS PDF name
    ('MASTIL Melvin Melvin Feycal MASTIL MASTIL') into 'Melvin Feycal Mastil' by
    de-duplicating tokens and moving the surname (the caps token) to the end."""
    seen, given, surnames = set(), [], []
    for tok in str(raw).split():
        key = tok.lower()
        if key in seen:
            continue
        seen.add(key)
        (surnames if tok.isupper() else given).append(tok)
    return " ".join(given + [s.title() for s in surnames]).strip() or str(raw)


def _display_name(ident) -> str:
    """Prefer the clean FBref name from whichever source matched most confidently."""
    best_name, best_score = None, -1.0
    for tag in _NAME_SOURCES:
        score, name = ident.get(f"{tag}_match_score"), ident.get(f"{tag}_matched_player")
        if pd.notna(score) and float(score) > best_score and isinstance(name, str):
            best_score, best_name = float(score), name
    return best_name if best_name else _clean_squad_name(ident["name"])


def build_features(merged: pd.DataFrame, strength: pd.DataFrame) -> pd.DataFrame:
    """Build the per-player parameter table used by the simulator."""
    rating_by_code = dict(zip(strength["nation_code"], strength["rating"]))

    # --- Step 1: pool blended counts for every player -------------------
    pooled_rows = []
    for _, row in merged.iterrows():
        rec = {"position": row["position"]}
        for stat in COUNT_COLS:
            club = _weighted_sum(row, CLUB_WEIGHTS, CLUB_WEIGHTS, stat)
            intl = _weighted_sum(row, INTL_WEIGHTS, INTL_WEIGHTS, stat) * INTL_RELEVANCE
            rec[stat] = club + intl
        pooled_rows.append(rec)
    pooled = pd.DataFrame(pooled_rows)

    baselines = _pos_baselines(pooled)

    # --- Step 2: per-player rates (shrunk) + minutes model --------------
    out = []
    for (_, ident), (_, p) in zip(merged.iterrows(), pooled.iterrows()):
        pos = ident["position"]
        n90 = p["nineties"]
        base = baselines.get(pos, {"goals": 0.05, "assists": 0.05})

        goals90 = _shrink(p["goals"], n90, base["goals"])
        assists90 = _shrink(p["assists"], n90, base["assists"])
        yellow90 = _shrink(p["yellows"], n90, RARE_PRIORS["yellow"], RARE_K)
        red90 = _shrink(p["reds"], n90, RARE_PRIORS["red"], RARE_K)
        og90 = _shrink(p["own_goals"], n90, RARE_PRIORS["own_goals"], RARE_K)
        penwon90 = _shrink(p["pens_won"], n90, RARE_PRIORS["pens_won"], RARE_K)
        pen_miss = max(p["pens_att"] - p["pens_scored"], 0)
        penmiss90 = _shrink(pen_miss, n90, RARE_PRIORS["pen_miss"], RARE_K)

        # Minutes model. Club start-share and minutes-per-match describe the player's
        # role; caps capture international standing for those with little/no club data.
        matches = p["matches"]
        club_start_share = p["starts"] / matches if matches > 0 else np.nan
        min_per_match = p["minutes"] / matches if matches > 0 else np.nan
        caps_factor = min(float(ident.get("caps", 0) or 0) / 40.0, 1.0)

        if pd.notna(club_start_share):
            p_start = 0.65 * club_start_share + 0.35 * caps_factor
        else:                                   # no club data: lean on caps
            p_start = 0.15 + 0.6 * caps_factor
        p_start = float(np.clip(p_start, 0.02, 0.98))

        min_if_start = float(np.clip(min_per_match if pd.notna(min_per_match) else 75, 55, 90))
        p_bench = (1 - p_start) * 0.35          # non-starters who still feature
        p_play = p_start + p_bench
        p_60 = p_start * 0.85 + p_bench * 0.10  # chance of lasting the 60-min mark

        out.append({
            "name": _display_name(ident),
            "name_raw": ident["name"],
            "nation_code": ident["nation_code"],
            "nation": ident["nation"],
            "position": pos,
            "club": ident.get("club"),
            "age": _age_from_dob(ident.get("dob")),
            "caps": ident.get("caps"),
            "team_rating": rating_by_code.get(ident["nation_code"], np.nan),
            "sample_90s": round(float(n90), 1),
            "goals90": goals90, "assists90": assists90, "yellow90": yellow90,
            "red90": red90, "og90": og90, "penwon90": penwon90, "penmiss90": penmiss90,
            "shots90": p["shots"] / n90 if n90 > 0 else 0.0,
            "p_start": p_start, "p_play": float(np.clip(p_play, 0.02, 0.99)),
            "p_60": float(np.clip(p_60, 0.01, 0.95)),
            "min_if_start": min_if_start,
        })

    return pd.DataFrame(out)
