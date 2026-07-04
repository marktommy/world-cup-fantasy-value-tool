import os
import time
import soccerdata as sd


def _flatten_columns(df):
    """
    FBref returns column headers as two-level tuples, e.g.
    ('Performance', 'Gls') for goals or ('Per 90 Minutes', 'Ast') for
    assists per 90. Saving that straight to CSV produces a messy,
    inconsistent header row - and reading it back later would be
    error-prone. This function joins each tuple into a single flat
    string like 'performance_gls', so every saved CSV has normal,
    predictable column names.
    """
    new_columns = []
    for col in df.columns:
        if isinstance(col, tuple):
            # Some columns like ('player', '') only have one meaningful
            # part - the `if p` filter drops the empty string so we don't
            # end up with a trailing underscore like 'player_'.
            parts = [str(p) for p in col if p]
            joined = "_".join(parts)
        else:
            joined = str(col)

        # Normalise casing and spacing so every column follows the same
        # style, e.g. "Playing Time" -> "playing_time".
        joined = joined.strip().lower().replace(" ", "_")
        new_columns.append(joined)

    df.columns = new_columns
    return df


# --- Configuration constants ---
# Keeping these as constants at the top makes them easy to find and change
# later without hunting through the function bodies.

# The two seasons we agreed to pull, in "YYYY-YY" format.
FBREF_CLUB_SEASONS = ["2024-25", "2025-26"]

# The stat tables actually available via soccerdata's FBref reader.
# NOTE: 'passing' and 'defensive' are NOT available in this library version -
# only these five stat_types are supported by read_player_season_stats().
FBREF_CLUB_STAT_TYPES = ["standard", "shooting", "playing_time", "misc"]

# World Cup years for international stats. FBref uses a "single-year" format
# for international tournaments (e.g. "2022"), unlike club leagues which
# span two years (e.g. "2024-25").
FBREF_INTERNATIONAL_SEASONS = ["2022", "2018"]
FBREF_INTERNATIONAL_STAT_TYPES = ["standard", "shooting", "playing_time", "misc"]

# Where raw pulls get saved, one file per league/season/stat_type combo.
RAW_CLUB_DIR = "data/raw/club"
RAW_INTERNATIONAL_DIR = "data/raw/international"


def fetch_fbref_club_stats():
    """
    Downloads player stats for the Big 5 European leagues from FBref,
    for each season and stat type configured above. Saves one CSV per
    season/stat_type combination to data/raw/club/.
    """
    # os.makedirs creates the folder (and any missing parent folders) if it
    # doesn't already exist. exist_ok=True means: don't raise an error if
    # the folder is already there - just carry on.
    os.makedirs(RAW_CLUB_DIR, exist_ok=True)

    for season in FBREF_CLUB_SEASONS:
        print(f"\n--- Fetching Big 5 club stats for {season} ---")

        # We create a fresh FBref reader for each season, rather than one
        # reader covering every season at once. This keeps each season's
        # data cleanly separated, and if one season fails it doesn't
        # affect the others.
        fbref = sd.FBref(
            leagues="Big 5 European Leagues Combined",
            seasons=season,
        )

        for stat_type in FBREF_CLUB_STAT_TYPES:
            # Build the output path, e.g. data/raw/club/2024-25_standard.csv
            output_path = os.path.join(RAW_CLUB_DIR, f"{season}_{stat_type}.csv")

            # Skip re-downloading if the file already exists. This makes the
            # fetcher resumable - if it crashes or gets rate-limited halfway
            # through, re-running it picks up where it left off instead of
            # starting over.
            if os.path.exists(output_path):
                print(f"  Skipping {stat_type} (already downloaded)")
                continue

            try:
                print(f"  Fetching {stat_type} stats...")
                df = fbref.read_player_season_stats(stat_type=stat_type)

                # FBref returns data indexed by (league, season, team, player)
                # rather than plain numbered rows. reset_index() converts
                # those index levels into normal columns, which is much
                # easier to work with in later steps like fuzzy matching.
                df = df.reset_index()

                # The stat columns themselves (e.g. goals, assists) also come
                # back as two-level tuples like ('Performance', 'Gls'). Flatten
                # those into plain strings like 'performance_gls' before saving.
                df = _flatten_columns(df)

                df.to_csv(output_path, index=False)
                print(f"  Saved {len(df)} rows to {output_path}")

            except Exception as e:
                # If one stat type fails, we log it and move on rather than
                # crashing the whole fetch. We'd rather get 3 out of 4 stat
                # tables than get nothing because of one bad pull.
                print(f"  FAILED to fetch {stat_type} for {season}: {e}")

            # Pause between requests. FBref rate-limits scrapers that make
            # requests too quickly, so this small delay protects us from
            # getting temporarily blocked.
            time.sleep(3)

    print("\nClub stats fetch complete.")


def fetch_fbref_international_stats():
    """
    Downloads player stats from the FIFA World Cup on FBref for the years
    configured above. Coverage here is known to be patchier than club
    data - some players or stat columns may be missing entirely.
    """
    os.makedirs(RAW_INTERNATIONAL_DIR, exist_ok=True)

    for season in FBREF_INTERNATIONAL_SEASONS:
        print(f"\n--- Fetching World Cup {season} international stats ---")

        fbref = sd.FBref(
            leagues="INT-World Cup",
            seasons=season,
        )

        for stat_type in FBREF_INTERNATIONAL_STAT_TYPES:
            output_path = os.path.join(
                RAW_INTERNATIONAL_DIR, f"{season}_{stat_type}.csv"
            )

            if os.path.exists(output_path):
                print(f"  Skipping {stat_type} (already downloaded)")
                continue

            try:
                print(f"  Fetching {stat_type} stats...")
                df = fbref.read_player_season_stats(stat_type=stat_type)
                df = df.reset_index()
                df = _flatten_columns(df)
                df.to_csv(output_path, index=False)
                print(f"  Saved {len(df)} rows to {output_path}")
            except Exception as e:
                print(f"  FAILED to fetch {stat_type} for World Cup {season}: {e}")

            time.sleep(3)

    print("\nInternational stats fetch complete.")


if __name__ == "__main__":
    # This block only runs when this file is executed directly (e.g.
    # `python fbref_fetchers.py`), not when its functions are imported into
    # another file like main.py. It's a handy way to test just this file
    # in isolation without triggering the whole pipeline.
    fetch_fbref_club_stats()
    fetch_fbref_international_stats()