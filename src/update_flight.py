#!/usr/bin/env python3
"""
Write a flight record to flights.json for FlightWall.

As a module:
    from update_flight import update_flight

    update_flight(
        flight_number = "AA 99",
        airline       = "American Airlines",
        airline_iata  = "AA",
        aircraft      = "Boeing 737-8",
        origin        = "LAX",
        destination   = "JFK",
        path          = "/home/pi/flightwall/dist/flights.json",  # optional
    )

From the command line:
    python update_flight.py \\
        --flight-number "AA 99" --airline "American Airlines" --airline-iata AA \\
        --aircraft "Boeing 737-8" --origin LAX --destination JFK
"""

import argparse
import json
import os
import tempfile

DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "dist", "flights.json")


def update_flight(
    *,
    flight_number: str,
    airline:       str,
    airline_iata:  str,
    aircraft:      str,
    origin:        str,
    destination:   str,
    path:          str = DEFAULT_PATH,
) -> dict:
    """
    Write a single flight record to flights.json and return the written record.

    The write is atomic — a temp file is written then renamed, so the display
    never reads a partial file.

    Args:
        flight_number: Flight designator, e.g. "AA 99"
        airline:       Full airline name, e.g. "American Airlines"
        airline_iata:  Two-letter IATA code used to load the logo, e.g. "AA"
        aircraft:      Aircraft type, e.g. "Boeing 737-8" or "B738"
        origin:        Origin IATA airport code, e.g. "LAX"
        destination:   Destination IATA airport code, e.g. "JFK"
        path:          Absolute or relative path to flights.json

    Returns:
        The record dict that was written.
    """
    record = {
        "flightNumber": flight_number.strip(),
        "airline":      airline.strip(),
        "airlineIata":  airline_iata.upper().strip(),
        "aircraft":     aircraft.strip(),
        "origin":       origin.upper().strip(),
        "destination":  destination.upper().strip(),
    }

    payload = json.dumps([record], indent=2)

    # Atomic write: write to a sibling temp file then rename
    dest = os.path.abspath(path)
    os.makedirs(os.path.dirname(dest), exist_ok=True)

    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(dest), suffix=".tmp")
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

    return record


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Write a flight record to flights.json for FlightWall.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--flight-number", required=True, help='e.g. "AA 99"')
    p.add_argument("--airline",       required=True, help='e.g. "American Airlines"')
    p.add_argument("--airline-iata",  required=True, help='e.g. "AA"')
    p.add_argument("--aircraft",      required=True, help='e.g. "Boeing 737-8"')
    p.add_argument("--origin",        required=True, help='e.g. "LAX"')
    p.add_argument("--destination",   required=True, help='e.g. "JFK"')
    p.add_argument(
        "--path",
        default=DEFAULT_PATH,
        help="Path to flights.json",
    )
    return p


if __name__ == "__main__":
    args = _build_parser().parse_args()
    record = update_flight(
        flight_number = args.flight_number,
        airline       = args.airline,
        airline_iata  = args.airline_iata,
        aircraft      = args.aircraft,
        origin        = args.origin,
        destination   = args.destination,
        path          = args.path,
    )
    print(f"Written to {args.path}:")
    print(json.dumps(record, indent=2))
