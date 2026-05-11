"""Callsign resolution: converts ADS-B ICAO callsigns to IATA flight numbers.

ICAO callsigns (e.g. ``AAL100``) are the 3-letter operator codes broadcast
by aircraft.  This module maps them to the public-facing IATA flight numbers
(e.g. ``AA100``) that passengers and flight-tracking sites use.

Regional/partner carriers (e.g. SkyWest operating as United Express) require
an extra lookup step: we query FlightStats for each possible partner and keep
the flight whose origin or destination is a nearby airport.
"""

import logging
from typing import Optional

import flightstats
from config import DEDUCE_FLIGHT_NUM, NEARBY_AIRPORTS

logger = logging.getLogger(__name__)

# ── Airline code tables ───────────────────────────────────────────────────────

# ICAO (3-letter) → IATA (2-letter) direct mappings.
# All codes verified against Airhex, airlinecodes.info, and Wikipedia.
ICAO_TO_IATA: dict[str, str] = {

    # ── US Carriers ───────────────────────────────────────────────────────
    "CLX": "CV",  # Cargolux
    "AAL": "AA",  # American Airlines
    "DAL": "DL",  # Delta Air Lines
    "UAL": "UA",  # United Airlines
    "SWA": "WN",  # Southwest Airlines
    "JBU": "B6",  # JetBlue Airways
    "ASA": "AS",  # Alaska Airlines
    "NKS": "NK",  # Spirit Airlines
    "FFT": "F9",  # Frontier Airlines
    "AAY": "G4",  # Allegiant Air
    "HAL": "HA",  # Hawaiian Airlines
    "SCX": "SY",  # Sun Country Airlines
    "SIL": "3M",  # Silver Airways
    "KAP": "9K",  # Cape Air
    "MXY": "MX",  # Breeze Airways

    # ── Canada ────────────────────────────────────────────────────────────
    "ACA": "AC",  # Air Canada
    "POE": "PD",  # Porter Airlines
    "WJA": "WS",  # WestJet
    "TSC": "TS",  # Air Transat

    # ── Latin America & Caribbean ─────────────────────────────────────────
    "AMX": "AM",  # Aeromexico
    "VOI": "Y4",  # Volaris
    "VIV": "VB",  # VivaAerobus
    "LAN": "LA",  # LATAM Airlines
    "LPE": "4M",  # LATAM Argentina
    "TAM": "JJ",  # LATAM Brasil
    "AVA": "AV",  # Avianca
    "CMP": "CM",  # Copa Airlines
    "AZU": "AD",  # Azul Brazilian Airlines
    "GLO": "G3",  # Gol Transportes Aéreos
    "FBU": "BF",  # French Bee
    "ECO": "8J",  # EcoJet
    "PVN": "P9",  # Peruvian Airlines

    # ── Europe ────────────────────────────────────────────────────────────
    "BAW": "BA",  # British Airways
    "DLH": "LH",  # Lufthansa
    "AFR": "AF",  # Air France
    "KLM": "KL",  # KLM
    "IBE": "IB",  # Iberia
    "ITY": "AZ",  # ITA Airways
    "SAS": "SK",  # Scandinavian Airlines
    "FIN": "AY",  # Finnair
    "SWR": "LX",  # Swiss International Air Lines
    "AUA": "OS",  # Austrian Airlines
    "BEL": "SN",  # Brussels Airlines
    "TAP": "TP",  # TAP Air Portugal
    "EZY": "U2",  # easyJet
    "RYR": "FR",  # Ryanair
    "VLG": "VY",  # Vueling
    "WZZ": "W6",  # Wizz Air
    "PGT": "PC",  # Pegasus Airlines
    "THY": "TK",  # Turkish Airlines
    "LOT": "LO",  # LOT Polish Airlines
    "ROT": "RO",  # TAROM
    "AEE": "A3",  # Aegean Airlines
    "VIK": "VK",  # Viking Airlines
    "NAX": "DY",  # Norwegian Air Shuttle
    "EIN": "EI",  # Aer Lingus
    "EXS": "LS",  # Jet2
    "TCX": "MT",  # Thomas Cook Airlines
    "TOM": "BY",  # TUI Airways  ← IATA is BY, not TOM (TOM is the ICAO)
    "BEE": "BE",  # Flybe (no longer operating)

    # ── Middle East & Africa ──────────────────────────────────────────────
    "UAE": "EK",  # Emirates
    "QTR": "QR",  # Qatar Airways
    "ETD": "EY",  # Etihad Airways
    "GFA": "GF",  # Gulf Air
    "KAC": "KU",  # Kuwait Airways
    "MEA": "ME",  # Middle East Airlines
    "RJA": "RJ",  # Royal Jordanian
    "MSR": "MS",  # EgyptAir
    "ETH": "ET",  # Ethiopian Airlines
    "RAM": "AT",  # Royal Air Maroc
    "SAA": "SA",  # South African Airways
    "KQA": "KQ",  # Kenya Airways
    "RWD": "WB",  # RwandAir
    "FDB": "FZ",  # flydubai
    "ABY": "G9",  # Air Arabia
    "KNE": "XY",  # flynas
    "SVA": "SV",  # Saudia
    "IAW": "IA",  # Iraqi Airways

    # ── Asia & Pacific ────────────────────────────────────────────────────
    "SIA": "SQ",  # Singapore Airlines
    "CPA": "CX",  # Cathay Pacific
    "QFA": "QF",  # Qantas
    "ANZ": "NZ",  # Air New Zealand
    "JAL": "JL",  # Japan Airlines
    "ANA": "NH",  # All Nippon Airways
    "KAL": "KE",  # Korean Air
    "AAR": "OZ",  # Asiana Airlines
    "CAL": "CI",  # China Airlines
    "EVA": "BR",  # EVA Air
    "MAS": "MH",  # Malaysia Airlines
    "THA": "TG",  # Thai Airways
    "GIA": "GA",  # Garuda Indonesia
    "PAL": "PR",  # Philippine Airlines
    "HVN": "VN",  # Vietnam Airlines
    "AIC": "AI",  # Air India
    "IGO": "6E",  # IndiGo
    "SEJ": "SG",  # SpiceJet
    "VTI": "UK",  # Vistara
    "PIA": "PK",  # Pakistan International Airlines
    "ALK": "UL",  # SriLankan Airlines
    "BBC": "BG",  # Biman Bangladesh Airlines
    "CES": "MU",  # China Eastern Airlines
    "CCA": "CA",  # Air China
    "CSN": "CZ",  # China Southern Airlines
    "CHH": "HU",  # Hainan Airlines
    "CSC": "3U",  # Sichuan Airlines
    "CSZ": "ZH",  # Shenzhen Airlines
    "CSH": "FM",  # Shanghai Airlines
    "CDG": "SC",  # Shandong Airlines
    "TGW": "TR",  # Scoot
    "AXM": "AK",  # AirAsia
    "AIQ": "FD",  # Thai AirAsia
    "AWQ": "QZ",  # AirAsia Indonesia
    "VJC": "VJ",  # VietJet Air
    "MXD": "OD",  # Batik Air Malaysia
    "JST": "JQ",  # Jetstar Airways
    "JSA": "3K",  # Jetstar Asia
    "JJP": "GK",  # Jetstar Japan
    "VOZ": "VA",  # Virgin Australia

    # ── Russia & Central Asia ─────────────────────────────────────────────
    "AFL": "SU",  # Aeroflot
    "SBI": "S7",  # Siberia Airlines (S7)
    "SVR": "U6",  # Ural Airlines
    "POB": "DP",  # Pobeda Airlines
    "KZR": "KC",  # Air Astana
    "UZB": "HY",  # Uzbekistan Airways
}

