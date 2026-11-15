"""Read the station file. Given: nobody needs to change this."""
import pandas as pd


def load_station(path="data/station.csv"):
    """Daily data indexed by date, with columns tmin_c, tmax_c (deg C) and rain_mm."""
    return pd.read_csv(path, parse_dates=["date"], index_col="date")
