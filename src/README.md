# FlightWall

A fullscreen LED dot-matrix departure board for a Raspberry Pi. Renders a single flight in the style of a 1980s amber airport split-flap display — dot-matrix text, glow bloom, scanline overlay, and flip animations on data changes.

![Three-canvas stack: main dot grid, CSS-blurred glow, scanline overlay]

---

## How it works

Three stacked `<canvas>` elements at 1920×1080 (scaled to fill the screen):

| Canvas | Purpose |
|---|---|
| `canvas-main` | Dot-matrix grid — background dots + all text and logos |
| `canvas-glow` | Same content drawn larger, CSS `filter: blur(5px)` + `mix-blend-mode: screen` |
| `canvas-scanline` | Alternating dark stripes drawn once at startup, never redrawn |

The board is idle at ~0% CPU between updates. The RAF loop only runs during flip animations (~500ms), then stops.

---

## Development setup

**Requirements:** Node 18+

```bash
npm install
npm run dev
```

Open `http://localhost:5173`. The board reads `public/flights.json` every 5 seconds and re-renders with flip animations when the data changes.

To build a production bundle:

```bash
npm run build
# output: dist/
```

---

## Raspberry Pi deployment

### 1. Build on your dev machine

```bash
npm run build
```

### 2. Copy to the Pi

```bash
rsync -av dist/ pi@raspberrypi.local:/home/pi/flightwall/dist/
```

### 3. Run the installer on the Pi

SSH in and run:

```bash
cd /home/pi/flightwall
bash deploy/install.sh
```

This:
- Installs `unclutter` (hides the mouse cursor)
- Installs and enables the `flightwall` systemd user service (serves `dist/` on port 3000 via `python3 -m http.server`)
- Adds Chromium kiosk autostart to `~/.config/labwc/autostart`

### 4. Reboot

```bash
sudo reboot
```

Chromium will launch fullscreen at `http://localhost:3000` on every boot.

### TV / display config

If the TV doesn't report its resolution correctly, add to `/boot/firmware/config.txt`:

```
hdmi_force_hotplug=1
hdmi_mode=82
```

`hdmi_mode=82` is 1920×1080 @ 60 Hz. Reboot after changing.

---

## Providing flight data

The display reads `dist/flights.json` (or `public/flights.json` in dev). Overwrite this file with a JSON array containing one flight record:

```json
[
  {
    "flightNumber": "AA 99",
    "airline": "American Airlines",
    "airlineIata": "AA",
    "aircraft": "Boeing 737-8",
    "origin": "LAX",
    "destination": "JFK"
  }
]
```

### Field reference

| Field | Type | Example | Notes |
|---|---|---|---|
| `flightNumber` | string | `"AA 99"` | Displayed in cyan, top-left |
| `airline` | string | `"American Airlines"` | Full name, displayed in cyan next to logo |
| `airlineIata` | string | `"AA"` | Used to load `logos/AA.svg`; falls back to airplane icon |
| `aircraft` | string | `"Boeing 737-8"` | Displayed in green, top-right |
| `origin` | string | `"LAX"` | IATA code — large amber text, bottom-left |
| `destination` | string | `"JFK"` | IATA code — large amber text, bottom-right |

The display polls every 5 seconds. Only changed fields animate; unchanged fields hold their position.

### Updating from a script

Use `update_flight.py` — a zero-dependency Python helper included in the repo.

**As a module** (import into your own code):

```python
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
```

**From the command line:**

```bash
python3 update_flight.py \
    --flight-number "AA 99" --airline "American Airlines" --airline-iata AA \
    --aircraft "Boeing 737-8" --origin LAX --destination JFK \
    --path /home/pi/flightwall/dist/flights.json
```

The write is atomic (temp file + rename) so the display never reads a partial file. The default `--path` is `dist/flights.json` relative to the script.

---

## Browser console interface

`window.flightBoard` is exposed for live testing and debugging:

```js
// Replace the current flight entirely (no animation)
flightBoard.set({
  flightNumber: 'BA 112',
  airline: 'British Airways',
  airlineIata: 'BA',
  aircraft: 'A388',
  origin: 'JFK',
  destination: 'LHR',
});

// Update — only changed fields animate
flightBoard.update({ ...currentFlight, aircraft: 'B77W' });

// Navigate between records in flights.json
flightBoard.next();   // arrow right
flightBoard.prev();   // arrow left
flightBoard.goto(2);  // jump to index 2
```

Arrow keys (`←` / `→`) also navigate between records while the page is focused.

---

## Airline logos

Place SVG files in `public/logos/` named by IATA code (uppercase):

```
public/logos/
  AA.svg
  BA.svg
  UA.svg
  ...
```

Logos are rendered with a pixelation effect (scaled down 5× then back up) to match the dot-matrix aesthetic. If no logo file exists for an airline, the board shows an amber airplane icon fetched from the Iconify CDN (`fa6-solid:plane`). The Pi must have internet access for the fallback icon to appear; without it the logo zone is left empty.

---

## Tuning

All visual constants live in `src/config.ts`:

| Constant | Default | Effect |
|---|---|---|
| `FLIP_DURATION` | `0.5` | Seconds each character takes to settle |
| `FLIP_INTERVAL` | `0.02` | Seconds between random character flips |
| `FLIP_STAGGER` | `0.015` | Delay added per character position (left→right cascade) |
| `POLL_INTERVAL_MS` | `5000` | How often `flights.json` is checked |
| `FONT_SIZE_AIRPORT` | `544` | Airport code (LAX / JFK) font size |
| `FONT_SIZE_AIRPORT_NAME` | `112` | Airport full name font size |
| `FONT_SIZE_FLIGHT` | `160` | Airline name font size |
| `FONT_SIZE_AIRLINE` | `192` | Flight number / aircraft font size |

The dev server hot-reloads on save, so constant changes are reflected immediately without restarting.
