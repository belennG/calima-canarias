"""Builds the rows for the measurements table from the EEA hourly PM10 archive.

data/raw/eea_pm10/*.parquet is the EEA's *verified* PM10 dataset (see CLAUDE.md) - one
file per station. Every row here is tagged dataset=Dataset.VERIFIED: checked across all
121 local files, the EEA's own `Verification` column is always 1, confirming this is all
the same dataset. The `up_to_date` (preliminary, unverified) dataset is a separate EEA
download we have not fetched yet - ingesting it is a later task.
"""

import glob
from pathlib import Path

import pandas as pd

from calima_api.models import Dataset

REPO_ROOT = Path(__file__).resolve().parents[4]
MEASUREMENTS_GLOB = str(REPO_ROOT / "data" / "raw" / "eea_pm10" / "*.parquet")

# EEA flags a reading as invalid (Validity == -1) and stores the sentinel -999 in Value
# instead of a real number. Loading -999 as a real ug/m3 reading would poison any mean or
# threshold calculation downstream - store NULL instead (see docs/decisions.md).
INVALID_VALIDITY = -1


def measurement_files() -> list[str]:
    return sorted(glob.glob(MEASUREMENTS_GLOB))


def measurement_rows(df: pd.DataFrame) -> list[dict]:
    """One station's raw EEA rows, transformed into rows ready to upsert.

    df must have the columns Samplingpoint, Start, Value, Validity - all rows are
    expected to share the same Samplingpoint (one parquet file = one station).
    """
    station_code = df["Samplingpoint"].str.extract(r"SP_(\d+)_")[0].iloc[0]

    return [
        {
            "station_code": station_code,
            "start_utc": row.Start,
            "value": float(row.Value) if row.Validity != INVALID_VALIDITY else None,
            "validity": int(row.Validity),
            "dataset": Dataset.VERIFIED,
        }
        for row in df.itertuples(index=False)
    ]


def read_measurement_file(parquet_file: str) -> list[dict]:
    df = pd.read_parquet(parquet_file, columns=["Samplingpoint", "Start", "Value", "Validity"])
    return measurement_rows(df)
