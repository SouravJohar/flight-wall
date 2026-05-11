# ── Flight Tracker Configuration ─────────────────────────────────────────────
# All tunable settings in one place. Edit here to change behavior.

# ── ADS-B reception point ─────────────────────────────────────────────────────
# Latitude/longitude of the location to watch for nearby aircraft
ADSB_LAT    = 40.786336
ADSB_LON    = -73.991927
# Search radius in nautical miles
ADSB_RADIUS = 4 # default is 2

# ADS-B API endpoint template
ADSB_ENDPOINT = "https://api.airplanes.live/v2/point/{lat}/{lon}/{radius}"

# Aircraft category codes to include (A3=large, A4=heavy, A5=super-heavy)
# Full list: https://www.adsbexchange.com/emitter-category-descriptions/
AIRCRAFT_CATEGORIES = ["A3", "A4", "A5"]

# ── Cache ─────────────────────────────────────────────────────────────────────
# How long (in minutes) before a cached flight entry expires
CACHE_TTL_MINUTES = 5

# ── Worker ────────────────────────────────────────────────────────────────────
# How often (in seconds) to poll for new aircraft overhead
POLL_INTERVAL_SECONDS = 10

# ── Callsign resolution ───────────────────────────────────────────────────────
# When a regional/partner carrier operates under multiple mainline brands,
# try to deduce the correct flight number by checking FlightStats
DEDUCE_FLIGHT_NUM = True

# Airports used to filter plausible flights when deducing partner callsigns.
# Flights whose origin OR destination is in this list are considered nearby.
NEARBY_AIRPORTS = ["LGA", "JFK", "EWR"]

# ── FlightStats scraper ───────────────────────────────────────────────────────
FLIGHTSTATS_BASE_URL = (
    "https://www.flightstats.com/v2/flight-tracker/{airline}/{number}"
    "?year={year}&month={month}&date={date}"
)

FLIGHTSTATS_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept":                  "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language":         "en-US,en;q=0.9",
    "Accept-Encoding":         "gzip, deflate, br",
    "Connection":              "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest":          "document",
    "Sec-Fetch-Mode":          "navigate",
    "Sec-Fetch-Site":          "none",
    "Cache-Control":           "max-age=0",
}

# Timeout in seconds for each HTTP request to FlightStats
FLIGHTSTATS_REQUEST_TIMEOUT = 15
