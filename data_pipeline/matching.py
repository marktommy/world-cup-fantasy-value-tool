"""
matching.py — Step 3 of the pipeline (Stage 1: consolidation).

Step 2 left us with FOUR separate CSV files per season/tournament, one for each
FBref stat type: 'standard', 'shooting', 'playing_time' and 'misc'. That's awkward
to work with — a single player's numbers are spread across four files.

This module's job (Stage 1) is to MERGE those four files back into ONE wide table
per season, so every player has a single row containing all their stats. Later
(Stage 2, not in this file yet) we'll fuzzy-match that consolidated table against
squads_2026.csv.

Keeping consolidation (this file) separate from fetching (fbref_fetchers.py) means
a bug here never forces us to re-scrape FBref — we just re-run this on the raw CSVs.
"""

import os
import pandas as pd


# --- Configuration constants ---

# ID_COLS are the eight columns that appear in EVERY raw FBref file. Together they
# uniquely identify one player-in-one-team-in-one-season, so we use them as the
# "merge key": the columns pandas lines up on when joining two tables. We verified
# against the real CSVs that these are unique within each file and identical across
# the four stat types, so merging on them is a clean 1-to-1 join (no row blow-up).
ID_COLS = ["league", "season", "team", "player", "nation", "pos", "age", "born"]

# The four stat tables to merge, in order. 'standard' goes FIRST because it's our
# base table (the widest, most useful one). Each later table is joined onto it.
STAT_TYPES = ["standard", "shooting", "playing_time", "misc"]


def consolidate_season(raw_dir, season, output_path,
                       stat_types=STAT_TYPES, id_cols=ID_COLS):
    """
    Merge the four stat-type CSVs for ONE season/tournament into a single wide
    table and save it to output_path.

    Parameters (these are placeholders — real values are passed in by the caller,
    e.g. consolidate_all() below):
      raw_dir     : folder holding the raw CSVs, e.g. "data/raw/club"
      season      : the season/tournament string, e.g. "2024-25" or "2022".
                    Combined with stat_type it builds each filename, e.g.
                    "2024-25_standard.csv".
      output_path : where to write the merged CSV.
      stat_types  : which stat tables to merge (defaults to all four above).
      id_cols     : the merge key (defaults to the eight ID_COLS above).
    """
    # `merged` starts as None. The first stat file we read becomes the base table;
    # every file after that gets joined onto `merged`.
    merged = None

    for stat_type in stat_types:
        # Build the path to this stat file, e.g. "data/raw/club/2024-25_standard.csv".
        path = os.path.join(raw_dir, f"{season}_{stat_type}.csv")

        # encoding="utf-8" is mandatory: the international files contain accented
        # names (e.g. players from Türkiye, Côte d'Ivoire). Windows would otherwise
        # default to cp1252 and crash with a UnicodeDecodeError.
        df = pd.read_csv(path, encoding="utf-8")

        # First time through the loop, `merged` is still None: this file ('standard')
        # becomes the base. `continue` skips straight to the next loop iteration.
        if merged is None:
            merged = df
            continue

        # Some columns repeat across stat files (e.g. both 'standard' and
        # 'playing_time' carry playing_time_mp). If we merged blindly, pandas would
        # rename the duplicates to messy names like playing_time_mp_x / _y.
        #
        # Instead we find the non-key columns in THIS file that already exist in the
        # accumulated `merged` table, and prefix just those with the stat type — so
        # misc's '90s' becomes 'misc_90s'. Columns that don't clash keep clean names.
        # (Longhand equivalent of the list comprehension below:
        #     overlap = []
        #     for c in df.columns:
        #         if c in merged.columns and c not in id_cols:
        #             overlap.append(c)
        # )
        overlap = [c for c in df.columns if c in merged.columns and c not in id_cols]
        df = df.rename(columns={c: f"{stat_type}_{c}" for c in overlap})

        # how="outer" keeps EVERY player from both tables. This matters because the
        # 'playing_time' table lists more players than the others (it includes people
        # with very few minutes). An inner join would silently drop them; outer keeps
        # them, leaving blanks (NaN) where a table had no data for that player.
        merged = merged.merge(df, on=id_cols, how="outer")

    # os.makedirs creates the output folder (and any missing parents) if needed.
    # os.path.dirname(output_path) pulls just the folder part out of the full path.
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # index=False stops pandas writing its internal 0,1,2… row numbers as a column.
    merged.to_csv(output_path, index=False)
    print(f"Saved {len(merged)} rows x {len(merged.columns)} cols -> {output_path}")

    # Returning the DataFrame lets a caller inspect it in memory without re-reading
    # the file — handy for quick checks or tests.
    return merged


def consolidate_all():
    """
    Run consolidate_season() for all four season/tournament combinations we have,
    producing four consolidated CSVs in data/processed/.

    Note this same function handles BOTH club and international data — only the
    folder and season strings change. That's deliberate: the consolidation logic is
    identical for both, so we don't duplicate it.
    """
    for season in ["2024-25", "2025-26"]:
        consolidate_season(
            "data/raw/club",
            season,
            f"data/processed/club_{season}_consolidated.csv",
        )

    for season in ["2018", "2022"]:
        consolidate_season(
            "data/raw/international",
            season,
            f"data/processed/international_{season}_consolidated.csv",
        )


if __name__ == "__main__":
    # This block only runs when the file is executed directly
    # (`python matching.py`), not when its functions are imported elsewhere.
    consolidate_all()