# Regional carriers that operate flights on behalf of one or more mainline
# partners.  When a callsign belongs to one of these, we resolve the correct
# partner flight number via FlightStats (if DEDUCE_FLIGHT_NUM is enabled).
PARTNERED_AIRLINES: dict[str, dict] = {
    "RPA": {"name": "Republic Airways",  "partners_with": ["AA", "DL", "UA"]},
    "ENY": {"name": "Envoy Air",         "partners_with": ["AA"]},
    "SKW": {"name": "SkyWest Airlines",  "partners_with": ["AA", "DL", "UA", "AS"]},
    "ASH": {"name": "Mesa Airlines",     "partners_with": ["UA", "AA"]},
    "QXE": {"name": "Horizon Air",       "partners_with": ["AS"]},
    "UCA": {"name": "CommutAir",         "partners_with": ["UA"]},
    "AWI": {"name": "Air Wisconsin",     "partners_with": ["AA"]},
    "GJS": {"name": "GoJet Airlines",    "partners_with": ["UA", "DL"]},
    "JZA": {"name": "Jazz Aviation",     "partners_with": ["AC"]},
    "PSA": {"name": "PSA Airlines",      "partners_with": ["AA"]},
    "PDT": {"name": "Piedmont Airlines", "partners_with": ["AA"]},
    "EDV": {"name": "Endeavor Air",      "partners_with": ["DL"]},
}


