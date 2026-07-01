import soccerdata as sd

print("Creating FBref reader for Premier League/Big 5, 2024-25 season...")

# A single, small, deliberate pull - just one season, one stat type.
# If this works, we know the full fetcher will work too.
fbref = sd.FBref(
    leagues="Big 5 European Leagues Combined",
    seasons="2024-25",
)

print("Reader created. Attempting to pull 'standard' stats...")
print("(This may take a little while the first time - it's launching a")
print("real headless Chrome browser behind the scenes via Selenium.)")

df = fbref.read_player_season_stats(stat_type="standard")

# Flatten the row index into normal columns, same as the real fetcher does.
df = df.reset_index()

# The column headers ALSO come back as two-level tuples like
# ('Performance', 'Gls') - flatten those into plain strings too, e.g.
# 'performance_gls', so the saved CSV has clean, predictable headers.
new_columns = []
for col in df.columns:
    if isinstance(col, tuple):
        parts = [str(p) for p in col if p]
        joined = "_".join(parts)
    else:
        joined = str(col)
    new_columns.append(joined.strip().lower().replace(" ", "_"))
df.columns = new_columns

print(f"\nSuccess! Pulled {len(df)} player rows.")
print("\nColumn names:")
print(list(df.columns))

print("\nFirst 5 rows:")
print(df.head())

# Save it so you can open it in Excel/a text editor and eyeball it properly.
df.to_csv("test_pull_output.csv", index=False)
print("\nAlso saved to test_pull_output.csv for you to inspect.")