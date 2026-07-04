"""
Step 5 (data side): the 2026 group draw and each nation's fixtures.

The 2026 tournament is 48 teams in 12 groups of four. Within a group everyone plays
everyone (a round-robin), so a nation's three group-stage opponents are simply the
other three teams in its group — we don't need a separate fixtures feed to know who
plays whom.

We pull the draw from the community worldcup26.ir endpoint, and fall back to an
embedded copy of the draw if the network is unavailable, so the pipeline stays
reproducible offline.
"""

from __future__ import annotations

from itertools import combinations

import pandas as pd
import requests

from wcfv.paths import GROUPS_CSV, FIXTURES_CSV, ensure_dirs

TEAMS_URL = "https://worldcup26.ir/get/teams"

# Offline fallback: the 12-group draw (FIFA codes). Used if the live fetch fails.
FALLBACK_GROUPS = {
    "A": ["CZE", "KOR", "MEX", "RSA"], "B": ["BIH", "CAN", "QAT", "SUI"],
    "C": ["BRA", "HAI", "MAR", "SCO"], "D": ["AUS", "PAR", "TUR", "USA"],
    "E": ["CIV", "CUW", "ECU", "GER"], "F": ["JPN", "NED", "SWE", "TUN"],
    "G": ["BEL", "EGY", "IRN", "NZL"], "H": ["CPV", "ESP", "KSA", "URU"],
    "I": ["FRA", "IRQ", "NOR", "SEN"], "J": ["ALG", "ARG", "AUT", "JOR"],
    "K": ["COD", "COL", "POR", "UZB"], "L": ["CRO", "ENG", "GHA", "PAN"],
}


def _fetch_groups() -> dict[str, list[str]]:
    """Return {group_letter: [fifa_code, ...]}, live if possible, else the fallback."""
    try:
        resp = requests.get(TEAMS_URL, timeout=15)
        resp.raise_for_status()
        payload = resp.json()
        teams = payload if isinstance(payload, list) else payload.get("teams", [])
        groups: dict[str, list[str]] = {}
        for team in teams:
            code, grp = team.get("fifa_code"), str(team.get("groups", "")).strip()
            if code and grp:
                groups.setdefault(grp, []).append(code)
        if sum(len(v) for v in groups.values()) == 48:
            print("  fetched live 2026 group draw")
            return groups
        print("  live draw looked incomplete; using embedded fallback")
    except Exception as exc:
        print(f"  live draw fetch failed ({exc}); using embedded fallback")
    return {g: list(codes) for g, codes in FALLBACK_GROUPS.items()}


def fetch_groups_and_fixtures():
    """Write groups_2026.csv (nation -> group) and fixtures_2026.csv (directed
    opponent pairs: one row per team per group opponent)."""
    ensure_dirs()
    print("Building 2026 groups and fixtures...")
    groups = _fetch_groups()

    group_rows, fixture_rows = [], []
    for letter in sorted(groups):
        members = groups[letter]
        for code in members:
            group_rows.append({"nation_code": code, "group": letter})
        # Round-robin: every unordered pair plays once; record both directions so
        # each team can look up its own three opponents easily.
        for a, b in combinations(members, 2):
            fixture_rows.append({"nation_code": a, "opponent_code": b, "group": letter})
            fixture_rows.append({"nation_code": b, "opponent_code": a, "group": letter})

    pd.DataFrame(group_rows).to_csv(GROUPS_CSV, index=False)
    pd.DataFrame(fixture_rows).to_csv(FIXTURES_CSV, index=False)
    print(f"  saved {len(group_rows)} teams, {len(fixture_rows)} fixtures "
          f"-> {GROUPS_CSV.name}, {FIXTURES_CSV.name}")
    return pd.DataFrame(group_rows), pd.DataFrame(fixture_rows)


if __name__ == "__main__":
    fetch_groups_and_fixtures()
