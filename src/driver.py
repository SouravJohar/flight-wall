import json
import logging
import os
import tempfile
import time

import adsb
import callsign
import flightstats
from cachestore import cache_get, cache_put
from config import POLL_INTERVAL_SECONDS

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger(__name__)


def _flight_json_paths() -> list[str]:
    base_dir = os.path.dirname(__file__)

    return [
        os.path.join(base_dir, "flightwall", "dist", "flights.json"),
        os.path.join(base_dir, "flightwall", "public", "flights.json"),
    ]


def _atomic_write_json(path: str, payload: str) -> None:
    """Atomically write payload to path."""
    dest = os.path.abspath(path)

    os.makedirs(os.path.dirname(dest), exist_ok=True)

    fd, tmp = tempfile.mkstemp(
        dir=os.path.dirname(dest),
        suffix=".tmp",
    )

    try:
        with os.fdopen(fd, "w") as f:
            f.write(payload)

        os.replace(tmp, dest)

    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass

        raise


def _write_flights_payload(data: list[dict]) -> None:
    payload = json.dumps(data, indent=2)

    for path in _flight_json_paths():
        _atomic_write_json(path, payload)


def _build_flight_record(flight: dict) -> dict:
    eqpmt = ""
    try:
        eqpmt = " ".join(flight["equipment"].split(" ")[:2])[:16]
    except:
        pass
    return {
        "flightNumber": flight["flight"],
        "airline": flight["carrier"],
        "airlineIata": flight["flight"][:2].upper().strip(),
        "aircraft": eqpmt,
        "origin": flight["origin_airport_code"],
        "destination": flight["dest_airport_code"],
    }


def clear_display() -> None:
    _write_flights_payload([])


def show_display(flight: dict) -> None:
    print(flight)

    record = _build_flight_record(flight)

    _write_flights_payload([record])


def process_overhead_flights() -> None:
    """Fetch nearby aircraft, resolve flight info, and print each result."""
    aircraft_list = adsb.get_nearby_aircraft()

    if not aircraft_list:
        clear_display()
        return

    aircraft_to_display = aircraft_list[0]
    call_sign = aircraft_to_display.get("call_sign")

    if not call_sign:
        return

    info = cache_get(call_sign)

    if not info:
        flight_number = callsign.resolve_flight_number(call_sign)
        info = flightstats.get_flight_info(flight_number)

        if info:
            cache_put(call_sign, info)

    if info:
        show_display(info)


def _print_flight(info: dict) -> None:
    print(f"{info['carrier']} {info['flight']}")
    print(f"{info['origin_airport_code']} --> {info['dest_airport_code']}")
    print(info["equipment"])
    print("-" * 48 + "\n")


def run() -> None:
    """Poll for overhead flights on a fixed interval until interrupted."""
    logger.info(
        "Flight tracker started (poll interval: %ds)",
        POLL_INTERVAL_SECONDS,
    )

    while True:
        process_overhead_flights()
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    run()











# import logging
# import time

# import adsb
# import callsign
# import flightstats
# from cachestore import cache_get, cache_put
# from config import POLL_INTERVAL_SECONDS
# import os
# import json
# import tempfile

# logging.basicConfig(
#     level=logging.DEBUG,
#     format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
#     datefmt="%H:%M:%S",
# )
# logger = logging.getLogger(__name__)


# def clear_display():
#     path_dist = os.path.join(os.path.dirname(__file__), "flightwall", "dist", "flights.json")
#     path_public = os.path.join(os.path.dirname(__file__), "flightwall", "public", "flights.json")
#     payload = json.dumps([], indent=2)

#     # Atomic write: write to a sibling temp file then rename
#     dest = os.path.abspath(path_dist)
#     os.makedirs(os.path.dirname(dest), exist_ok=True)

#     fd, tmp = tempfile.mkstemp(dir=os.path.dirname(dest), suffix=".tmp")
#     try:
#         with os.fdopen(fd, "w") as f:
#             f.write(payload)
#         os.replace(tmp, dest)
#     except Exception:
#         try:
#             os.unlink(tmp)
#         except OSError:
#             pass
#         raise


#     # Atomic write: write to a sibling temp file then rename
#     dest = os.path.abspath(path_public)
#     os.makedirs(os.path.dirname(dest), exist_ok=True)

