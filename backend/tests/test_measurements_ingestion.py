import pandas as pd

from calima_api.ingestion.measurements import measurement_rows
from calima_api.models import Dataset


def _df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def test_measurement_rows_extracts_station_code_and_marks_dataset_verified():
    df = _df(
        [
            {"Samplingpoint": "ES/SP_38006002_10_46", "Start": pd.Timestamp("2013-01-01 01:00:00"), "Value": 8, "Validity": 1},
        ]
    )

    [row] = measurement_rows(df)

    assert row["station_code"] == "38006002"
    assert row["start_utc"] == pd.Timestamp("2013-01-01 01:00:00")
    assert row["value"] == 8.0
    assert row["validity"] == 1
    assert row["dataset"] == Dataset.VERIFIED


def test_measurement_rows_turns_invalid_sentinel_into_null_value():
    df = _df(
        [
            {"Samplingpoint": "ES/SP_38006002_10_46", "Start": pd.Timestamp("2017-02-10 12:00:00"), "Value": -999, "Validity": -1},
        ]
    )

    [row] = measurement_rows(df)

    assert row["value"] is None
    assert row["validity"] == -1


def test_measurement_rows_handles_multiple_hours():
    df = _df(
        [
            {"Samplingpoint": "ES/SP_35016010_10_49", "Start": pd.Timestamp("2020-02-22 00:00:00"), "Value": 12, "Validity": 1},
            {"Samplingpoint": "ES/SP_35016010_10_49", "Start": pd.Timestamp("2020-02-22 01:00:00"), "Value": 55, "Validity": 1},
        ]
    )

    rows = measurement_rows(df)

    assert [row["value"] for row in rows] == [12.0, 55.0]
    assert all(row["station_code"] == "35016010" for row in rows)
