"""FlightStats scraper — fetches origin, destination, carrier, and aircraft
type for a given IATA flight number.

Usage (CLI):
    python flightstats.py AA100
    python flightstats.py AA100 --year 2026 --month 04 --date 12
    python flightstats.py --flight DL400 --year 2026 --month 04 --date 12

Requirements:
    pip install requests beautifulsoup4 lxml
"""

import argparse
import json
import logging
import re
import sys
from datetime import date as dt_date
from typing import Optional

import requests
from bs4 import BeautifulSoup

from config import FLIGHTSTATS_BASE_URL, FLIGHTSTATS_HEADERS, FLIGHTSTATS_REQUEST_TIMEOUT

logger = logging.getLogger(__name__)

# ── Airline name table ────────────────────────────────────────────────────────

# IATA code → full carrier name (extend as needed)
AIRLINE_NAMES: dict[str, str] = {

    # ── US Carriers ───────────────────────────────────────────────────────
    "CV": "Cargo Lux",
    "AA": "American Airlines",
    "DL": "Delta Air Lines",
    "UA": "United Airlines",
    "WN": "Southwest Airlines",
    "B6": "JetBlue Airways",
    "AS": "Alaska Airlines",
    "NK": "Spirit Airlines",
    "F9": "Frontier Airlines",
    "G4": "Allegiant Air",
    "HA": "Hawaiian Airlines",
    "SY": "Sun Country Airlines",
    "3M": "Silver Airways",
    "9K": "Cape Air",
    "C5": "CommutAir",
    "OH": "PSA Airlines",
    "OO": "SkyWest Airlines",
    "MQ": "Envoy Air",
    "YX": "Midwest Express / Republic Airways",
    "PT": "Piedmont Airlines",
    "9E": "Endeavor Air",

    # ── Canada ────────────────────────────────────────────────────────────
    "AC": "Air Canada",
    "PD": "Porter Airlines",
    "WS": "WestJet",
    "TS": "Air Transat",
    "QK": "Jazz Aviation",

    # ── Latin America & Caribbean ─────────────────────────────────────────
    "AM": "Aeromexico",
    "MX": "Breeze Airways",
    "VB": "VivaAerobus",
    "Y4": "Volaris",
    "LA": "LATAM Airlines",
    "4M": "LATAM Argentina",
    "JJ": "LATAM Brasil",
    "AV": "Avianca",
    "CM": "Copa Airlines",
    "AD": "Azul Brazilian Airlines",
    "G3": "Gol Transportes Aéreos",
    "BF": "French Bee",
    "8J": "Eco Jet",
    "P9": "Peruvian Airlines",

    # ── Europe ────────────────────────────────────────────────────────────
    "BA": "British Airways",
    "LH": "Lufthansa",
    "AF": "Air France",
    "KL": "KLM",
    "IB": "Iberia",
    "AZ": "ITA Airways",
    "SK": "Scandinavian Airlines (SAS)",
    "AY": "Finnair",
    "LX": "Swiss International Air Lines",
    "OS": "Austrian Airlines",
    "SN": "Brussels Airlines",
    "TP": "TAP Air Portugal",
    "U2": "easyJet",
    "FR": "Ryanair",
    "VY": "Vueling",
    "W6": "Wizz Air",
    "PC": "Pegasus Airlines",
    "TK": "Turkish Airlines",
    "PS": "Ukraine International Airlines",
    "LO": "LOT Polish Airlines",
    "OK": "Czech Airlines",
    "RO": "TAROM",
    "A3": "Aegean Airlines",
    "VK": "Viking Airlines",
    "DY": "Norwegian Air Shuttle",
    "EI": "Aer Lingus",
    "LS": "Jet2",
    "MT": "Thomas Cook Airlines",
    "TOM": "TUI Airways",
    "BE": "Flybe",

    # ── Middle East & Africa ──────────────────────────────────────────────
    "EK": "Emirates",
    "QR": "Qatar Airways",
    "EY": "Etihad Airways",
    "GF": "Gulf Air",
    "KU": "Kuwait Airways",
    "ME": "Middle East Airlines",
    "RJ": "Royal Jordanian",
    "MS": "EgyptAir",
    "ET": "Ethiopian Airlines",
    "AT": "Royal Air Maroc",
    "SA": "South African Airways",
    "KQ": "Kenya Airways",
    "WB": "RwandAir",
    "FZ": "flydubai",
    "G9": "Air Arabia",
    "XY": "flynas",
    "SV": "Saudia",
    "IA": "Iraqi Airways",

    # ── Asia & Pacific ────────────────────────────────────────────────────
    "SQ": "Singapore Airlines",
    "CX": "Cathay Pacific",
    "QF": "Qantas",
    "NZ": "Air New Zealand",
    "JL": "Japan Airlines",
    "NH": "All Nippon Airways (ANA)",
    "KE": "Korean Air",
    "OZ": "Asiana Airlines",
    "CI": "China Airlines",
    "BR": "EVA Air",
    "MH": "Malaysia Airlines",
    "TG": "Thai Airways",
    "GA": "Garuda Indonesia",
    "PR": "Philippine Airlines",
    "VN": "Vietnam Airlines",
    "AI": "Air India",
    "6E": "IndiGo",
    "SG": "SpiceJet",
    "UK": "Vistara",
    "PK": "Pakistan International Airlines",
    "UL": "SriLankan Airlines",
    "BG": "Biman Bangladesh Airlines",
    "OU": "Croatia Airlines",
    "MU": "China Eastern Airlines",
    "CA": "Air China",
    "CZ": "China Southern Airlines",
    "HU": "Hainan Airlines",
    "3U": "Sichuan Airlines",
    "ZH": "Shenzhen Airlines",
    "FM": "Shanghai Airlines",
    "SC": "Shandong Airlines",
    "TR": "Scoot",
    "AK": "AirAsia",
    "FD": "Thai AirAsia",
    "QZ": "AirAsia Indonesia",
    "VJ": "VietJet Air",
    "OD": "Batik Air Malaysia",
    "JQ": "Jetstar Airways",
    "3K": "Jetstar Asia",
    "GK": "Jetstar Japan",
    "VA": "Virgin Australia",

    # ── Russia & Central Asia ─────────────────────────────────────────────
    "SU": "Aeroflot",
    "S7": "Siberia Airlines (S7)",
    "U6": "Ural Airlines",
    "DP": "Pobeda Airlines",
    "KC": "Air Astana",
    "HY": "Uzbekistan Airways",
}


