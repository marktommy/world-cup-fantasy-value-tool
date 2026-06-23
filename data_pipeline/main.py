import requests
import pandas as pd

BASE_URL = "https://worldcup26.ir/get/teams"

def fetch_live_2026_teams():
    print("Connecting to the Open-Source World Cup 2026 Data Hub...")
    
    try:
        # Fire a clean GET request - notice we don't need ANY headers or API keys!
        response = requests.get(BASE_URL)
        
        # Verify the request was successful
        if response.status_code != 200:
            print(f"Failed to fetch data. Server status code: {response.status_code}")
            return None
            
        raw_data = response.json()
        
        # The community API returns a direct list or an object containing the list
        # Let's handle their structure elegantly
        teams_list = raw_data if isinstance(raw_data, list) else raw_data.get("teams", [])
        
        if not teams_list:
            print("No teams found in the response payload.")
            return None
            
        print(f"Success! Retrieved {len(teams_list)} active 2026 World Cup teams.")
        
        # Extract the key data points we want to look at
        parsed_teams = []
        for team in teams_list:
            parsed_teams.append({
                "Team Name": team.get("name_en"),
                "Group": team.get("groups", "N/A"),
                "Code": team.get("fifa_code", "N/A"),
                "ID": team.get("_id")
            })
            
        # Throw it into a beautiful Pandas DataFrame table
        df = pd.DataFrame(parsed_teams)
        
        # Sort it by group then team name to make it look highly organized
        df = df.sort_values(by=["Group", "Team Name"]).reset_index(drop=True)
        return df

    except Exception as e:
        print(f"An error occurred while connecting to the open source engine: {e}")
        return None

if __name__ == "__main__":
    df_2026 = fetch_live_2026_teams()
    
    if df_2026 is not None:
        print("\n--- OFFICIAL 2026 WORLD CUP TEAMS & GROUPS (FREE DATA) ---")
        print(df_2026.to_string())