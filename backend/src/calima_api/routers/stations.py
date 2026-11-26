"""GET /stations: every station as a GeoJSON FeatureCollection, for the map."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from calima_api.database import get_db
from calima_api.models import Station

router = APIRouter()


def station_to_feature(station: Station, longitude: float, latitude: float) -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [longitude, latitude]},
        "properties": {
            "station_code": station.station_code,
            "eea_code": station.eea_code,
            "name": station.name,
            "island": station.island.value,
            "altitude_m": station.altitude_m,
            "station_type": station.station_type.value if station.station_type else None,
            "station_area": station.station_area.value if station.station_area else None,
        },
    }


@router.get("/stations")
def list_stations(db: Session = Depends(get_db)) -> dict:
    rows = db.execute(
        select(Station, func.ST_X(Station.location), func.ST_Y(Station.location))
    ).all()
    return {
        "type": "FeatureCollection",
        "features": [station_to_feature(station, lon, lat) for station, lon, lat in rows],
    }
