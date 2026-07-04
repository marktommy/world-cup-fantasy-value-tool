"""
Step 1: fetch the official 2026 World Cup squad list.

Downloads FIFA's squad-list PDF, parses it with pdfplumber + regex, and writes one
row per player to data/processed/squads_2026.csv. This CSV is the master list that
every later stage filters and joins against (~1,248 players across 48 nations).
"""

from __future__ import annotations

import io
import re

import pandas as pd
import pdfplumber
import requests

from wcfv.paths import SQUADS_CSV, ensure_dirs

PDF_URL = "https://fdp.fifa.org/assetspublic/ce281/pdf/SquadLists-English.pdf"

# Matches a team header line like "Argentina (ARG)".
TEAM_RE = re.compile(r"^(.+?)\s+\(([A-Z]{2,3})\)$")

# Matches a player row: number, position, name, DOB, club, height, caps, goals.
PLAYER_RE = re.compile(
    r"^(\d{1,2})\s+(GK|DF|MF|FW)\s+"   # jersey number + position
    r"(.+?)\s+"                          # player name (all caps, often duplicated)
    r"(\d{2}/\d{2}/\d{4})\s+"           # date of birth
    r"(.+?)\s+"                          # club (e.g. "Manchester City FC (ENG)")
    r"(\d{3})\s+"                         # height in cm
    r"(\d+)\s+"                           # caps
    r"(\d+)$"                             # international goals
)


def download_pdf(url: str = PDF_URL) -> io.BytesIO:
    print("Downloading FIFA squad-list PDF...")
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return io.BytesIO(response.content)


def parse_squads(pdf_file) -> pd.DataFrame:
    players = []
    current_team = current_code = None

    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue

            for line in text.split("\n"):
                line = line.strip()

                team = TEAM_RE.match(line)
                if team and "FIFA World Cup" not in line:
                    current_team, current_code = team.group(1).strip(), team.group(2).strip()
                    continue

                player = PLAYER_RE.match(line)
                if player and current_team:
                    club_raw = player.group(5).strip()
                    club = re.match(r"^(.+?)\s+\(([A-Z]{2,3})\)$", club_raw)
                    club_name = club.group(1).strip() if club else club_raw
                    club_country = club.group(2).strip() if club else ""

                    players.append({
                        "jersey_number": int(player.group(1)),
                        "position": player.group(2),
                        "name": player.group(3).strip(),
                        "dob": player.group(4),
                        "nation": current_team,
                        "nation_code": current_code,
                        "club": club_name,
                        "club_country": club_country,
                        "height_cm": int(player.group(6)),
                        "caps": int(player.group(7)),
                        "int_goals": int(player.group(8)),
                    })

    return pd.DataFrame(players)


def fetch_squads(output_csv=SQUADS_CSV) -> pd.DataFrame:
    ensure_dirs()
    df = parse_squads(download_pdf())
    df.to_csv(output_csv, index=False)
    print(f"Saved {len(df)} players from {df['nation'].nunique()} nations "
          f"-> {output_csv.name}")
    return df


if __name__ == "__main__":
    fetch_squads()
