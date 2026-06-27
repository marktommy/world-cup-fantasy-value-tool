import re
import requests
import pdfplumber
import pandas as pd
import io

PDF_URL = "https://fdp.fifa.org/assetspublic/ce281/pdf/SquadLists-English.pdf"

def download_pdf(url):
    print("Downloading FIFA squad list PDF...")
    response = requests.get(url)
    response.raise_for_status()
    return io.BytesIO(response.content)

def parse_squads(pdf_file):
    players = []
    current_team = None
    current_code = None

    # Matches lines like "Argentina (ARG)"
    team_pattern = re.compile(r'^(.+?)\s+\(([A-Z]{2,3})\)$')

    # Matches player rows — starts with a number 1-26
    player_pattern = re.compile(
        r'^(\d{1,2})\s+(GK|DF|MF|FW)\s+'   # jersey number + position
        r'(.+?)\s+'                           # player name (all caps)
        r'(\d{2}/\d{2}/\d{4})\s+'            # DOB
        r'(.+?)\s+'                           # club name
        r'(\d{3})\s+'                         # height
        r'(\d+)\s+'                           # caps
        r'(\d+)$'                             # goals
    )

    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue

            for line in text.split('\n'):
                line = line.strip()

                # Check for team header
                team_match = team_pattern.match(line)
                if team_match:
                    # Ignore the repeated "FIFA World Cup 2026" title line
                    if 'FIFA World Cup' not in line:
                        current_team = team_match.group(1).strip()
                        current_code = team_match.group(2).strip()
                    continue

                # Check for player row
                player_match = player_pattern.match(line)
                if player_match and current_team:
                    jersey    = player_match.group(1)
                    position  = player_match.group(2)
                    name      = player_match.group(3).strip()
                    dob       = player_match.group(4)
                    club_raw  = player_match.group(5).strip()
                    height    = player_match.group(6)
                    caps      = player_match.group(7)
                    goals     = player_match.group(8)

                    # Club raw looks like "Manchester City FC (ENG)"
                    # Split out the club country code
                    club_match = re.match(r'^(.+?)\s+\(([A-Z]{2,3})\)$', club_raw)
                    if club_match:
                        club_name    = club_match.group(1).strip()
                        club_country = club_match.group(2).strip()
                    else:
                        club_name    = club_raw
                        club_country = ""

                    players.append({
                        "jersey_number": int(jersey),
                        "position":      position,
                        "name":          name,
                        "dob":           dob,
                        "nation":        current_team,
                        "nation_code":   current_code,
                        "club":          club_name,
                        "club_country":  club_country,
                        "height_cm":     int(height),
                        "caps":          int(caps),
                        "int_goals":     int(goals),
                    })

    return pd.DataFrame(players)


def main():
    pdf_file = download_pdf(PDF_URL)
    df = parse_squads(pdf_file)

    print(f"\nTotal players parsed: {len(df)}")
    print(f"Total nations: {df['nation'].nunique()}")
    print(f"\nSample rows:")
    print(df.head(10).to_string())

    output_path = "squads_2026.csv"
    df.to_csv(output_path, index=False)
    print(f"\nSaved to {output_path}")


if __name__ == "__main__":
    main()