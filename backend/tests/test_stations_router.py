from calima_api.models import Island, Station, StationArea, StationType
from calima_api.routers.stations import station_to_feature


def test_station_to_feature_includes_coordinates_and_properties():
    station = Station(
        station_code="35002001",
        eea_code="ES1745A",
        name="AGÜIMES",
        island=Island.GRAN_CANARIA,
        altitude_m=150.0,
        station_type=StationType.BACKGROUND,
        station_area=StationArea.RURAL_REGIONAL,
    )

    feature = station_to_feature(station, longitude=-15.445028, latitude=27.897639)

    assert feature["geometry"] == {"type": "Point", "coordinates": [-15.445028, 27.897639]}
    assert feature["properties"]["station_code"] == "35002001"
    assert feature["properties"]["island"] == "gran_canaria"
    assert feature["properties"]["station_type"] == "background"


def test_station_to_feature_handles_missing_optional_fields():
    station = Station(
        station_code="35002003",
        eea_code=None,
        name="35002003",
        island=Island.GRAN_CANARIA,
        altitude_m=None,
        station_type=None,
        station_area=None,
    )

    feature = station_to_feature(station, longitude=-15.445, latitude=27.905)

    assert feature["properties"]["eea_code"] is None
    assert feature["properties"]["station_type"] is None
    assert feature["properties"]["station_area"] is None
