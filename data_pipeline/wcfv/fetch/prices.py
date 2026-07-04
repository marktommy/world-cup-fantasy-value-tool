"""
Step 4b: player prices from the official World Cup Fantasy game.

Prices let us turn expected points into *value* (points per unit cost) — the metric
that actually wins fantasy leagues, because it surfaces under-priced players.

The official game's price feed is not reliably public, so this is best-effort:
we try a couple of known endpoints and, if none respond, return nothing. In that
case the value stage falls back to a synthetic price model
(`wcfv.model.pricing.synthetic_prices`) built from each player's stats — clearly
labelled as synthetic so the "value vs price" comparison is honest.
"""

from __future__ import annotations

import pandas as pd
import requests

from wcfv.paths import PRICES_CSV, ensure_dirs
from wcfv.process.countries import CountryResolver

# Candidate feeds for the official game. These change every tournament and are often
# geo/rate-limited, hence the best-effort try/except around them.
CANDIDATE_FEEDS = [
    "https://gaming.fifa.com/fantasy/api/feed/players?locale=en",
    "https://fantasy.fifa.com/api/players.json",
]

HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}


def _try_scrape() -> pd.DataFrame | None:
    resolver = CountryResolver()
    for url in CANDIDATE_FEEDS:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200 or "json" not in resp.headers.get("content-type", ""):
                continue
            payload = resp.json()
            players = payload.get("players", payload if isinstance(payload, list) else [])
            rows = []
            for p in players:
                name = p.get("name") or p.get("fullName")
                price = p.get("price") or p.get("value") or p.get("cost")
                code = resolver.to_code(p.get("country") or p.get("nationality") or "")
                if name and price:
                    rows.append({"name": name, "nation_code": code,
                                 "price": float(price), "source": "official"})
            if rows:
                print(f"  scraped {len(rows)} prices from {url}")
                return pd.DataFrame(rows)
        except Exception:
            continue
    return None


def fetch_prices(output_csv=PRICES_CSV) -> pd.DataFrame | None:
    ensure_dirs()
    print("Fetching official fantasy prices (best-effort)...")
    prices = _try_scrape()
    if prices is None:
        print("  no official price feed reachable — value stage will use synthetic prices")
        return None
    prices.to_csv(output_csv, index=False)
    print(f"  saved {len(prices)} official prices -> {output_csv.name}")
    return prices


if __name__ == "__main__":
    fetch_prices()
