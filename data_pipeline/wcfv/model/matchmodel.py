"""
The team-level match model.

Turns two nation strength ratings into expected goals for and against, using a
standard Poisson/Elo-style mapping: a team's scoring rate rises exponentially with
its rating advantage over the opponent. Calibrated so an even match is ~1.35 goals
per side (about the international average) and a large favourite scores ~2.5 while
conceding ~0.7.

These team expected-goals values do two jobs later:
  - clean-sheet probability = P(opponent scores 0) = exp(-goals_against)
  - a per-opponent multiplier that scales each player's individual output up or down
    relative to an average opponent.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

BASE_GOALS = 1.35     # expected goals per team in an evenly-matched game
BETA = 0.25           # how strongly a rating edge boosts scoring
SCALE = 10.0          # rating points per "unit" of edge
AVG_RATING = 72.0     # a typical WC team, used as the "average opponent" baseline

GOALS_FLOOR, GOALS_CEIL = 0.15, 4.5


@dataclass(frozen=True)
class MatchGoals:
    goals_for: float
    goals_against: float

    @property
    def clean_sheet_prob(self) -> float:
        """P(opponent scores zero) under a Poisson goals model."""
        return math.exp(-self.goals_against)


def _clamp(x: float) -> float:
    return max(GOALS_FLOOR, min(GOALS_CEIL, x))


def team_goals(rating_for: float, rating_against: float) -> MatchGoals:
    """Expected goals for/against given the two teams' ratings."""
    edge = BETA * (rating_for - rating_against) / SCALE
    return MatchGoals(
        goals_for=_clamp(BASE_GOALS * math.exp(edge)),
        goals_against=_clamp(BASE_GOALS * math.exp(-edge)),
    )


def attack_multiplier(rating_for: float, rating_against: float) -> float:
    """
    How much this fixture inflates/deflates the team's attacking output relative to
    playing an average opponent. A player's individual expected goals/assists get
    multiplied by this, keeping the player's *share* of team output constant while
    the team total flexes with the opponent.
    """
    vs_opp = team_goals(rating_for, rating_against).goals_for
    vs_avg = team_goals(rating_for, AVG_RATING).goals_for
    return vs_opp / vs_avg
