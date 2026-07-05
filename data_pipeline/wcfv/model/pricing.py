"""
Synthetic player pricing.

If the official fantasy price feed can't be scraped, we build a stand-in price so the
value metric (points per unit cost) still works. We deliberately price players the way
a real fantasy game would — off observable output, playing time, team quality and
reputation — NOT off our own expected-points number. That keeps the value metric
meaningful: it rewards players whose projected points beat what their profile alone
would imply (because of favourable fixtures, position scoring, or minutes).

Prices land on a familiar fantasy scale (~4.0 to ~13.5) in 0.5 steps.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

POSITION_BASE = {"GK": 4.5, "DF": 4.5, "MF": 5.0, "FW": 5.5}
PRICE_MIN, PRICE_MAX = 4.0, 13.5


def synthetic_prices(features: pd.DataFrame) -> pd.Series:
    """Return a price (indexed like `features`) for every player."""
    base = features["position"].map(POSITION_BASE).fillna(5.0)

    # Attacking output is the dominant driver, exactly as in real fantasy pricing.
    output = 6.0 * (features["goals90"].fillna(0) + 0.7 * features["assists90"].fillna(0))
    # Nailed-on starters, players on strong teams, and capped internationals cost more.
    minutes_premium = 1.5 * features["p_start"].fillna(0)
    team_premium = 0.03 * (features["team_rating"].fillna(70) - 70)
    reputation = 0.010 * features["caps"].fillna(0).clip(upper=120)

    raw = base + output + minutes_premium + team_premium + reputation
    rounded = (raw * 2).round() / 2                     # nearest 0.5
    return rounded.clip(PRICE_MIN, PRICE_MAX)