# ── Public API ────────────────────────────────────────────────────────────────

def get_flight_info(
    flight_input: str,
    year: Optional[int] = None,
    month: Optional[int] = None,
    day: Optional[int] = None,
) -> Optional[dict]:
    """Fetch flight info for *flight_input* (e.g. ``"AA100"``) on a given date.

    Defaults to today when no date is supplied.  Returns ``None`` on any
    error, including unrecognised flight numbers and network failures.
    """
    if not flight_input:
        return None

    try:
        airline_code, flight_number = _parse_flight_input(flight_input)

        today = dt_date.today()
        year  = year  or today.year
        month = month or today.month
        day   = day   or today.day

        soup, url = _fetch_flight_page(airline_code, flight_number, year, month, day)

        info = _extract_flight_info(soup)
        info["flight"]     = f"{airline_code}{flight_number}"
        info["carrier"]    = AIRLINE_NAMES[airline_code]
        info["date"]       = f"{year}-{month:02d}-{day:02d}"
        info["source_url"] = url

        return info
    except Exception:
        logger.exception("Failed to retrieve flight info for '%s'", flight_input)
        return None


# ── Scraping helpers ──────────────────────────────────────────────────────────

def _fetch_flight_page(
    airline: str,
    number: str,
    year: int,
    month: int,
    day: int,
) -> tuple[BeautifulSoup, str]:
    """Download and parse the FlightStats tracker page for a specific date."""
    url = FLIGHTSTATS_BASE_URL.format(
        airline=airline,
        number=number,
        year=year,
        month=f"{month:02d}",
        date=f"{day:02d}",
    )
    session = requests.Session()
    # Seed the session with cookies from the homepage before the tracker page.
    session.get("https://www.flightstats.com", headers=FLIGHTSTATS_HEADERS, timeout=FLIGHTSTATS_REQUEST_TIMEOUT)
    response = session.get(url, headers=FLIGHTSTATS_HEADERS, timeout=FLIGHTSTATS_REQUEST_TIMEOUT)
    response.raise_for_status()
    return BeautifulSoup(response.text, "lxml"), url