# ── Public API ────────────────────────────────────────────────────────────────

def resolve_flight_number(callsign: str) -> Optional[str]:
    """Convert an ADS-B ICAO callsign to a public IATA flight number.

    Resolution order:
      1. Direct ICAO → IATA table lookup  (e.g. ``AAL`` → ``AA100``)
      2. Single-partner regional carrier  (e.g. ``ENY`` → ``AA100``)
      3. Multi-partner deduction via FlightStats (requires DEDUCE_FLIGHT_NUM)

    Returns ``None`` if the callsign cannot be resolved.
    """
    icao_prefix = callsign.strip().upper()[:3]
    flight_number = callsign.strip().upper()[3:]

    # 1. Direct mapping
    if iata_prefix := ICAO_TO_IATA.get(icao_prefix):
        return f"{iata_prefix}{flight_number}"

    # 2 & 3. Regional/partner carrier
    if partner_info := PARTNERED_AIRLINES.get(icao_prefix):
        partners = partner_info["partners_with"]
        if len(partners) == 1:
            return f"{partners[0]}{flight_number}"
        if DEDUCE_FLIGHT_NUM:
            return _deduce_partner_flight(
                flight_number=flight_number,
                partners=partners,
                nearby_airports=NEARBY_AIRPORTS,
            )

    return None


# ── Internal helpers ──────────────────────────────────────────────────────────

def _deduce_partner_flight(
    flight_number: str,
    partners: list[str],
    nearby_airports: list[str],
) -> Optional[str]:
    """Query FlightStats for each partner and return the one whose route
    passes through a nearby airport.  Returns ``None`` if the result is
    ambiguous or no match is found.
    """
    candidates = []

    for airline_code in partners:
        candidate = f"{airline_code}{flight_number}"
        flight_info = flightstats.get_flight_info(candidate)

        if not flight_info:
            logger.debug("No flight info for %s", candidate)
            continue

        origin = flight_info.get("origin_airport_code")
        dest = flight_info.get("dest_airport_code")

        if not origin or not dest:
            logger.debug("Missing origin/dest for %s — skipping", candidate)
            continue

        if _serves_nearby_airport(origin=origin, destination=dest, nearby=nearby_airports):
            logger.debug("%s matched — origin=%s, dest=%s", candidate, origin, dest)
            candidates.append(candidate)
        else:
            logger.debug("%s found but no nearby airport — origin=%s, dest=%s", candidate, origin, dest)

    if len(candidates) == 1:
        logger.debug("Deduced flight number: %s", candidates[0])
        return candidates[0]

    if not candidates:
        logger.debug("No partner match for flight_number=%s, partners=%s", flight_number, partners)
    else:
        logger.debug("Ambiguous — multiple matches: %s", candidates)

    return None


def _serves_nearby_airport(origin: str, destination: str, nearby: list[str]) -> bool:
    return origin in nearby or destination in nearby
