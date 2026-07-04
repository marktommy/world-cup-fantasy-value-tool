"""
Country name / code reconciliation.

The three data sources each identify a nation differently:
  - squads_2026.csv  -> FIFA 3-letter code   (e.g. "USA", "IRN")
  - FBref club stats -> FBref 3-letter code   (identical to FIFA for our nations)
  - FBref intl stats -> full country name     (e.g. "United States", "IR Iran")

`CountryResolver` loads config/countries.csv and turns ANY of those spellings into
one canonical FIFA code, so every table can be joined on the same key.
"""

from __future__ import annotations

import pandas as pd

from wcfv.paths import COUNTRIES_CSV


def _norm(value: str) -> str:
    """Lower-case and strip so 'United States ' and 'united states' compare equal."""
    return str(value).strip().lower()


class CountryResolver:
    def __init__(self, countries_csv=COUNTRIES_CSV):
        df = pd.read_csv(countries_csv, encoding="utf-8")

        # Map every known spelling -> FIFA code. We register, for each nation:
        #   the FIFA code itself, the FBref code, the canonical name, and every alias.
        self._lookup: dict[str, str] = {}
        self.codes: set[str] = set(df["fifa_code"])
        self.name_by_code: dict[str, str] = dict(zip(df["fifa_code"], df["name"]))

        for _, row in df.iterrows():
            code = row["fifa_code"]
            self._register(row["fifa_code"], code)
            self._register(row["fbref_code"], code)
            self._register(row["name"], code)
            # `aliases` is a pipe-separated string, possibly empty/NaN.
            if isinstance(row["aliases"], str):
                for alias in row["aliases"].split("|"):
                    if alias.strip():
                        self._register(alias, code)

    def _register(self, spelling: str, code: str) -> None:
        self._lookup[_norm(spelling)] = code

    def to_code(self, value) -> str | None:
        """Resolve a name/code/alias to a FIFA code, or None if unknown."""
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        return self._lookup.get(_norm(value))

    def name(self, code: str) -> str:
        """Canonical display name for a FIFA code."""
        return self.name_by_code.get(code, code)
