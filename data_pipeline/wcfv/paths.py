"""
Central path configuration.

Every other module imports its file locations from here instead of hard-coding
relative paths like "data/raw/...". Relative paths only work if you happen to run
Python from the right folder; by resolving everything from THIS file's location we
make the pipeline runnable from anywhere (an IDE, a cron job, a different drive).

`Path(__file__).resolve()` gives the absolute path to this file; `.parent` walks
up the folder tree. wcfv/paths.py -> wcfv/ -> data_pipeline/.
"""

from pathlib import Path

# data_pipeline/wcfv/paths.py  ->  data_pipeline/
PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent          # data_pipeline/
REPO_ROOT = PROJECT_ROOT.parent              # the git repo root

# --- Data folders --------------------------------------------------------
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
RAW_CLUB_DIR = RAW_DIR / "club"
RAW_INTERNATIONAL_DIR = RAW_DIR / "international"
PROCESSED_DIR = DATA_DIR / "processed"
OUTPUT_DIR = DATA_DIR / "output"

# --- Config folder -------------------------------------------------------
CONFIG_DIR = PROJECT_ROOT / "config"
COUNTRIES_CSV = CONFIG_DIR / "countries.csv"

# --- Key named files -----------------------------------------------------
SQUADS_CSV = PROCESSED_DIR / "squads_2026.csv"
MERGED_STATS_CSV = PROCESSED_DIR / "squad_stats_merged.csv"
GROUPS_CSV = PROCESSED_DIR / "groups_2026.csv"
FIXTURES_CSV = PROCESSED_DIR / "fixtures_2026.csv"
STRENGTH_CSV = PROCESSED_DIR / "team_strength.csv"
PRICES_CSV = PROCESSED_DIR / "prices_2026.csv"

# Final model outputs
VALUES_CSV = OUTPUT_DIR / "fantasy_values_2026.csv"
PLAYERS_JSON = OUTPUT_DIR / "players.json"

# Where the front-end reads its data from (a copy of the JSON above).
FRONTEND_DATA_DIR = REPO_ROOT / "frontend" / "public" / "data"


def ensure_dirs() -> None:
    """Create every output folder if it does not already exist."""
    for d in (RAW_CLUB_DIR, RAW_INTERNATIONAL_DIR, PROCESSED_DIR, OUTPUT_DIR, CONFIG_DIR):
        d.mkdir(parents=True, exist_ok=True)
