"""Ingestion CLI. Every command is idempotent: running it twice upserts the same
rows instead of duplicating them.
"""

import logging

import typer
from geoalchemy2 import WKTElement
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from calima_api.database import engine
from calima_api.ingestion.altitude import fetch_elevations
from calima_api.ingestion.stations import build_stations
from calima_api.models import Station

app = typer.Typer()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)


@app.callback()
def main() -> None:
    """Keeps Typer from collapsing to a single command while there is only one."""


@app.command("stations")
def ingest_stations() -> None:
    """Upsert every station that has measurement data (see ingestion/stations.py)."""
    stations = build_stations()

    with Session(engine) as session:
        for station in stations:
            location = WKTElement(f"POINT({station['longitude']} {station['latitude']})", srid=4326)
            values = {
                "station_code": station["station_code"],
                "eea_code": station["eea_code"],
                "name": station["name"],
                "island": station["island"],
                "altitude_m": station["altitude_m"],
                "station_type": station["station_type"],
                "station_area": station["station_area"],
                "location": location,
            }
            stmt = insert(Station).values(**values)
            stmt = stmt.on_conflict_do_update(index_elements=["station_code"], set_=values)
            session.execute(stmt)
        session.commit()

    logger.info("Upserted %d stations", len(stations))


@app.command("backfill-altitude")
def backfill_altitude() -> None:
    """Fill altitude_m from Open-Elevation for stations that have none."""
    with Session(engine) as session:
        rows = session.execute(
            select(Station.station_code, func.ST_Y(Station.location), func.ST_X(Station.location)).where(
                Station.altitude_m.is_(None)
            )
        ).all()

        if not rows:
            logger.info("No stations missing altitude_m")
            return

        elevations = fetch_elevations([tuple(row) for row in rows])
        for station_code, elevation in elevations.items():
            session.execute(update(Station).where(Station.station_code == station_code).values(altitude_m=elevation))
        session.commit()

    logger.info("Backfilled altitude_m for %d stations", len(elevations))


if __name__ == "__main__":
    app()
