"""
Monte-Carlo match simulation.

Rather than reduce a player's game to a single expected number, we simulate the game
thousands of times and record the fantasy points each time. This gives us not just a
mean (the expected points, xP) but a whole distribution — a floor (10th percentile),
a ceiling (90th percentile) and a standard deviation. Those matter in fantasy: a
high-ceiling player is a good captain pick even if their mean is modest.

Everything is vectorised with numpy: each call simulates all N games for one player-
vs-opponent at once, so scoring the whole tournament stays fast.
"""

from __future__ import annotations

import numpy as np

from wcfv.model.scoring import ScoringRules, DEFAULT_RULES

N_SIMS = 4000
MIN_IF_BENCH = 32          # assumed minutes for a substitute appearance


def simulate(feat, attack_mult: float, clean_sheet_prob: float, goals_against: float,
             n: int = N_SIMS, rules: ScoringRules = DEFAULT_RULES, rng=None) -> dict:
    """
    Simulate `n` games for one player against one opponent and summarise the points.

    Parameters:
      feat              : a row (dict-like) from build_features — the player's rates
                          and minutes probabilities.
      attack_mult       : opponent scaling for this player's team output (1.0 = avg).
      clean_sheet_prob  : P(team keeps a clean sheet) in this fixture.
      goals_against     : expected goals the team concedes (drives conceded penalties).
    """
    rng = rng or np.random.default_rng()
    pos = feat["position"]

    # --- Minutes: draw a bucket (didn't play / 1-59 / 60+) for every sim ----
    p_dnp = 1.0 - feat["p_play"]
    p_short = feat["p_play"] - feat["p_60"]
    u = rng.random(n)
    minutes = np.where(u < p_dnp, 0.0,
                       np.where(u < p_dnp + p_short, MIN_IF_BENCH, feat["min_if_start"]))
    played = minutes > 0
    played60 = minutes >= 60
    share = minutes / 90.0                       # fraction of a full game played

    # --- Attacking returns: Poisson counts scaled by minutes and opponent ---
    goals = rng.poisson(np.maximum(feat["goals90"] * share * attack_mult, 0))
    assists = rng.poisson(np.maximum(feat["assists90"] * share * attack_mult, 0))

    # --- Defensive / disciplinary events ------------------------------------
    clean_sheet = played60 & (rng.random(n) < clean_sheet_prob)
    conceded = np.where(played60, rng.poisson(goals_against, n), 0)
    yellow = rng.random(n) < np.minimum(feat["yellow90"] * share, 0.9)
    red = rng.random(n) < np.minimum(feat["red90"] * share, 0.5)
    own_goals = rng.poisson(np.maximum(feat["og90"] * share, 0))
    pens_won = rng.poisson(np.maximum(feat["penwon90"] * share, 0))
    pens_missed = rng.poisson(np.maximum(feat["penmiss90"] * share, 0))

    # --- Score every simulated game (vectorised version of score_outcome) ---
    pts = np.zeros(n)
    pts += np.where(played60, rules.appearance_60_plus,
                    np.where(played, rules.appearance_1_59, 0))
    pts += goals * rules.goal.get(pos, 4)
    pts += assists * rules.assist
    pts += np.where(clean_sheet, rules.clean_sheet.get(pos, 0), 0)
    if pos in ("GK", "DF"):
        pts += np.where(played60, (conceded // 2) * rules.goals_conceded_per_2, 0)
    pts += yellow * rules.yellow
    pts += red * rules.red
    pts += own_goals * rules.own_goal
    pts += pens_missed * rules.penalty_miss
    pts += pens_won * rules.penalty_won

    return {
        "xp": float(pts.mean()),
        "floor": float(np.percentile(pts, 10)),
        "ceiling": float(np.percentile(pts, 90)),
        "std": float(pts.std()),
        "p_haul": float((pts >= 9).mean()),      # chance of a big (9+) return
    }
