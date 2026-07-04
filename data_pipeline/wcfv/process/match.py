"""
Stage 2 of processing: matching.

We attach FBref stats to every player in the official squad list. This is fuzzy,
not exact, because the two sources spell names differently:
  - the FIFA squad PDF gives garbled, duplicated ALL-CAPS names
    ("MASTIL Melvin Melvin Feycal MASTIL MASTIL")
  - FBref gives clean names ("Melvin Mastil"), sometimes with accents.

Strategy:
  1. Normalise both names (strip accents, lower-case, drop punctuation).
  2. Block by nation — only compare a squad player against FBref players of the
     same country. This shrinks each comparison to ~26 candidates and kills almost
     all false positives.
  3. Fuzzy-match with rapidfuzz `token_set_ratio`, which ignores duplicate tokens
     and word order — perfect for the repeated-surname mess above.

Club and international stats are kept as SEPARATE, source-tagged columns (never
pre-averaged) so the model can weight them itself. Low-confidence matches are
written to a review file so they can be inspected by hand.
"""

from __future__ import annotations

import unicodedata

import numpy as np
import pandas as pd
from rapidfuzz import process, fuzz

from wcfv.paths import PROCESSED_DIR, SQUADS_CSV, MERGED_STATS_CSV
from wcfv.process.countries import CountryResolver

# Fuzzy score (0-100) a match must beat to be accepted, and the level below which
# we flag it for human review.
MATCH_THRESHOLD = 85
REVIEW_THRESHOLD = 90

# The raw FBref columns we carry through, mapped to clean semantic names. These are
# everything the expected-points model needs. (Goalkeeping/saves are not available
# in the fetched stat types, so GK scoring later relies on appearances + clean
# sheets only.)
CURATED = {
    "playing_time_mp": "matches",
    "playing_time_starts": "starts",
    "playing_time_min": "minutes",
    "playing_time_90s": "nineties",
    "performance_gls": "goals",
    "performance_ast": "assists",
    "performance_pk": "pens_scored",
    "performance_pkatt": "pens_att",
    "performance_crdy": "yellows",
    "performance_crdr": "reds",
    "standard_sh": "shots",
    "standard_sot": "shots_on_target",
    "performance_fls": "fouls",
    "performance_int": "interceptions",
    "performance_tklw": "tackles_won",
    "performance_og": "own_goals",
    "performance_pkwon": "pens_won",
    "performance_pkcon": "pens_conceded",
}

# The four stat tables, each with a short column tag and which column holds the
# nation. Club files store the nation as a code; international files as a name in
# the `team` column (the country the player represented at that World Cup).
SOURCES = [
    ("c2425", "club_2024-25_consolidated.csv", "nation"),
    ("c2526", "club_2025-26_consolidated.csv", "nation"),
    ("i2018", "international_2018_consolidated.csv", "team"),
    ("i2022", "international_2022_consolidated.csv", "team"),
]


def normalize_name(name) -> str:
    """
    Turn a name into a plain-ASCII, lower-case, punctuation-free string so that
    'BELAÏD' and 'Belaid' compare as equal.

    unicodedata.normalize('NFKD', ...) splits accented letters into a base letter
    plus a combining mark; encoding to ASCII and ignoring errors then drops the
    marks. Everything that is not a letter or digit becomes a space, and repeated
    spaces are collapsed.
    """
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return ""
    text = unicodedata.normalize("NFKD", str(name))
    text = text.encode("ascii", "ignore").decode("ascii")
    text = "".join(ch if ch.isalnum() else " " for ch in text)
    return " ".join(text.lower().split())


def _match_one_source(squads: pd.DataFrame, stat_df: pd.DataFrame,
                      resolver: CountryResolver, tag: str, nation_col: str):
    """Fuzzy-match every squad player against one stat table; return attached
    columns (aligned to the squad index) and a list of low-confidence matches."""
    stat_df = stat_df.copy()
    stat_df["_code"] = stat_df[nation_col].map(resolver.to_code)
    stat_df["_norm"] = stat_df["player"].map(normalize_name)

    # Build one candidate pool per nation: {row_index: normalized_name}.
    pools: dict[str, dict] = {
        code: dict(zip(grp.index, grp["_norm"]))
        for code, grp in stat_df.groupby("_code")
    }

    rows, review = [], []
    for _, player in squads.iterrows():
        pool = pools.get(player["nation_code"])
        query = normalize_name(player["name"])
        best = (
            process.extractOne(query, pool, scorer=fuzz.token_set_ratio,
                               score_cutoff=MATCH_THRESHOLD)
            if pool else None
        )

        row = {}
        if best is not None:
            _, score, row_idx = best
            src = stat_df.loc[row_idx]
            for src_col, sem in CURATED.items():
                row[f"{tag}_{sem}"] = src.get(src_col, np.nan)
            row[f"{tag}_match_score"] = score
            row[f"{tag}_matched_player"] = src["player"]
            if score < REVIEW_THRESHOLD:
                review.append({
                    "squad_name": player["name"], "nation": player["nation_code"],
                    "matched_player": src["player"], "score": score, "source": tag,
                })
        else:
            for sem in CURATED.values():
                row[f"{tag}_{sem}"] = np.nan
            row[f"{tag}_match_score"] = np.nan
            row[f"{tag}_matched_player"] = None
        rows.append(row)

    return pd.DataFrame(rows, index=squads.index), review


def match_players_to_stats(squads_csv=SQUADS_CSV, output_csv=MERGED_STATS_CSV):
    """Attach club + international FBref stats to the full squad list."""
    print("Matching squads to FBref stats...")
    squads = pd.read_csv(squads_csv, encoding="utf-8")
    resolver = CountryResolver()

    merged = squads.copy()
    all_review = []
    for tag, filename, nation_col in SOURCES:
        stat_df = pd.read_csv(PROCESSED_DIR / filename, encoding="utf-8")
        attached, review = _match_one_source(squads, stat_df, resolver, tag, nation_col)
        merged = pd.concat([merged, attached], axis=1)
        all_review.extend(review)
        hit = attached[f"{tag}_match_score"].notna().sum()
        print(f"  {tag}: matched {hit:4d}/{len(squads)} squad players")

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(output_csv, index=False)

    review_path = PROCESSED_DIR / "match_review.csv"
    pd.DataFrame(all_review).to_csv(review_path, index=False)
    print(f"Saved {len(merged)} players -> {output_csv.name} "
          f"({len(all_review)} low-confidence matches logged to {review_path.name})")
    return merged


if __name__ == "__main__":
    match_players_to_stats()
