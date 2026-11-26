"""Download CAMS global forecasts for the Canary Islands, one request at a time.

Run it from the spikes/ folder:

    caffeinate -i uv run python download_cams.py

- Requests are sent one after another, never in parallel (ADS rule).
- Files that already exist are skipped, so the script can be stopped and run again.
- The cost of every request is checked against the ADS limit before it is sent.
- If anything fails, the script stops instead of retrying, so it never sends
  the same failing request twice. Run it again once the problem is fixed.

Before running it again after an interruption, check "Your requests" on the ADS
website: if a request is still queued or running there, wait for it (or delete it)
so that the script does not send a second copy.
"""

import logging
from datetime import date
from pathlib import Path

import cdsapi

DATASET = "cams-global-atmospheric-composition-forecasts"
VARIABLES = ["particulate_matter_10um", "dust_aerosol_optical_depth_550nm"]
LEADTIME_HOURS = [str(hour) for hour in range(0, 73, 3)]  # 0, 3, 6, ..., 72 → 25 values
AREA = [30, -19, 27, -13]  # North, West, South, East
COST_LIMIT = 10_000  # ADS limit per request: days × lead times × variables
OUTPUT_FOLDER = Path("../data/raw/cams/forecasts_3h")

# Priority order: the February 2020 episode first, then recent years, then older ones.
# Before 2015, check on the dataset page which is the first available date.
YEARS = [2020, 2021, 2022, 2023, 2024, 2025, 2019, 2018, 2017, 2016, 2015]


def half_years(year: int) -> list[tuple[date, date]]:
    """Split a year in two periods (January–June and July–December), each under the cost limit."""
    return [
        (date(year, 1, 1), date(year, 6, 30)),
        (date(year, 7, 1), date(year, 12, 31)),
    ]


def request_cost(start_date: date, end_date: date) -> int:
    """Number of fields the ADS counts for a request: days × lead times × variables."""
    number_of_days = (end_date - start_date).days + 1
    return number_of_days * len(LEADTIME_HOURS) * len(VARIABLES)


def download_period(client: cdsapi.Client, start_date: date, end_date: date) -> None:
    target_file = OUTPUT_FOLDER / f"cams_{start_date:%Y-%m-%d}_{end_date:%Y-%m-%d}_00utc_3h.zip"

    if target_file.exists():
        logging.info("Skip %s (already downloaded)", target_file.name)
        return

    cost = request_cost(start_date, end_date)
    if cost > COST_LIMIT:
        raise ValueError(f"{target_file.name}: cost {cost} is over the limit of {COST_LIMIT}")

    request = {
        "variable": VARIABLES,
        "date": [f"{start_date:%Y-%m-%d}/{end_date:%Y-%m-%d}"],
        "time": ["00:00"],
        "leadtime_hour": LEADTIME_HOURS,
        "type": ["forecast"],
        "data_format": "netcdf_zip",
        "area": AREA,
    }

    logging.info("Request %s (cost %d)", target_file.name, cost)

    # Download to a temporary name first. If the download is cut halfway,
    # the incomplete file keeps the temporary name, and the next run does not
    # mistake it for a finished download.
    partial_file = target_file.with_suffix(".part")
    client.retrieve(DATASET, request).download(str(partial_file))
    partial_file.rename(target_file)

    logging.info("Saved %s", target_file.name)


def main() -> None:
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(message)s",
        handlers=[
            logging.FileHandler(OUTPUT_FOLDER / "download.log"),
            logging.StreamHandler(),
        ],
    )

    client = cdsapi.Client()
    for year in YEARS:
        for start_date, end_date in half_years(year):
            download_period(client, start_date, end_date)

    logging.info("All periods downloaded")


if __name__ == "__main__":
    main()