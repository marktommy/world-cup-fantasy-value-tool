"""
Run the full World Cup Fantasy Value pipeline, end to end.

    python run_pipeline.py            # process + model, using already-fetched raw data
    python run_pipeline.py --fetch    # also re-fetch squads + FBref stats (needs Chrome)

Stages, in order:
    1. (optional) fetch squads + FBref stats          [--fetch, slow, needs Selenium]
    2. consolidate the raw FBref files                (process.consolidate)
    3. match stats to the squad list                  (process.match)
    4. fetch groups / strength / prices               (fast network calls, cached)
    5. build projections + export JSON                (model.build, export)

The heavy scraping in stage 1 is off by default because the raw CSVs are already on
disk; every later stage reads from disk, so the pipeline is cheap to re-run while
iterating on the model.
"""

from __future__ import annotations

import argparse
import time

from wcfv.env import load_env


def main():
    parser = argparse.ArgumentParser(description="World Cup Fantasy Value pipeline")
    parser.add_argument("--fetch", action="store_true",
                        help="also re-fetch squads + FBref stats (slow, needs Chrome)")
    args = parser.parse_args()

    load_env()                       # pick up ODDS_API_KEY from .env if present
    start = time.time()

    if args.fetch:
        from wcfv.fetch import squads, fbref
        squads.fetch_squads()
        fbref.fetch_club_stats()
        fbref.fetch_international_stats()

    from wcfv.process import consolidate, match
    from wcfv.fetch import groups, strength, prices
    from wcfv import export

    consolidate.consolidate_all()
    match.match_players_to_stats()
    groups.fetch_groups_and_fixtures()
    strength.fetch_team_strength()
    prices.fetch_prices()
    export.export_json()

    print(f"\nPipeline complete in {time.time() - start:.1f}s.")


if __name__ == "__main__":
    main()