def _extract_flight_info(soup: BeautifulSoup) -> dict:
    """Try the embedded JSON first; fall back to plain-text extraction."""
    info = _parse_info_from_script(soup)

    if not all(v is not None for v in info.values()):
        text_info = _parse_info_from_text(soup.get_text(" ", strip=True))
        for key, value in info.items():
            if value is None:
                info[key] = text_info[key]

    return info


def _parse_info_from_script(soup: BeautifulSoup) -> dict:
    """Extract flight info from the embedded ``__NEXT_DATA__`` JSON blob."""
    origin_code = origin_name = dest_code = dest_name = equipment = None

    raw_json = _extract_next_data_json(soup)
    if raw_json:
        try:
            flight_data = raw_json["props"]["initialState"]["flightTracker"]["flight"]
            if flight_data:
                departure = (
                    flight_data.get("departure")
                    or flight_data.get("departureAirport")
                    or {}
                )
                arrival = (
                    flight_data.get("arrival")
                    or flight_data.get("arrivalAirport")
                    or {}
                )

                # Some response shapes nest airport info one level deeper.
                if isinstance(departure.get("airport"), dict):
                    departure = departure["airport"]
                if isinstance(arrival.get("airport"), dict):
                    arrival = arrival["airport"]

                origin_code, origin_name = _extract_airport_fields(departure)
                dest_code, dest_name     = _extract_airport_fields(arrival)
                equipment = flight_data["additionalFlightInfo"]["equipment"]["name"]
        except Exception:
            pass  # Fall through to text-based extraction

    return {
        "origin_airport_code": origin_code,
        "origin_airport_name": origin_name,
        "dest_airport_code":   dest_code,
        "dest_airport_name":   dest_name,
        "equipment":           equipment,
    }


def _extract_next_data_json(soup: BeautifulSoup) -> Optional[dict]:
    """Find and decode the ``__NEXT_DATA__`` script tag, if present."""
    for tag in soup.find_all("script"):
        if tag.text.startswith("__NEXT_DATA__"):
            start = tag.text.index("{", tag.text.index("__NEXT_DATA__"))
            data, _ = json.JSONDecoder().raw_decode(tag.text, start)
            return data
    return None


def _parse_info_from_text(text: str) -> dict:
    """Best-effort plain-text fallback parser for origin, destination, and aircraft."""
    origin_code, origin_name, dest_code, dest_name = _extract_airports_from_text(text)
    equipment = _extract_equipment_from_text(text)

    return {
        "origin_airport_code": origin_code,
        "origin_airport_name": origin_name,
        "dest_airport_code":   dest_code,
        "dest_airport_name":   dest_name,
        "equipment":           equipment,
    }


def _extract_airports_from_text(text: str) -> tuple[Optional[str], ...]:
    """Parse origin and destination airport codes from page text."""
    try:
        anchor = "Flight Tracker Flight Status"
        anchor_idx = text.find(anchor)
        if anchor_idx > -1:
            text = text[anchor_idx + len(anchor):].strip()

        # Truncate at the first flight-status word to avoid false matches.
        status_words = ["Departed", "Scheduled", "Arrived"]
        cutoff = min(
            (text.find(w) for w in status_words if text.find(w) > -1),
            default=None,
        )
        if cutoff:
            text = text[:cutoff].strip()

        matches = re.findall(r"\b([A-Z]{3})\b\s+([A-Za-z\s]+?)(?=\s+[A-Z]{3}\b|$)", text)
        if len(matches) < 2:
            return None, None, None, None

        origin_code, origin_name   = matches[0][0], matches[0][1].strip()
        dest_code,   dest_name     = matches[1][0], matches[1][1].strip()
        return origin_code, origin_name, dest_code, dest_name

    except Exception:
        return None, None, None, None


