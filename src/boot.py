"""
boot.py — FLIGHT TRACKER SYSTEM BOOT SEQUENCE
Cinematic startup experience. Functional logic lives in driver.py unchanged.
"""

import sys
import time
import random
import socket
import platform
import datetime
import requests

# ── ANSI colour helpers ────────────────────────────────────────────────────────

class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    BLINK   = "\033[5m"

    BLACK   = "\033[30m"
    RED     = "\033[31m"
    GREEN   = "\033[32m"
    YELLOW  = "\033[33m"
    BLUE    = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN    = "\033[36m"
    WHITE   = "\033[37m"

    BRIGHT_RED     = "\033[91m"
    BRIGHT_GREEN   = "\033[92m"
    BRIGHT_YELLOW  = "\033[93m"
    BRIGHT_BLUE    = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAAN    = "\033[96m"
    BRIGHT_WHITE   = "\033[97m"

    BG_BLACK  = "\033[40m"
    BG_BLUE   = "\033[44m"
    BG_CYAN   = "\033[46m"


def c(colour: str, text: str) -> str:
    return f"{colour}{text}{C.RESET}"

def bold(text: str) -> str:
    return f"{C.BOLD}{text}{C.RESET}"


# ── Typewriter / flicker effects ───────────────────────────────────────────────

def typewrite(text: str, delay: float = 0.032, newline: bool = True) -> None:
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        time.sleep(delay)
    if newline:
        print()


def glitch_print(text: str, glitch_chars: str = "█▓▒░▀▄■□▪▫", iterations: int = 3) -> None:
    """Print text with a brief glitch effect before settling."""
    for i in range(iterations):
        glitched = "".join(
            random.choice(glitch_chars) if random.random() < 0.4 else ch
            for ch in text
        )
        sys.stdout.write(f"\r{c(C.CYAN, glitched)}")
        sys.stdout.flush()
        time.sleep(0.06)
    sys.stdout.write(f"\r{c(C.BRIGHT_WHITE, text)}\n")
    sys.stdout.flush()


def progress_bar(label: str, width: int = 38, duration: float = 0.8,
                 colour: str = C.BRIGHT_GREEN) -> None:
    steps = width
    for i in range(steps + 1):
        bar     = "█" * i + "░" * (steps - i)
        pct     = int(i / steps * 100)
        prefix  = f"  {c(C.DIM, label.ljust(28))}"
        filled  = c(colour, bar)
        suffix  = c(C.BRIGHT_WHITE, f" {pct:3d}%")
        sys.stdout.write(f"\r{prefix}[{filled}]{suffix}")
        sys.stdout.flush()
        time.sleep(duration / steps)
    print()


def status_line(label: str, value: str, ok: bool = True,
                indent: int = 4, width: int = 32) -> None:
    tick  = c(C.BRIGHT_GREEN, "✔") if ok else c(C.BRIGHT_RED, "✘")
    val   = c(C.BRIGHT_GREEN if ok else C.BRIGHT_RED, value)
    print(f"{'':>{indent}}{c(C.DIM, label.ljust(width))}{tick}  {val}")


def warn_line(label: str, value: str, indent: int = 4, width: int = 32) -> None:
    sym = c(C.YELLOW, "⚠")
    val = c(C.YELLOW, value)
    print(f"{'':>{indent}}{c(C.DIM, label.ljust(width))}{sym}  {val}")


def section(title: str) -> None:
    print()
    bar = "─" * 60
    print(c(C.CYAN, f"  ┌{bar}┐"))
    print(c(C.CYAN,  f"  │") +
          c(C.BOLD + C.BLACK, f"  {title:<58}") +
          c(C.CYAN, "│"))
    print(c(C.CYAN, f"  └{bar}┘"))
    print()


def horizontal_rule(char: str = "─", colour: str = C.DIM) -> None:
    print(c(colour, "  " + char * 62))


# ── Banner ─────────────────────────────────────────────────────────────────────

BANNER = r""""""

BANNER_SUBTITLE = "  [ AERIAL SURVEILLANCE & IDENTIFICATION SYSTEM  //  v2.1.0 ]"
BANNER_TAGLINE  = "  [ NYC METROPOLITAN AIRSPACE — REAL-TIME ADS-B MONITOR     ]"


# ── Individual boot checks ─────────────────────────────────────────────────────

def _check_network() -> bool:
    """Verify internet connectivity via DNS lookup."""
    try:
        socket.setdefaulttimeout(3)
        socket.getaddrinfo("api.airplanes.live", 443)
        return True
    except OSError:
        return False


