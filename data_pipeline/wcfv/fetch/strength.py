"""
Step 4: opponent strength.

The expected-points model needs to know how strong each nation is, so it can scale
a player's output up against weak opponents and down against strong ones. We express
strength as a single 0-100 `rating` per nation (loosely Elo-like); the match model
later converts a rating *difference* into expected goals.

Strategy:
  - Start from embedded pre-tournament rating priors for all 48 nations (this fixes
    the scale and guarantees every team gets a rating).
  - If an ODDS_API_KEY is available, pull live outright-winner odds from The Odds API,
    convert them to de-margined title probabilities, and blend those into the priors
    for the teams the market prices. Odds are only listed for a subset of contenders,
    so this improves the teams that matter most while leaving the rest on priors.
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd
import requests

from wcfv.paths import STRENGTH_CSV, ensure_dirs
from wcfv.process.countries import CountryResolver

ODDS_SPORT = "soccer_fifa_world_cup_winner"
ODDS_URL = (
    f"https://api.the-odds-api.com/v4/sports/{ODDS_SPORT}/odds"
    "?regions=uk&oddsFormat=decimal&markets=outrights"
)

ODDS_BLEND = 0.5   # weight on the odds signal vs the prior, for teams with odds

# Fallback pre-tournament strength priors (0-100). Approximate, bookmaker-informed
# relative strengths as of early 2026. These also define the rating scale that the
# odds signal is calibrated onto.
RATING_PRIORS = {
    "ARG": 91, "FRA": 91, "ESP": 90, "ENG": 89, "BRA": 89,
    "POR": 85, "NED": 84, "GER": 83, "BEL": 82,
    "CRO": 79, "URU": 79, "COL": 77, "MAR": 77, "USA": 75, "SUI": 75,
    "MEX": 74, "JPN": 74, "SEN": 74, "NOR": 74, "AUT": 72, "ECU": 72,
    "KOR": 71, "IRN": 71, "CIV": 71, "TUR": 71, "AUS": 70, "SWE": 70,
    "CZE": 70, "EGY": 70, "ALG": 70, "SCO": 68, "TUN": 68, "CAN": 68,
    "PAR": 67, "BIH": 67, "GHA": 66, "QAT": 66, "COD": 65, "RSA": 64,
    "CPV": 62, "KSA": 62, "PAN": 62, "UZB": 61, "JOR": 60, "IRQ": 58,
    "NZL": 58, "HAI": 55, "CUW": 53,
}


def _odds_implied_probs(api_key: str) -> dict[str, float] | None:
    """Fetch outright odds, aggregate across bookmakers, and return de-margined title
    probabilities keyed by FIFA code — or None on any failure."""
    try:
        resp = requests.get(f"{ODDS_URL}&apiKey={api_key}", timeout=25)
        resp.raise_for_status()
        events = resp.json()
        if not events:
            return None
        resolver = CountryResolver()

        # Average the raw implied probability (1/decimal-odds) across every bookmaker's
        # outright market, so we don't lean on a single book.
        raw: dict[str, list[float]] = {}
        for bm in events[0].get("bookmakers", []):
            for market in bm.get("markets", []):
                if market["key"] != "outrights":
                    continue
                for o in market["outcomes"]:
                    code = resolver.to_code(o["name"])
                    if code:
                        raw.setdefault(code, []).append(1.0 / float(o["price"]))
        if not raw:
            return None

        avg = {c: float(np.mean(v)) for c, v in raw.items()}
        total = sum(avg.values())                    # >1 because of bookmaker margin
        return {c: p / total for c, p in avg.items()}  # de-vigged probabilities
    except Exception as exc:
        print(f"  odds fetch failed ({exc}); using priors only")
        return None


def _blend_odds_into_priors(priors: dict, probs: dict) -> tuple[dict, set]:
    """Calibrate title probabilities onto the prior rating scale and blend them in,
    only for the teams the market prices."""
    codes = [c for c in probs if c in priors]
    if not codes:
        return dict(priors), set()

    # Title prob is hugely skewed toward favourites; a cube-root compresses it.
    scores = np.array([probs[c] ** (1 / 3) for c in codes])
    z = (scores - scores.mean()) / (scores.std() or 1.0)

    # Anchor the odds ratings to the mean/spread of these same teams' priors, so odds
    # and prior teams live on one comparable 0-100 scale.
    prior_vals = np.array([priors[c] for c in codes])
    odds_rating = prior_vals.mean() + z * prior_vals.std()

    blended = dict(priors)
    for c, r in zip(codes, odds_rating):
        blended[c] = ODDS_BLEND * float(r) + (1 - ODDS_BLEND) * priors[c]
    return blended, set(codes)


def fetch_team_strength(output_csv=STRENGTH_CSV) -> pd.DataFrame:
    ensure_dirs()
    print("Building team strength ratings...")
    api_key = os.environ.get("ODDS_API_KEY")

    ratings = dict(RATING_PRIORS)
    odds_codes: set = set()
    if api_key:
        probs = _odds_implied_probs(api_key)
        if probs:
            ratings, odds_codes = _blend_odds_into_priors(RATING_PRIORS, probs)
            print(f"  blended live odds for {len(odds_codes)} teams into priors")
    else:
        print("  no ODDS_API_KEY set — using embedded rating priors")

    df = pd.DataFrame(
        [{"nation_code": c, "rating": round(float(r), 1),
          "source": "odds+prior" if c in odds_codes else "prior"}
         for c, r in ratings.items()]
    ).sort_values("rating", ascending=False).reset_index(drop=True)

    df.to_csv(output_csv, index=False)
    n_odds = (df["source"] == "odds+prior").sum()
    print(f"  saved {len(df)} team ratings ({n_odds} odds-informed) -> {output_csv.name}")
    return df


if __name__ == "__main__":
    from wcfv.env import load_env
    load_env()
    fetch_team_strength()
