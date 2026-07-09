# Mission Control Dashboard — Project Handoff Notes

Context file for AI assistants (or humans) picking up this project. Read this before changing anything.

## What this is

A space-station-themed, always-on dashboard for Dawg (GitHub: **Dawg4037**), running locally on Windows.
Location: Tarpon Springs, FL 34689. Repo: **https://github.com/Dawg4037/Mission-Control-Dashboard** (public).
Local working copy: `Desktop\mission-control\` — **this folder is the source of truth**; keep it and GitHub in sync.

## Architecture

- `server.py` — Python 3 stdlib + psutil only. Serves `dashboard.html` at **http://localhost:8350** (127.0.0.1 only) and proxies/caches all external APIs under `/api/*`. All config (location, port, NASA key, tide station, RSS feeds, YouTube channels) is in dicts at the top of the file.
- `dashboard.html` — single file, zero external JS/CSS dependencies (everything hand-rolled: canvas charts, starfield, ticker). Panels: Atmospherics (Open-Meteo + NWS alerts), Video Uplink (YouTube embed + latest uploads list), Ship Systems (psutil hardware telemetry, 2s), Gulf Ops (NOAA tides + NHC hurricanes), Orbital Ops (rotating tabs: ISS map / launch countdowns / NOAA SWPC Kp / NASA APOD), bottom news ticker (RSS from 12 outlets in 4 categories).
- `start_dashboard.bat` / `start_kiosk.bat` — launchers (install psutil if missing, start server minimized, open browser; kiosk uses Edge --kiosk).
- `make_desktop_shortcut.bat` — creates Desktop shortcut via **VBScript** (see gotchas).
- `gen_icon.py` — regenerates `mission_control.ico` (PIL). The .ico exists locally but is **NOT in the repo** (see gotchas).

Data endpoints: `/api/hardware` (no cache), `/api/iss` (5s), `/api/news` (10m), `/api/videos` (15m), `/api/weather` (10m), `/api/tides` (1h), `/api/hurricanes` (30m), `/api/apod` (6h), `/api/launches` (1h), `/api/spacewx` (15m), `/api/config`. All failures degrade per-panel ("SIGNAL LOST" overlays); `cached()` serves stale data on refresh failure.

Always-on features: burn-in micro-shift (4 min), night dim 23:00–07:00, cursor auto-hide, red alert flashes (NWS alert, CPU>90%, RAM>92%, Kp≥5, launch<10min, active tropical system) + header status light.

## Critical operational rules

1. **`server.py` changes require a server restart** (close the minimized "Mission Control Server" window, relaunch). `dashboard.html` changes only need a browser refresh (served fresh from disk, no-store). Symptom of forgotten restart: new UI shows but new endpoints return 404 → panel shows OFFLINE.
2. **dashboard.html must be opened via the server**, never as file:// — there's a JS guard that shows "WRONG LAUNCH SEQUENCE" if opened directly.
3. User runs **Brave** browser. Windows PC, Python from python.org (was missing initially — the bats check for it).

## Gotchas learned the hard way (do not repeat these)

- **Sandbox/VM file-copy corruption**: copying files to the user's folders through the agent sandbox mount (`cp` in bash) produced a **truncated dashboard.html** (cut at the file's previous byte-length). Symptom: even the clock froze because the inline JS was cut mid-line. **Fix/rule: write files to the user's machine with direct host-side Write/Edit tools, never bash cp through the mount; after any transfer, verify the file ends with `</html>`.**
- **PowerShell is locked down** on this PC (Constrained Language Mode — COM blocked). Shortcut creation had to use VBScript via cscript. Assume fancy PowerShell won't work.
- **GitHub connector**: authenticates via fine-grained PAT. It can push contents but initially couldn't create repos (user fixed token perms). **Binary files cannot be pushed** through the connector (text-only) — that's why `gen_icon.py` exists instead of committing the .ico. `push_files` fails on an empty repo ("Git Repository is empty") — seed with `create_or_update_file` first; updates via `create_or_update_file` need the file's current SHA.
- YouTube video feed uses **channel RSS** (`youtube.com/feeds/videos.xml?channel_id=...`) — no API key. NASA APOD uses DEMO_KEY (rate-limited; user can drop a free key into CONFIG).

## Current YouTube channels (YT_CHANNELS in server.py)

NASA, SpaceX, NASASpaceflight, Linus Tech Tips, Gamers Nexus, ABC News, NBC News. Player auto-plays newest upload muted; clicking a list item plays with sound.

## Ideas discussed but not built

- Cleveland Browns scores/next-game countdown (user is a Browns fan — ESPN free API).
- User has interests in crypto mining (Flux, mining pools), homelab hardware (Dell R620, K8s) per browser bookmarks — themed panels could fit.

## Workflow expectations

- User is non-developer-ish but technical; wants working double-click solutions, concise answers.
- After any change: update the local files in `Desktop\mission-control\` AND push the same change to GitHub (repo listed above), then tell the user whether a server restart or just a browser refresh is needed.
