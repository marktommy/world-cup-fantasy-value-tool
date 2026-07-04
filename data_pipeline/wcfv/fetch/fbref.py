"""
Step 2: fetch player stats from FBref (via the soccerdata library).

Two competitions are pulled:
  - club:          the Big-5 European leagues, seasons 2024-25 and 2025-26
  - international: the FIFA World Cup, 2018 and 2022

For each we download four stat tables (standard, shooting, playing_time, misc) and
save one raw CSV per season/stat-type. soccerdata drives a real headless Chrome via
Selenium, so this MUST run on a machine with Chrome installed — it cannot run in a
sandbox. Files that already exist are skipped, making the fetch resumable.
"""

from __future__ import annotations

import time

import soccerdata as sd

from wcfv.paths import RAW_CLUB_DIR, RAW_INTERNATIONAL_DIR, ensure_dirs

CLUB_SEASONS = ["2024-25", "2025-26"]
INTERNATIONAL_SEASONS = ["2022", "2018"]

# soccerdata's FBref reader only exposes these four stat types (no passing/defensive
# or dedicated goalkeeping table in this version).
STAT_TYPES = ["standard", "shooting", "playing_time", "misc"]

REQUEST_DELAY_SECONDS = 3   # be polite; FBref rate-limits fast scrapers


def _flatten_columns(df):
    """FBref returns two-level column headers, e.g. ('Performance', 'Gls'). Join each
    tuple into a single flat, lower-case string like 'performance_gls'."""
    new_columns = []
    for col in df.columns:
        if isinstance(col, tuple):
            joined = "_".join(str(p) for p in col if p)   # drop empty tuple halves
        else:
            joined = str(col)
        new_columns.append(joined.strip().lower().replace(" ", "_"))
    df.columns = new_columns
    return df


def _fetch(leagues, season, stat_type, out_dir):
    out_path = out_dir / f"{season}_{stat_type}.csv"
    if out_path.exists():
        print(f"  skip {out_path.name} (already downloaded)")
        return
    try:
        print(f"  fetching {stat_type} for {season}...")
        fbref = sd.FBref(leagues=leagues, seasons=season)
        df = _flatten_columns(fbref.read_player_season_stats(stat_type=stat_type).reset_index())
        df.to_csv(out_path, index=False)
        print(f"  saved {len(df)} rows -> {out_path.name}")
    except Exception as exc:                                # keep going on a single failure
        print(f"  FAILED {stat_type} for {season}: {exc}")
    time.sleep(REQUEST_DELAY_SECONDS)


def fetch_club_stats():
    ensure_dirs()
    print("Fetching Big-5 club stats...")
    for season in CLUB_SEASONS:
        for stat_type in STAT_TYPES:
            _fetch("Big 5 European Leagues Combined", season, stat_type, RAW_CLUB_DIR)


def fetch_international_stats():
    ensure_dirs()
    print("Fetching World Cup international stats...")
    for season in INTERNATIONAL_SEASONS:
        for stat_type in STAT_TYPES:
            _fetch("INT-World Cup", season, stat_type, RAW_INTERNATIONAL_DIR)


if __name__ == "__main__":
    fetch_club_stats()
    fetch_international_stats()
