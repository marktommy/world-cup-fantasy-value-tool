"""
The fantasy scoring rules, and a function to score a single match outcome.

These numbers follow the FIFA World Cup 2022 Fantasy scoring system. They are kept
in one dataclass so the whole model is driven by a single, auditable source of
truth — when the official 2026 rules are published, only this file changes.

Note: the fetched FBref stat types do not include goalkeeping saves, so save and
penalty-save points are not modelled. GK/DEF scoring therefore rests on appearances,
clean sheets, goals conceded and the occasional goal/assist.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ScoringRules:
    appearance_1_59: int = 1          # played 1-59 minutes
    appearance_60_plus: int = 2       # played 60+ minutes

    # Points per goal, by position.
    goal: dict = field(default_factory=lambda: {"GK": 6, "DF": 6, "MF": 5, "FW": 4})
    assist: int = 3

    # Clean-sheet points (only if the player played 60+ minutes), by position.
    clean_sheet: dict = field(default_factory=lambda: {"GK": 4, "DF": 4, "MF": 1, "FW": 0})

    # Penalty (per 2 goals conceded) for GK/DF who played 60+ minutes.
    goals_conceded_per_2: int = -1

    yellow: int = -1
    red: int = -3
    own_goal: int = -2
    penalty_miss: int = -2
    penalty_won: int = 1              # winning a penalty for your team


DEFAULT_RULES = ScoringRules()


def score_outcome(outcome: dict, position: str, rules: ScoringRules = DEFAULT_RULES) -> float:
    """
    Score one realised match for one player.

    `outcome` is a dict of realised event counts for a single game, e.g.
    {"minutes": 90, "goals": 1, "assists": 0, "clean_sheet": True,
     "conceded": 1, "yellow": 0, "red": 0, "own_goals": 0,
     "pens_missed": 0, "pens_won": 0}. Used both by the Monte-Carlo simulator
    (one call per simulated game) and for quick analytic checks.
    """
    minutes = outcome.get("minutes", 0)
    if minutes <= 0:
        return 0.0  # did not play -> no points at all

    pts = rules.appearance_60_plus if minutes >= 60 else rules.appearance_1_59
    pts += outcome.get("goals", 0) * rules.goal.get(position, 4)
    pts += outcome.get("assists", 0) * rules.assist

    played_60 = minutes >= 60
    if played_60 and outcome.get("clean_sheet"):
        pts += rules.clean_sheet.get(position, 0)

    # Goals conceded only bite GK/DF who were on for the defensive shift.
    if position in ("GK", "DF") and played_60:
        pts += (outcome.get("conceded", 0) // 2) * rules.goals_conceded_per_2

    pts += outcome.get("yellow", 0) * rules.yellow
    pts += outcome.get("red", 0) * rules.red
    pts += outcome.get("own_goals", 0) * rules.own_goal
    pts += outcome.get("pens_missed", 0) * rules.penalty_miss
    pts += outcome.get("pens_won", 0) * rules.penalty_won
    return float(pts)
