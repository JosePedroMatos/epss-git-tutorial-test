"""Station report. Open this file and press the Run Python File button (top right)."""
from weather.loader import load_station

df = load_station("data/station.csv")
print(f"{len(df)} days loaded: {df.index[0].date()} to {df.index[-1].date()}")

# --- members: paste your two lines below this line ---

# --- members: paste your two lines above this line ---
