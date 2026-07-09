#!/usr/bin/env python3
"""
MISSION CONTROL DASHBOARD - backend server
Serves dashboard.html and proxies/caches all external data feeds.
Requires: Python 3.8+, psutil (pip install psutil)
"""
import json
import gzip
import time
import threading
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from pathlib import Path

try:
    import psutil
except ImportError:
    psutil = None

# ------------------------- CONFIG -------------------------
CONFIG = {
    "PORT": 8350,
    "LAT": 28.146,          # Tarpon Springs, FL 34689
    "LON": -82.757,
    "PLACE": "TARPON SPRINGS, FL",
    "NASA_API_KEY": "DEMO_KEY",   # get a free key at https://api.nasa.gov for higher limits
    "TIDE_STATION": "8726724",    # NOAA Clearwater Beach, FL
    "TIMEZONE": "America/New_York",
}

FEEDS = {
    "local": [
        ("WFLA", "https://www.wfla.com/feed/"),
        ("FOX 13", "https://www.fox13news.com/latest.xml"),
        ("ABC Action News", "https://www.abcactionnews.com/index.rss"),
    ],
    "us": [
        ("NPR", "https://feeds.npr.org/1003/rss.xml"),
        ("CBS News", "https://www.cbsnews.com/latest/rss/us"),
        ("Fox News", "https://moxie.foxnews.com/google-publisher/us.xml"),
    ],
    "world": [
        ("BBC", "https://feeds.bbci.co.uk/news/world/rss.xml"),
        ("NPR World", "https://feeds.npr.org/1004/rss.xml"),
        ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
    ],
    "tech": [
        ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
        ("The Verge", "https://www.theverge.com/rss/index.xml"),
        ("Hacker News", "https://hnrss.org/frontpage"),
    ],
}

# YouTube channels for the video panel (name, channel_id) - uploads pulled via RSS, no API key
YT_CHANNELS = [
    ("NASA", "UCLA_DiR1FfKNvjuUpBHmylQ"),
    ("SpaceX", "UCtI0Hodo5o5dUb67FeUjDeA"),
    ("NASASpaceflight", "UCSUu1lih2RifWkKtDOJdsBA"),
    ("Linus Tech Tips", "UCXuqSBlHAE6Xw-yeJA0Tunw"),
    ("Gamers Nexus", "UChIs72whgZI9w6d6FhwGGHA"),
    ("ABC News", "UCBi2mrWuNuyYy4gbM6fU18Q"),
    ("NBC News", "UCeY0bbntWzzVIaj2z3QigXg"),
]

HERE = Path(__file__).parent
UA = {"User-Agent": "MissionControlDashboard/1.0 (personal use)"}

# ------------------------- FETCH + CACHE -------------------------
_cache = {}
_cache_lock = threading.Lock()


