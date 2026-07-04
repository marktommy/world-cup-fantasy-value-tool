"""
Stage 1 of processing: consolidation.

Each season/tournament arrives as FOUR separate FBref files (one per stat type:
standard, shooting, playing_time, misc). This module merges those four into ONE
wide table per season, so every player has a single row of stats.

We merge on the eight id-columns that appear in every file. They are unique within
each file and consistent across the four stat types, so the merge is a clean 1-to-1
join. A handful of columns repeat across files (e.g. `90s`); only those get their
stat type prefixed (`misc_90s`) so names never clash.
"""

from __future__ import annotations

import pandas as pd

from wcfv.paths import RAW_CLUB_DIR, RAW_INTERNATIONAL_DIR, PROCESSED_DIR

# The eight columns present in EVERY raw FBref file — used as the exact merge key.
ID_COLS = ["league", "season", "team", "player", "nation", "pos", "age", "born"]

# 'standard' is the base table; the rest are joined onto it, in this order.
STAT_TYPES = ["standard", "shooting", "playing_time", "misc"]


def consolidate_season(raw_dir, season, output_path,
                       stat_types=STAT_TYPES, id_cols=ID_COLS):
    """Merge the four stat-type CSVs for ONE season into a single wide table."""
    merged = None
    for stat_type in stat_types:
        path = raw_dir / f"{season}_{stat_type}.csv"
        df = pd.read_csv(path, encoding="utf-8")            # utf-8 is mandatory
        if merged is None:
            merged = df                                     # 'standard' = base
            continue
        # Prefix only the non-key columns that already exist, so repeats don't clash.
        overlap = [c for c in df.columns if c in merged.columns and c not in id_cols]
        df = df.rename(columns={c: f"{stat_type}_{c}" for c in overlap})
        # Outer join: 'playing_time' lists more players than the others; keep them all.
        merged = merged.merge(df, on=id_cols, how="outer")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(output_path, index=False)
    print(f"  consolidated {season}: {len(merged)} rows x {len(merged.columns)} cols "
          f"-> {output_path.name}")
    return merged


# Which seasons exist for each competition, mapped to (raw_dir, output_prefix).
CLUB_SEASONS = ["2024-25", "2025-26"]
INTERNATIONAL_SEASONS = ["2018", "2022"]


def consolidate_all():
    """Consolidate every club and international season into data/processed/."""
    print("Consolidating raw FBref files...")
    for season in CLUB_SEASONS:
        consolidate_season(RAW_CLUB_DIR, season,
                           PROCESSED_DIR / f"club_{season}_consolidated.csv")
    for season in INTERNATIONAL_SEASONS:
        consolidate_season(RAW_INTERNATIONAL_DIR, season,
                           PROCESSED_DIR / f"international_{season}_consolidated.csv")
    print("Consolidation complete.")


if __name__ == "__main__":
    consolidate_all()
