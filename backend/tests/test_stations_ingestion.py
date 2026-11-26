from calima_api.ingestion.stations import build_station, nearest_island
from calima_api.models import Island, StationArea, StationType


def test_nearest_island_matches_known_towns():
    assert nearest_island(28.976990, -13.547584) == Island.LANZAROTE  # Arrecife
    assert nearest_island(28.099050, -17.120510) == Island.LA_GOMERA  # SS Gomera
    assert nearest_island(28.685983, -17.764587) == Island.LA_PALMA  # Sta Cruz de la Palma
    assert nearest_island(27.831766, -17.921671) == Island.EL_HIERRO  # Valverde
    assert nearest_island(28.455375, -16.276750) == Island.TENERIFE  # Sta Cruz de Tenerife


def test_build_station_prefers_samplingpoint_metadata():
    sampling_point = {
        "Latitude": "27.897639",
        "Longitude": "-15.445028",
        "Altitude": "150",
        "AirQualityStationEoICode": "ES1745A",
        "AirQualityStationType": "background",
        "AirQualityStationArea": "rural-regional",
    }
    coordinate = {"LATITUD_G": "0", "LONGITUD_G": "0", "COD_ESTACI": "ES1745A", "NOMBRE": "AGÜIMES"}

    station = build_station("35002001", sampling_point, coordinate)

    assert station["eea_code"] == "ES1745A"
    assert station["name"] == "AGÜIMES"
    assert station["island"] == Island.GRAN_CANARIA
    assert station["altitude_m"] == 150
    assert station["station_type"] == StationType.BACKGROUND
    assert station["station_area"] == StationArea.RURAL_REGIONAL
    assert station["latitude"] == 27.897639


def test_build_station_falls_back_to_coordinates_csv_when_no_samplingpoint():
    coordinate = {"LATITUD_G": "28.03512", "LONGITUD_G": "-15.41631", "COD_ESTACI": "ES0873A", "NOMBRE": "JINÁMAR"}

    station = build_station("35016010", sampling_point=None, coordinate=coordinate)

    assert station["eea_code"] == "ES0873A"
    assert station["name"] == "JINÁMAR"
    assert station["altitude_m"] is None
    assert station["station_type"] is None
    assert station["station_area"] is None
    assert station["island"] == Island.GRAN_CANARIA


def test_build_station_falls_back_to_a_municipality_sibling():
    sibling = (27.897639, -15.445028)  # 35002001, AGÜIMES, in canarias_station_coordinates.csv

    station = build_station("35002003", sampling_point=None, coordinate=None, sibling_coordinate=sibling)

    assert (station["latitude"], station["longitude"]) == sibling
    assert station["eea_code"] is None
    assert station["name"] == "35002003"
    assert station["island"] == Island.GRAN_CANARIA


def test_build_station_uses_hardcoded_fallback_when_municipality_has_no_sibling_either():
    station = build_station("38024001", sampling_point=None, coordinate=None, sibling_coordinate=None)

    assert station["latitude"] == 28.65851
    assert station["longitude"] == -17.91821
    assert station["island"] == Island.LA_PALMA


def test_build_station_name_falls_back_to_eea_code_without_coordinates_csv():
    sampling_point = {
        "Latitude": "28.1",
        "Longitude": "-15.4",
        "Altitude": "10",
        "AirQualityStationEoICode": "ES9999A",
        "AirQualityStationType": "",
        "AirQualityStationArea": "",
    }

    station = build_station("35099999", sampling_point, coordinate=None)

    assert station["name"] == "ES9999A"
    assert station["station_type"] is None
    assert station["station_area"] is None
