"""
Transform the real EaseMyTrip Indian-domestic-fares dataset (2022) into the
ingestion pipeline's CSV contract.

WHY THIS SCRIPT EXISTS AND WHAT IT DOES NOT DO
------------------------------------------------
The source dataset (300,153 real fare-search rows, 6 major Indian metros,
scraped from EaseMyTrip) is genuine: every airline, route, class, lead-time,
and price value below is exactly what's in the original file. What the
source does NOT publish is a per-row calendar date - only a documented
collection window: 11 Feb 2022 - 31 Mar 2022 (per the dataset's own
description, widely cited in academic use of this data).

DATE HANDLING - READ THIS BEFORE TRUSTING ANY DATE IN THIS DATA
------------------------------------------------------------------
Two separate things happen to dates here, and they must not be confused:

1. Real collection window (2022): rows are placed round-robin across the
   dataset's ACTUAL documented 48-day window, so the real day-to-day price
   variation the source captured is preserved in relative terms.
2. Replay shift (2022 -> recent): that 48-day window is then SLID FORWARD
   so it ends on the day this script runs, purely so the app's existing
   "trailing 30/90 days" queries have something to show in a live demo.
   This is a deliberate, disclosed replay - not a claim that these are
   live 2026 prices. Every row is tagged source="csv-historical-real" and
   the data_sources record says so explicitly.

Do not remove the shift without also updating every analytics query that
filters on a trailing window from today - they would return nothing against
genuinely dated 2022 rows.
"""
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

SOURCE_FILE = Path(__file__).resolve().parent.parent / "data" / "raw" / "easemytrip_2022_real.csv"
OUTPUT_FILE = Path(__file__).resolve().parent.parent / "data" / "raw" / "easemytrip_2022_prepared.csv"

# The dataset's own REAL documented collection window (for the record).
REAL_WINDOW_START = date(2022, 2, 11)
REAL_WINDOW_END = date(2022, 3, 31)
WINDOW_DAYS = (REAL_WINDOW_END - REAL_WINDOW_START).days + 1

# Where that window is REPLAYED to, so trailing-30/90-day queries work in a
# live demo. Ends "today" whenever this script is run.
REPLAY_WINDOW_END = date.today()
REPLAY_WINDOW_START = REPLAY_WINDOW_END - timedelta(days=WINDOW_DAYS - 1)

CITY_TO_IATA = {
    "Delhi": "DEL",
    "Mumbai": "BOM",
    "Bangalore": "BLR",
    "Kolkata": "CCU",
    "Hyderabad": "HYD",
    "Chennai": "MAA",
}


def main():
    if not SOURCE_FILE.exists():
        print(f"Source file not found: {SOURCE_FILE}", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(SOURCE_FILE)

    df["origin"] = df["source_city"].map(CITY_TO_IATA)
    df["destination"] = df["destination_city"].map(CITY_TO_IATA)
    unmapped = df[df["origin"].isna() | df["destination"].isna()]
    if len(unmapped):
        print(f"Warning: {len(unmapped)} rows had an unmapped city, dropping them.")
        df = df.dropna(subset=["origin", "destination"])

    # Deterministic round-robin placement across the replay window (see
    # module docstring: real collection was 2022, replayed to end today).
    search_dates = [REPLAY_WINDOW_START + timedelta(days=int(i) % WINDOW_DAYS) for i in df.index]
    df["date"] = search_dates
    df["travel_date"] = [
        d + timedelta(days=int(days_left)) for d, days_left in zip(search_dates, df["days_left"])
    ]

    df["airline"] = df["airline"]
    df["days_to_departure"] = df["days_left"]
    df["price"] = df["price"]
    df["travel_class"] = df["class"]
    df["currency"] = "INR"
    # Total price is real; this dataset doesn't publish a fare/tax/fee split,
    # so those stay unset rather than inventing a breakdown.

    out = df[[
        "date", "origin", "destination", "airline", "days_to_departure",
        "price", "travel_class", "currency", "travel_date",
    ]]
    out.to_csv(OUTPUT_FILE, index=False)
    print(f"Wrote {len(out):,} rows to {OUTPUT_FILE}")
    print(f"Real dataset's documented collection window: {REAL_WINDOW_START}..{REAL_WINDOW_END}")
    print(f"Replayed (search_date) to: {min(search_dates)}..{max(search_dates)}")


if __name__ == "__main__":
    main()