def _extract_equipment_from_text(text: str) -> Optional[str]:
    """Parse aircraft type from page text."""
    try:
        anchor = "Aircraft Equipment Code"
        anchor_idx = text.find(anchor)
        if anchor_idx > -1:
            text = text[anchor_idx + len(anchor): anchor_idx + len(anchor) + 80].strip()

        match = re.search(
            r"(Airbus\s+A\d{3}(?:neo)?|Boeing\s+\d{3}[A-Z\-\d]*|"
            r"Embraer\s+[A-Z]?\d+|Bombardier\s+\w+|"
            r"Mitsubishi\s+(?:SpaceJet|MRJ)\s*\w*|"
            r"\bA\d{3}(?:neo)?\b|\bB\d{3}\b|\bMRJ\d+\b|\bM\d{2,3}\b)",
            text,
            re.IGNORECASE,
        )
        return match.group(1) if match else None

    except Exception:
        return None


def _extract_airport_fields(airport: dict) -> tuple[Optional[str], Optional[str]]:
    """Pull (iata_code, city_name) from an airport dict, trying multiple key names."""
    code = airport.get("iata") or airport.get("fs") or airport.get("code") or airport.get("icao")
    name = airport.get("city") or airport.get("name") or airport.get("municipalityName")
    return code, name


def _parse_flight_input(raw: str) -> tuple[str, str]:
    """Split a raw flight string (e.g. ``"AA100"``) into (airline_code, number).

    Uses longest-prefix matching against known IATA codes.
    Raises ``ValueError`` if the input doesn't match any known airline.
    """
    raw = raw.strip().upper().replace(" ", "")

    for code in sorted(AIRLINE_NAMES.keys(), key=len, reverse=True):
        if raw.startswith(code):
            number = raw[len(code):]
            if number.isdigit() and number:
                return code, number

    raise ValueError(
        f"Unrecognised flight format: '{raw}'. "
        "Expected IATA code + number, e.g. 'AA100' or 'B6372'."
    )


# ── CLI ───────────────────────────────────────────────────────────────────────

def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scrape flight info (origin, destination, airline, aircraft) from FlightStats.com"
    )
    parser.add_argument(
        "flight",
        nargs="?",
        help="Flight number, e.g. AA100, UA23, DL400",
    )
    parser.add_argument(
        "--flight", "-f",
        dest="flight_flag",
        help="Alternative flag form: --flight AA100",
    )
    parser.add_argument(
        "--year", "-y",
        type=int,
        help="4-digit year, e.g. 2026 (default: today)",
    )
    parser.add_argument(
        "--month", "-m",
        type=int,
        choices=range(1, 13),
        metavar="MONTH (1-12)",
        help="Month as a number 1–12 (default: today)",
    )
    parser.add_argument(
        "--date", "-d",
        type=int,
        choices=range(1, 32),
        metavar="DATE (1-31)",
        help="Day of the month 1–31 (default: today)",
    )
    return parser


def main() -> None:
    parser = _build_arg_parser()
    args = parser.parse_args()

    raw = args.flight or args.flight_flag
    if not raw:
        parser.print_help()
        sys.exit(1)

    try:
        info = get_flight_info(raw, year=args.year, month=args.month, day=args.date)
    except ValueError as exc:
        print(f"\n[Input Error] {exc}")
        sys.exit(1)
    except requests.HTTPError as exc:
        print(f"\n[HTTP Error] {exc}")
        print("  FlightStats may have blocked the request or the flight doesn't exist.")
        sys.exit(1)
    except requests.RequestException as exc:
        print(f"\n[Network Error] {exc}")
        sys.exit(1)

    if info:
        print(info)


if __name__ == "__main__":
    main()
