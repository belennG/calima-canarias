"""Builds the rows for the stations table from the EEA/MITECO metadata files.

The EEA hourly PM10 archive (data/raw/eea_pm10/*.parquet) is the source of truth for
which stations exist: measurements will have a foreign key to stations, so every
station code with measurement data needs a row here, whether or not the metadata
snapshots below happen to cover it.

Two metadata snapshots, taken at different times, fill in the rest of each station's
attributes, and disagree on which stations exist because the network itself changes
over time (stations open, close, get replaced):

- `canarias_pm10_samplingpoints.csv`: the EEA's own station registry (eea_code,
  altitude, station_type, station_area, coordinates). Covers 52 of our 56 stations.
- `canarias_station_coordinates.csv`: derived from the MITECO 2024 PM10 evaluation
  shapefile (name, coordinates, and its own EoI code). Covers 51 of our 56 stations.

See docs/decisions.md for the full reconciliation, including the one station whose
municipality has no coordinates in either file.
"""

import csv
import glob
from pathlib import Path

import pandas as pd

from calima_api.models import Island, StationArea, StationType

REPO_ROOT = Path(__file__).resolve().parents[4]
SAMPLINGPOINTS_CSV = REPO_ROOT / "data" / "raw" / "canarias_pm10_samplingpoints.csv"
COORDINATES_CSV = REPO_ROOT / "data" / "processed" / "canarias_station_coordinates.csv"
MEASUREMENTS_GLOB = str(REPO_ROOT / "data" / "raw" / "eea_pm10" / "*.parquet")

# Used to assign each station to its nearest island. The islands are tens of
# kilometres apart, so nearest-centroid is unambiguous - verified against every
# station name in canarias_station_coordinates.csv (e.g. "ARRECIFE" -> lanzarote,
# "SS GOMERA" -> la_gomera).
ISLAND_CENTROIDS: dict[Island, tuple[float, float]] = {
    Island.TENERIFE: (28.27, -16.60),
    Island.GRAN_CANARIA: (27.95, -15.59),
    Island.LANZAROTE: (29.04, -13.64),
    Island.FUERTEVENTURA: (28.40, -14.00),
    Island.LA_PALMA: (28.68, -17.84),
    Island.LA_GOMERA: (28.11, -17.21),
    Island.EL_HIERRO: (27.75, -17.99),
}

# `canarias_station_coordinates.csv` has no row at all for municipality 38024 (Los
# Llanos de Aridane, La Palma), so there is no sibling station to fall back to there
# either. Checked the EEA's live metadata.csv and station service too - neither has
# it (see docs/decisions.md). This is the town's own centre, not the real sensor
# location.
MUNICIPALITY_FALLBACK_COORDINATES: dict[str, tuple[float, float]] = {
    "38024": (28.65851, -17.91821),  # Los Llanos de Aridane, La Palma (geodatos.net)
}


def nearest_island(latitude: float, longitude: float) -> Island:
    return min(
        ISLAND_CENTROIDS,
        key=lambda island: (latitude - ISLAND_CENTROIDS[island][0]) ** 2
        + (longitude - ISLAND_CENTROIDS[island][1]) ** 2,
    )


def measured_station_codes() -> set[str]:
    """Every station code that has at least one row in the EEA hourly archive."""
    codes: set[str] = set()
    for parquet_file in glob.glob(MEASUREMENTS_GLOB):
        sampling_points = pd.read_parquet(parquet_file, columns=["Samplingpoint"])["Samplingpoint"]
        codes.update(sampling_points.str.extract(r"SP_(\d+)_")[0].dropna().unique())
    return codes


def read_samplingpoints(csv_path: Path = SAMPLINGPOINTS_CSV) -> dict[str, dict]:
    with open(csv_path, newline="", encoding="utf-8") as f:
        return {row["AirQualityStationNatCode"]: row for row in csv.DictReader(f)}


def read_coordinates(csv_path: Path = COORDINATES_CSV) -> dict[str, dict]:
    with open(csv_path, newline="", encoding="utf-8") as f:
        return {row["station_code"]: row for row in csv.DictReader(f)}


def build_station(
    station_code: str,
    sampling_point: dict | None,
    coordinate: dict | None,
    sibling_coordinate: tuple[float, float] | None = None,
) -> dict:
    """One station row, merged from whichever metadata sources cover this code.

    sibling_coordinate is another station's coordinates in the same municipality
    (first 5 digits of station_code), used when this station has none of its own -
    a closer approximation than a town-centre lookup, and needs no external source.
    """
    # canarias_pm10_samplingpoints.csv has a Longitude/Latitude column, but it is
    # empty for every single row in our 60 - the EEA vocabulary export used here
    # does not actually carry coordinates. canarias_station_coordinates.csv (from
    # the MITECO shapefile) is the only local source that does.
    if sampling_point is not None and sampling_point["Longitude"] and sampling_point["Latitude"]:
        latitude = float(sampling_point["Latitude"])
        longitude = float(sampling_point["Longitude"])
    elif coordinate is not None:
        latitude = float(coordinate["LATITUD_G"])
        longitude = float(coordinate["LONGITUD_G"])
    elif sibling_coordinate is not None:
        latitude, longitude = sibling_coordinate
    else:
        latitude, longitude = MUNICIPALITY_FALLBACK_COORDINATES[station_code[:5]]

    eea_code = None
    if sampling_point is not None:
        eea_code = sampling_point["AirQualityStationEoICode"]
    elif coordinate is not None:
        eea_code = coordinate["COD_ESTACI"]

    name = coordinate["NOMBRE"] if coordinate is not None else (eea_code or station_code)

    station_type = None
    station_area = None
    altitude_m = None
    if sampling_point is not None:
        if sampling_point["AirQualityStationType"]:
            station_type = StationType(sampling_point["AirQualityStationType"])
        if sampling_point["AirQualityStationArea"]:
            station_area = StationArea(sampling_point["AirQualityStationArea"])
        altitude_m = float(sampling_point["Altitude"])

    return {
        "station_code": station_code,
        "eea_code": eea_code,
        "name": name,
        "island": nearest_island(latitude, longitude),
        "altitude_m": altitude_m,
        "station_type": station_type,
        "station_area": station_area,
        "latitude": latitude,
        "longitude": longitude,
    }


def build_stations() -> list[dict]:
    """One row per measured station code, ready to upsert into the stations table."""
    samplingpoints = read_samplingpoints()
    coordinates = read_coordinates()

    municipality_siblings: dict[str, tuple[float, float]] = {}
    for code, coordinate in coordinates.items():
        municipality_siblings.setdefault(
            code[:5], (float(coordinate["LATITUD_G"]), float(coordinate["LONGITUD_G"]))
        )

    return [
        build_station(
            station_code,
            samplingpoints.get(station_code),
            coordinates.get(station_code),
            municipality_siblings.get(station_code[:5]),
        )
        for station_code in sorted(measured_station_codes())
    ]
