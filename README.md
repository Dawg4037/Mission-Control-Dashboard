# Mission Control Dashboard

Space-station-style always-on dashboard for Tarpon Springs, FL (34689).

## Run it

Double-click **start_dashboard.bat** (normal window) or **start_kiosk.bat** (fullscreen kiosk, Edge).
First run installs `psutil` automatically. Requires Python 3.8+ from python.org.

Server runs at http://localhost:8350 (local only — nothing exposed to the network).
To stop: close the minimized "Mission Control Server" window.

## Panels

| Panel | Data | Refresh |
|---|---|---|
| Atmospherics | Open-Meteo forecast + NWS alerts | 10 min |
| Precip Scan | NWS doppler radar loop, Tampa Bay station KTBW (radar.weather.gov) | 5 min |
| Comms / Newsfeed | Local (WFLA, FOX 13, ABC AN), US (NPR, CBS, Fox), World (BBC, NPR, Al Jazeera), Tech (Ars, Verge, HN) — tabs auto-rotate 15s; click a tab to pin | 10 min |
| Ship Systems | Live CPU (per-core), RAM, disks, network, uptime, top processes via psutil | 2 s |
| Gulf Ops | NOAA tides (Clearwater station) + NHC tropical activity | 1 h / 30 min |
| Orbital Ops | ISS live track, launch countdowns, planetary K-index, NASA APOD — auto-rotates 20s; click to pin | 5 s – 6 h |
| Ticker | Scrolling headlines from all categories | 10 min |

## Always-on features

- **Burn-in protection**: layout micro-shifts every 4 min; auto-dims 11 PM–7 AM
- **Alert flashes**: panel pulses red on NWS alerts, CPU >90%, RAM >92%, Kp ≥5, launch <10 min, active tropical systems; header status light goes red
- **Cursor auto-hides** after 8 s idle; ⛶ button or F11 for fullscreen

## Desktop shortcut

Run **make_desktop_shortcut.bat** once — it puts a "Mission Control" icon on your Desktop.
If `mission_control.ico` is missing (e.g., fresh clone), generate it with
`pip install pillow` then `python gen_icon.py`.

## Tweaks (edit CONFIG at top of server.py)

- `NASA_API_KEY`: using DEMO_KEY (limited). Free key at https://api.nasa.gov
- `PORT`, location (`LAT`/`LON`), tide station
- News sources: edit the `FEEDS` dict — any RSS/Atom URL works
