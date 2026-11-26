import json
from contextlib import contextmanager
from unittest.mock import patch
from urllib.error import URLError

from calima_api.ingestion.altitude import fetch_elevations


@contextmanager
def _fake_response(elevations: list[float]):
    class Response:
        def read(self):
            return json.dumps({"results": [{"elevation": e} for e in elevations]}).encode()

    yield Response()


def test_fetch_elevations_maps_results_back_to_station_codes():
    coordinates = [("35016014", 28.1033, -15.4228), ("35022003", 27.8155, -15.4276)]

    with patch("calima_api.ingestion.altitude.urllib.request.urlopen") as urlopen:
        urlopen.side_effect = lambda *a, **kw: _fake_response([117.96, 14.79])

        elevations = fetch_elevations(coordinates)

    assert elevations == {"35016014": 117.96, "35022003": 14.79}


def test_fetch_elevations_returns_empty_dict_for_no_coordinates():
    assert fetch_elevations([]) == {}


def test_fetch_elevations_retries_then_succeeds():
    coordinates = [("35016014", 28.1033, -15.4228)]
    attempts = [URLError("timed out"), _fake_response([117.96])]

    with (
        patch("calima_api.ingestion.altitude.urllib.request.urlopen") as urlopen,
        patch("calima_api.ingestion.altitude.time.sleep"),
    ):

        def side_effect(*args, **kwargs):
            result = attempts.pop(0)
            if isinstance(result, Exception):
                raise result
            return result

        urlopen.side_effect = side_effect

        elevations = fetch_elevations(coordinates)

    assert elevations == {"35016014": 117.96}


def test_fetch_elevations_raises_after_exhausting_retries():
    coordinates = [("35016014", 28.1033, -15.4228)]

    with (
        patch("calima_api.ingestion.altitude.urllib.request.urlopen") as urlopen,
        patch("calima_api.ingestion.altitude.time.sleep"),
    ):
        urlopen.side_effect = URLError("timed out")

        try:
            fetch_elevations(coordinates)
            raised = False
        except RuntimeError:
            raised = True

    assert raised
