import logging

import requests

from config import ADSB_ENDPOINT, ADSB_LAT, ADSB_LON, ADSB_RADIUS, AIRCRAFT_CATEGORIES

logger = logging.getLogger(__name__)


def get_nearby_aircraft(
    lat: float = ADSB_LAT,
    lon: float = ADSB_LON,
    radius: int = ADSB_RADIUS,
    apply_filters: bool = True,
) -> list[dict]:
    """Fetch aircraft currently within *radius* nautical miles of (lat, lon).

    Returns a list of aircraft dicts, each guaranteed to have ``call_sign``
    and ``registration`` keys.  Returns an empty list on any network error.
    """
    try:
        url = ADSB_ENDPOINT.format(lat=lat, lon=lon, radius=radius)
        response = requests.get(url)
        response.raise_for_status()
        aircraft = response.json().get("ac", [])
        return _filter_aircraft(aircraft) if apply_filters else aircraft
    except Exception:
        logger.exception("Failed to fetch aircraft from ADS-B endpoint")
        return []


def _filter_aircraft(aircraft: list[dict]) -> list[dict]:
    """Keep only large commercial aircraft and normalise key names."""
    results = []
    for ac in aircraft:
        if ac.get("category") not in AIRCRAFT_CATEGORIES:
            continue
        ac["call_sign"] = ac.get("flight", "").strip()
        ac["registration"] = ac.get("r", "").strip()
        results.append(ac)
    return results