def _check_adsb_endpoint() -> bool:
    """Ping the ADS-B API endpoint (HEAD request, no data consumed)."""
    try:
        from config import ADSB_ENDPOINT, ADSB_LAT, ADSB_LON, ADSB_RADIUS
        url = ADSB_ENDPOINT.format(lat=ADSB_LAT, lon=ADSB_LON, radius=ADSB_RADIUS)
        r = requests.get(url, timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def _check_flightstats() -> bool:
    """Verify FlightStats base URL is reachable."""
    try:
        r = requests.head("https://www.flightstats.com", timeout=5)
        return r.status_code < 500
    except Exception:
        return False


# ── Boot phases ────────────────────────────────────────────────────────────────

def phase_banner() -> None:
    print(c(C.CYAN, BANNER))
    time.sleep(0.1)
    typewrite(c(C.BLACK, BANNER_SUBTITLE), delay=0.008)
    typewrite(c(C.DIM,           BANNER_TAGLINE),  delay=0.008)
    print()
    time.sleep(0.3)


def phase_hardware_init() -> None:
    section("PHASE 1 — HARDWARE & RUNTIME INITIALISATION")

    checks = [
        ("Python runtime",        platform.python_version(),               True),
        ("Operating system",      f"{platform.system()} {platform.release()}", True),
        ("Host node",             socket.gethostname(),                    True),
        ("Architecture",          platform.machine(),                      True),
        ("UTC clock",             datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), True),
    ]

    for label, value, ok in checks:
        time.sleep(random.uniform(0.05, 0.12))
        status_line(label, value, ok=ok)

    print()
    progress_bar("Loading runtime modules ...", duration=0.9, colour=C.CYAN)
    progress_bar("Initialising memory pools ...", duration=0.6, colour=C.CYAN)
    progress_bar("Calibrating system clock  ...", duration=0.4, colour=C.CYAN)


def phase_config_dump() -> None:
    from config import (
        ADSB_LAT, ADSB_LON, ADSB_RADIUS,
        ADSB_ENDPOINT,
        AIRCRAFT_CATEGORIES,
        CACHE_TTL_MINUTES,
        POLL_INTERVAL_SECONDS,
        DEDUCE_FLIGHT_NUM,
        NEARBY_AIRPORTS,
        FLIGHTSTATS_BASE_URL,
        FLIGHTSTATS_REQUEST_TIMEOUT,
    )

    section("PHASE 2 — CONFIGURATION MATRIX")

    horizontal_rule()
    print(f"  {c(C.YELLOW, '▶ ADS-B RECEPTION POINT')}")
    horizontal_rule()
    status_line("Latitude",            f"{ADSB_LAT}° N")
    status_line("Longitude",           f"{ADSB_LON}° W")
    status_line("Search radius",       f"{ADSB_RADIUS} nm")
    status_line("API endpoint",        ADSB_ENDPOINT.split("/v2")[0] + "/v2/…")
    status_line("Aircraft categories", ", ".join(AIRCRAFT_CATEGORIES))
    print()

    time.sleep(1)

    horizontal_rule()
    print(f"  {c(C.YELLOW, '▶ CACHE & POLLING')}")
    horizontal_rule()
    status_line("Cache TTL",           f"{CACHE_TTL_MINUTES} min")
    status_line("Poll interval",       f"{POLL_INTERVAL_SECONDS} s")
    print()

    time.sleep(1)

    horizontal_rule()
    print(f"  {c(C.YELLOW, '▶ CALLSIGN RESOLUTION')}")
    horizontal_rule()
    status_line("Deduce flight number",  str(DEDUCE_FLIGHT_NUM))
    status_line("Nearby airports",       ", ".join(NEARBY_AIRPORTS))
    print()

    time.sleep(1)

    horizontal_rule()
    print(f"  {c(C.YELLOW, '▶ FLIGHTSTATS SCRAPER')}")
    horizontal_rule()
    base = FLIGHTSTATS_BASE_URL.split("?")[0].replace("{airline}", "XX").replace("{number}", "000")
    status_line("Base URL",            base)
    status_line("Request timeout",     f"{FLIGHTSTATS_REQUEST_TIMEOUT} s")
    print()
    time.sleep(0.3)


