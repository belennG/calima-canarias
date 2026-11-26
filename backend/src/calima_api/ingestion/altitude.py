"""Fills in stations.altitude_m from Open-Elevation, for stations whose local
metadata files don't have an altitude at all (see docs/decisions.md).

Open-Elevation needs no API key and takes a batch of coordinates in one request,
so all missing stations are looked up in a single call.
"""

import json
import logging
import time
import urllib.request
from urllib.error import URLError

OPEN_ELEVATION_URL = "https://api.open-elevation.com/api/v1/lookup"
MAX_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 2

logger = logging.getLogger(__name__)


def fetch_elevations(coordinates: list[tuple[str, float, float]]) -> dict[str, float]:
    """coordinates: (station_code, latitude, longitude). Returns station_code -> elevation_m.

    Retries on network errors, since this is a live call to an external service.
    """
    if not coordinates:
        return {}

    payload = {
        "locations": [{"latitude": latitude, "longitude": longitude} for _, latitude, longitude in coordinates]
    }
    request = urllib.request.Request(
        OPEN_ELEVATION_URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                results = json.load(response)["results"]
            return {
                station_code: result["elevation"] for (station_code, _, _), result in zip(coordinates, results)
            }
        except URLError as error:
            last_error = error
            logger.warning("Open-Elevation request failed (attempt %d/%d): %s", attempt, MAX_ATTEMPTS, error)
            time.sleep(RETRY_DELAY_SECONDS)

    raise RuntimeError(f"Open-Elevation request failed after {MAX_ATTEMPTS} attempts") from last_error