def fetch_raw(url, timeout=12):
    req = urllib.request.Request(url, headers={**UA, "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
        if r.headers.get("Content-Encoding") == "gzip" or data[:2] == b"\x1f\x8b":
            data = gzip.decompress(data)
        return data


def fetch_json(url, timeout=12):
    return json.loads(fetch_raw(url, timeout).decode("utf-8", "replace"))


def cached(key, ttl, fn):
    """Return cached value if fresh; else call fn(). On failure, serve stale."""
    now = time.time()
    with _cache_lock:
        hit = _cache.get(key)
        if hit and now < hit[0]:
            return hit[1]
    try:
        val = fn()
        with _cache_lock:
            _cache[key] = (now + ttl, val)
        return val
    except Exception as e:
        if hit:  # stale is better than nothing
            return hit[1]
        return {"error": str(e)}


# ------------------------- RSS -------------------------
def _strip_ns(tag):
    return tag.split("}")[-1] if "}" in tag else tag


def parse_feed(source, xml_bytes, limit=12):
    items = []
    root = ET.fromstring(xml_bytes)
    # RSS 2.0
    for item in root.iter():
        if _strip_ns(item.tag) not in ("item", "entry"):
            continue
        title, link, pub = "", "", ""
        for c in item:
            t = _strip_ns(c.tag)
            if t == "title":
                title = (c.text or "").strip()
            elif t == "link":
                link = (c.text or "").strip() or c.get("href", "")
            elif t in ("pubDate", "published", "updated", "date"):
                pub = pub or (c.text or "").strip()
        if title:
            items.append({"title": title, "link": link, "pub": pub, "source": source})
        if len(items) >= limit:
            break
    return items


def get_news():
    out = {}
    for cat, feeds in FEEDS.items():
        merged, errors = [], []
        for name, url in feeds:
            try:
                merged.extend(parse_feed(name, fetch_raw(url)))
            except Exception as e:
                errors.append(f"{name}: {e}")
        # interleave sources so one outlet doesn't dominate the top
        by_src = {}
        for it in merged:
            by_src.setdefault(it["source"], []).append(it)
        inter = []
        while any(by_src.values()) and len(inter) < 24:
            for src in list(by_src):
                if by_src[src]:
                    inter.append(by_src[src].pop(0))
        out[cat] = {"items": inter, "errors": errors}
    return out


def get_videos():
    """Latest uploads from YT_CHANNELS via YouTube's public RSS (Atom)."""
    NS = {
        "a": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
    }
    vids, errors = [], []
    for name, cid in YT_CHANNELS:
        try:
            root = ET.fromstring(fetch_raw(
                f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}"))
            for e in root.findall("a:entry", NS)[:4]:
                vid = e.findtext("yt:videoId", "", NS)
                if not vid:
                    continue
                vids.append({
                    "id": vid,
                    "title": e.findtext("a:title", "", NS),
                    "channel": name,
                    "published": e.findtext("a:published", "", NS),
                    "thumb": f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg",
                })
        except Exception as ex:
            errors.append(f"{name}: {ex}")
    vids.sort(key=lambda v: v["published"], reverse=True)
    return {"videos": vids[:24], "errors": errors}


# ------------------------- WEATHER / TIDES / HURRICANES -------------------------
def get_weather():
    lat, lon = CONFIG["LAT"], CONFIG["LON"]
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&current=temperature_2m,relative_humidity_2m,apparent_temperature,"
        "weather_code,wind_speed_10m,wind_gusts_10m,wind_direction_10m,"
        "uv_index,pressure_msl,cloud_cover,precipitation"
        "&hourly=temperature_2m,precipitation_probability,weather_code"
        "&daily=weather_code,temperature_2m_max,temperature_2m_min,"
        "precipitation_probability_max,sunrise,sunset"
        "&temperature_unit=fahrenheit&wind_speed_unit=mph"
        "&precipitation_unit=inch&forecast_days=7"
        f"&timezone={CONFIG['TIMEZONE'].replace('/', '%2F')}"
    )
    data = fetch_json(url)
    try:
        alerts = fetch_json(f"https://api.weather.gov/alerts/active?point={lat},{lon}")
        data["nws_alerts"] = [
            {
                "event": f["properties"].get("event"),
                "severity": f["properties"].get("severity"),
                "headline": f["properties"].get("headline"),
                "expires": f["properties"].get("expires"),
            }
            for f in alerts.get("features", [])
        ]
    except Exception as e:
        data["nws_alerts"] = []
        data["nws_error"] = str(e)
    return data


def get_tides():
    st = CONFIG["TIDE_STATION"]
    base = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
    out = {"station": st}
    out["predictions"] = fetch_json(
        f"{base}?product=predictions&station={st}&date=today&range=48"
        "&datum=MLLW&time_zone=lst_ldt&units=english&format=json&interval=hilo"
        "&application=MissionControl"
    ).get("predictions", [])
    try:
        wt = fetch_json(
            f"{base}?product=water_temperature&station={st}&date=latest"
            "&time_zone=lst_ldt&units=english&format=json&application=MissionControl"
        )
        out["water_temp"] = wt.get("data", [{}])[-1].get("v")
    except Exception:
        out["water_temp"] = None
    return out


def get_hurricanes():
    data = fetch_json("https://www.nhc.noaa.gov/CurrentStorms.json")
    storms = []
    for s in data.get("activeStorms", []):
        storms.append({
            "name": s.get("name"),
            "classification": s.get("classification"),
            "intensity": s.get("intensity"),
            "pressure": s.get("pressure"),
            "lat": s.get("latitudeNumeric"),
            "lon": s.get("longitudeNumeric"),
            "movement": f"{s.get('movementDir', '')}° @ {s.get('movementSpeed', '')} mph",
            "update": s.get("lastUpdate"),
        })
    return {"storms": storms}


# ------------------------- SPACE -------------------------
def get_apod():
    d = fetch_json(
        f"https://api.nasa.gov/planetary/apod?api_key={CONFIG['NASA_API_KEY']}&thumbs=true"
    )
    return {
        "title": d.get("title"),
        "url": d.get("thumbnail_url") or d.get("url"),
        "media_type": d.get("media_type"),
        "explanation": (d.get("explanation") or "")[:400],
        "date": d.get("date"),
    }


def get_iss():
    try:
        d = fetch_json("https://api.wheretheiss.at/v1/satellites/25544", timeout=8)
        return {"lat": d["latitude"], "lon": d["longitude"], "alt_km": d.get("altitude"),
                "vel_kmh": d.get("velocity"), "visibility": d.get("visibility")}
    except Exception:
        d = fetch_json("http://api.open-notify.org/iss-now.json", timeout=8)
        p = d["iss_position"]
        return {"lat": float(p["latitude"]), "lon": float(p["longitude"]),
                "alt_km": None, "vel_kmh": None, "visibility": None}


def get_launches():
    d = fetch_json("https://ll.thespacedevs.com/2.2.0/launch/upcoming/?limit=5&hide_recent_previous=true")
    out = []
    for l in d.get("results", []):
        out.append({
            "name": l.get("name"),
            "net": l.get("net"),
            "status": (l.get("status") or {}).get("abbrev"),
            "provider": (l.get("launch_service_provider") or {}).get("name"),
            "pad": ((l.get("pad") or {}).get("location") or {}).get("name"),
            "probability": l.get("probability"),
        })
    return {"launches": out}


def get_spacewx():
    out = {}
    kp = fetch_json("https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json")
    # first row is header when using /products/ endpoints that return lists-of-lists;
    # this one returns list of dicts - handle both
    if kp and isinstance(kp[0], dict):
        rows = kp[-24:]
        out["kp"] = [{"t": r["time_tag"], "kp": float(r["Kp"])} for r in rows]
    else:
        rows = kp[1:][-24:]
        out["kp"] = [{"t": r[0], "kp": float(r[1])} for r in rows]
    try:
        alerts = fetch_json("https://services.swpc.noaa.gov/products/alerts.json")
        out["alerts"] = [
            {"issued": a.get("issue_datetime"), "msg": (a.get("message") or "")[:220]}
            for a in alerts[:3]
        ]
    except Exception:
        out["alerts"] = []
    try:
        wind = fetch_json("https://services.swpc.noaa.gov/products/summary/solar-wind-speed.json")
        out["solar_wind"] = wind.get("WindSpeed")
    except Exception:
        out["solar_wind"] = None
    return out


# ------------------------- HARDWARE -------------------------
_net_last = {"t": 0.0, "sent": 0, "recv": 0}
if psutil:
    psutil.cpu_percent(percpu=True)  # prime


def get_hardware():
    if not psutil:
        return {"error": "psutil not installed - run: pip install psutil"}
    vm = psutil.virtual_memory()
    sw = psutil.swap_memory()
    disks = []
    for p in psutil.disk_partitions(all=False):
        if "cdrom" in p.opts or not p.fstype:
            continue
        try:
            u = psutil.disk_usage(p.mountpoint)
            disks.append({"mount": p.mountpoint, "pct": u.percent,
                          "used_gb": round(u.used / 1e9, 1), "total_gb": round(u.total / 1e9, 1)})
        except Exception:
            pass
    now = time.time()
    io = psutil.net_io_counters()
    up = down = 0.0
    if _net_last["t"]:
        dt = max(now - _net_last["t"], 0.001)
        up = (io.bytes_sent - _net_last["sent"]) / dt
        down = (io.bytes_recv - _net_last["recv"]) / dt
    _net_last.update(t=now, sent=io.bytes_sent, recv=io.bytes_recv)

    temps = {}
    try:
        for name, entries in (psutil.sensors_temperatures() or {}).items():
            for e in entries:
                if e.current:
                    temps[e.label or name] = round(e.current, 1)
    except Exception:
        pass

    freq = None
    try:
        f = psutil.cpu_freq()
        freq = round(f.current) if f else None
    except Exception:
        pass

    procs = []
    try:
        plist = [(p.info["name"], p.info["cpu_percent"] or 0, p.info["memory_percent"] or 0)
                 for p in psutil.process_iter(["name", "cpu_percent", "memory_percent"])]
        plist.sort(key=lambda x: x[1], reverse=True)
        procs = [{"name": n[:22], "cpu": round(c, 1), "mem": round(m, 1)}
                 for n, c, m in plist[:5]]
    except Exception:
        pass

    return {
        "cpu_total": psutil.cpu_percent(),
        "cpu_per_core": psutil.cpu_percent(percpu=True),
        "cpu_freq_mhz": freq,
        "ram_pct": vm.percent,
        "ram_used_gb": round(vm.used / 1e9, 1),
        "ram_total_gb": round(vm.total / 1e9, 1),
        "swap_pct": sw.percent,
        "disks": disks,
        "net_up_bps": round(up),
        "net_down_bps": round(down),
        "uptime_s": round(time.time() - psutil.boot_time()),
        "temps": temps,
        "top_procs": procs,
        "proc_count": len(psutil.pids()),
    }


# ------------------------- HTTP -------------------------
ROUTES = {
    "/api/hardware": lambda: get_hardware(),                       # no cache
    "/api/iss":      lambda: cached("iss", 5, get_iss),
    "/api/news":     lambda: cached("news", 600, get_news),
    "/api/videos":   lambda: cached("videos", 900, get_videos),
    "/api/weather":  lambda: cached("weather", 600, get_weather),
    "/api/tides":    lambda: cached("tides", 3600, get_tides),
    "/api/hurricanes": lambda: cached("hurr", 1800, get_hurricanes),
    "/api/apod":     lambda: cached("apod", 6 * 3600, get_apod),
    "/api/launches": lambda: cached("launches", 3600, get_launches),
    "/api/spacewx":  lambda: cached("spacewx", 900, get_spacewx),
    "/api/config":   lambda: {"place": CONFIG["PLACE"], "lat": CONFIG["LAT"], "lon": CONFIG["LON"]},
}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass  # quiet

    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html", "/dashboard.html"):
            try:
                body = (HERE / "dashboard.html").read_bytes()
                self._send(200, body, "text/html; charset=utf-8")
            except FileNotFoundError:
                self._send(500, b"dashboard.html not found next to server.py", "text/plain")
            return
        fn = ROUTES.get(path)
        if fn:
            try:
                data = fn()
            except Exception as e:
                data = {"error": str(e)}
            self._send(200, json.dumps(data).encode(), "application/json")
            return
        self._send(404, b"not found", "text/plain")


def main():
    port = CONFIG["PORT"]
    print(f"\n  MISSION CONTROL online -> http://localhost:{port}\n  Ctrl+C to shut down.\n")
    if not psutil:
        print("  WARNING: psutil not installed; hardware panel disabled.")
        print("  Fix: pip install psutil\n")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