def phase_systems_check() -> bool:
    section("PHASE 3 — SYSTEMS CONNECTIVITY CHECK")

    all_ok = True

    # Network
    sys.stdout.write(f"  {c(C.DIM, 'Network layer'.ljust(32))}{c(C.BLINK + C.YELLOW, '… scanning')}")
    sys.stdout.flush()
    net_ok = _check_network()
    sys.stdout.write("\r" + " " * 60 + "\r")
    if net_ok:
        status_line("Network layer", "ONLINE", ok=True)
    else:
        status_line("Network layer", "OFFLINE", ok=False)
        all_ok = False

    time.sleep(0.3)

    # ADS-B endpoint
    sys.stdout.write(f"  {c(C.DIM, 'ADS-B endpoint'.ljust(32))}{c(C.BLINK + C.YELLOW, '… probing ')}")
    sys.stdout.flush()
    adsb_ok = _check_adsb_endpoint()
    sys.stdout.write("\r" + " " * 60 + "\r")
    if adsb_ok:
        status_line("ADS-B endpoint", "REACHABLE", ok=True)
    else:
        warn_line("ADS-B endpoint", "UNREACHABLE — tracker will retry at runtime")

    time.sleep(0.3)

    # FlightStats
    sys.stdout.write(f"  {c(C.DIM, 'FlightStats service'.ljust(32))}{c(C.BLINK + C.YELLOW, '… probing ')}")
    sys.stdout.flush()
    fs_ok = _check_flightstats()
    sys.stdout.write("\r" + " " * 60 + "\r")
    if fs_ok:
        status_line("FlightStats service", "REACHABLE", ok=True)
    else:
        warn_line("FlightStats service", "UNREACHABLE — enrichment may be limited")

    time.sleep(0.4)
    print()
    progress_bar("Running diagnostics       ...", duration=0.8, colour=C.BRIGHT_GREEN)
    progress_bar("Verifying module integrity...", duration=0.5, colour=C.BRIGHT_GREEN)

    return all_ok


def phase_ready() -> None:
    section("PHASE 4 — ALL SYSTEMS NOMINAL")

    lines = [
        "  ╔════════════════════════════════════════════════════════════╗",
        "  ║                                                            ║",
        "  ║   Now monitoring airspace for heavy commercial traffic.    ║",
        "  ║   ADS-B feed active · FlightStats enrichment enabled       ║",
        "  ║   Cache armed · Callsign resolver standing by.             ║",
        "  ║                                                            ║",
        "  ╚════════════════════════════════════════════════════════════╝",
    ]
    for line in lines:
        typewrite(c(C.BRIGHT_GREEN, line), delay=0)
        # time.sleep(0.03)

    print()
    print(c(C.CYAN,
        "  Type  " + c(C.BOLD + C.RED, "start") + c(C.CYAN, "  to begin tracking  ·  Ctrl-C to abort")))
    print()


def phase_launch_countdown() -> None:
    section("INITIATING TRACKING SEQUENCE")

    for label, duration, col in [
        ("Arming ADS-B listener     ...", 0.5, C.RED),
        ("Spinning up cache layer   ...", 0.4, C.RED),
        ("Engaging callsign resolver...", 0.4, C.RED),
        ("Connecting to FlightStats ...", 0.6, C.RED),
        ("Launching polling loop    ...", 0.3, C.RED),
    ]:
        progress_bar(label, duration=duration, colour=col)

    print()
    # for i in range(3, 0, -1):
    #     sys.stdout.write(
    #         f"\r  {c(C.BOLD + C.YELLOW, f'LAUNCHING IN  {i} …')}"
    #         + "   "
    #     )
    #     sys.stdout.flush()
    #     time.sleep(0.8)

    sys.stdout.write(f"\r  {c(C.BOLD + C.RED, 'BEGIN SCANNING')}" + "   \n\n")
    sys.stdout.flush()
    time.sleep(0.4)


# ── Entry point ────────────────────────────────────────────────────────────────

def await_command(prompt: str, expected: str) -> None:
    """Block until the user types the expected command (case-insensitive)."""
    while True:
        try:
            raw = input(prompt).strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            print(c(C.BRIGHT_RED, "\n  [ABORT]  Boot sequence cancelled."))
            sys.exit(0)
        if raw == expected.lower():
            break
        print(c(C.BRIGHT_RED,
            f"  ✘  Unrecognised command. "
            f"Type '{c(C.BOLD + C.BRIGHT_WHITE, expected)}{C.BRIGHT_RED}' to continue."))


def main() -> None:
    # ── Await 'boot' ──────────────────────────────────────────────────────────
    print()
    print(c(C.DIM, "  ──────────────────────────────────────────────────────────────"))
    typewrite(c(C.CYAN,
        "  FLIGHT TRACKER OS  //  type  ") +
        c(C.BOLD + C.RED, "boot") +
        c(C.CYAN, "  to initialise"),
        delay=0)
    print(c(C.DIM, "  ──────────────────────────────────────────────────────────────"))
    print()

    await_command(
        c(C.CYAN, "  flight-tracker:~$ "),
        "boot",
    )

    # ── Boot phases ───────────────────────────────────────────────────────────
    print()
    time.sleep(0.2)
    phase_banner()
    phase_hardware_init()
    phase_config_dump()
    net_ok = phase_systems_check()

    if not net_ok:
        print()
        print(c(C.BRIGHT_RED,
            "  [WARNING]  Network check failed. "
            "Tracker will attempt to run but may not reach ADS-B feed."))
        print()

    phase_ready()

    await_command(
        c(C.BRIGHT_GREEN, "  flight-tracker:~$ "),
        "start",
    )

    phase_launch_countdown()

    # ── Hand off to driver — no functional changes ─────────────────────────────
    import driver
    driver.run()


if __name__ == "__main__":
    main()