#     fd, tmp = tempfile.mkstemp(dir=os.path.dirname(dest), suffix=".tmp")
#     try:
#         with os.fdopen(fd, "w") as f:
#             f.write(payload)
#         os.replace(tmp, dest)
#     except Exception:
#         try:
#             os.unlink(tmp)
#         except OSError:
#             pass
#         raise

# def show_display(flight):
#     print(flight)
#     {'origin_airport_code': 'HPN', 'origin_airport_name': 'Westchester County', 'dest_airport_code': 'PBI', 'dest_airport_name': 'West Palm Beach', 'equipment': 'Airbus A320', 'flight': 'B61367', 'carrier': 'JetBlue Airways', 'date': '2026-05-01', 'source_url': 'https://www.flightstats.com/v2/flight-tracker/B6/1367?year=2026&month=05&date=01'}
#     record = {
#         "flightNumber": flight['flight'],
#         "airline":      flight['carrier'],
#         "airlineIata":  flight['flight'][:2].upper().strip(),
#         "aircraft":     " ".join(flight['equipment'].split(" ")[:2])[:16],
#         "origin":       flight["origin_airport_code"],
#         "destination":  flight["dest_airport_code"],
#     }
#     path_dist = os.path.join(os.path.dirname(__file__), "flightwall", "dist", "flights.json")
#     path_public = os.path.join(os.path.dirname(__file__), "flightwall", "public", "flights.json")
#     payload = json.dumps([record], indent=2)

#     # Atomic write: write to a sibling temp file then rename
#     dest = os.path.abspath(path_dist)
#     os.makedirs(os.path.dirname(dest), exist_ok=True)

#     fd, tmp = tempfile.mkstemp(dir=os.path.dirname(dest), suffix=".tmp")
#     try:
#         with os.fdopen(fd, "w") as f:
#             f.write(payload)
#         os.replace(tmp, dest)
#     except Exception:
#         try:
#             os.unlink(tmp)
#         except OSError:
#             pass
#         raise

#     # Atomic write: write to a sibling temp file then rename
#     dest = os.path.abspath(path_public)
#     os.makedirs(os.path.dirname(dest), exist_ok=True)

#     fd, tmp = tempfile.mkstemp(dir=os.path.dirname(dest), suffix=".tmp")
#     try:
#         with os.fdopen(fd, "w") as f:
#             f.write(payload)
#         os.replace(tmp, dest)
#     except Exception:
#         try:
#             os.unlink(tmp)
#         except OSError:
#             pass
#         raise




# def process_overhead_flights() -> None:
#     """Fetch nearby aircraft, resolve flight info, and print each result."""
#     aircraft_list = adsb.get_nearby_aircraft()

#     if len(aircraft_list) == 0:
#         clear_display()
#         return

#     aircraft_to_display = aircraft_list[0]
#     call_sign = aircraft_to_display.get("call_sign")
#     if call_sign:
#         info = cache_get(call_sign)
#         if not info:
#             flight_number = callsign.resolve_flight_number(call_sign)
#             info = flightstats.get_flight_info(flight_number)
#             if info:
#                 cache_put(call_sign, info)

#         if info:
#             show_display(info)






#     # for aircraft in aircraft_list:
#     #     call_sign = aircraft.get("call_sign")
#     #     print("heading", aircraft.get("nav_heading"))
#     #     # print(aircraft)
#     #     if not call_sign:
#     #         continue

#     #     info = cache_get(call_sign)

#     #     if not info:
#     #         flight_number = callsign.resolve_flight_number(call_sign)
#     #         info = flightstats.get_flight_info(flight_number)
#     #         if info:
#     #             cache_put(call_sign, info)

#     #     if info:
#     #         _print_flight(info)


# def _print_flight(info: dict) -> None:
#     print(f"{info['carrier']} {info['flight']}")
#     print(f"{info['origin_airport_code']} --> {info['dest_airport_code']}")
#     print(info["equipment"])
#     print("-" * 48 + "\n")


# def run() -> None:
#     """Poll for overhead flights on a fixed interval until interrupted."""
#     logger.info("Flight tracker started (poll interval: %ds)", POLL_INTERVAL_SECONDS)
#     while True:
#         process_overhead_flights()
#         time.sleep(POLL_INTERVAL_SECONDS)


# if __name__ == "__main__":
#     run()
