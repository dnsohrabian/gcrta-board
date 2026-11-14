#!/usr/bin/env python3
"""Find GCRTA stop numbers for config.py. Runs on your computer (Python 3.8+), not on the board.

Examples:
  python find_stops.py lorain 117          stops whose name contains "lorain" and "117"
  python find_stops.py lorain --route 22   only stops served by route 22
  python find_stops.py 7694 --live         show live arrivals for stop 7694 (needs an API key)

The first run downloads GCRTA's published schedule data (~18 MB) and builds a small index;
later runs are instant. The index refreshes automatically after 14 days.
--live reads SWIFTLY_API_KEY from the environment, --key, or a settings.toml next to this
folder (e.g. on the CIRCUITPY drive).
"""
import argparse
import csv
import io
import json
import os
import sys
import time
import urllib.request
import zipfile

GTFS_URL = "https://www.riderta.com/sites/default/files/gtfs/latest/google_transit.zip"
LIVE_URL = "https://api.goswift.ly/real-time/{agency}/predictions?stop={stop}&number=3"
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, ".cache")
INDEX = os.path.join(CACHE, "stop_index.json")
MAX_AGE_DAYS = 14


def build_index():
    os.makedirs(CACHE, exist_ok=True)
    print("Downloading GCRTA schedule data (GTFS)...", file=sys.stderr)
    req = urllib.request.Request(GTFS_URL, headers={"User-Agent": "transit-board-stop-finder"})
    data = urllib.request.urlopen(req, timeout=120).read()
    z = zipfile.ZipFile(io.BytesIO(data))

    def rows(name):
        return csv.DictReader(io.TextIOWrapper(z.open(name), "utf-8-sig", errors="replace"))

    print("Indexing stops (takes ~30 s)...", file=sys.stderr)
    routes = {r["route_id"]: r["route_short_name"] for r in rows("routes.txt")}
    trips = {t["trip_id"]: (routes.get(t["route_id"], t["route_id"]), t["trip_headsign"]) for t in rows("trips.txt")}
    served = {}
    for st in rows("stop_times.txt"):
        served.setdefault(st["stop_id"], set()).add(trips[st["trip_id"]])
    stops = []
    for s in rows("stops.txt"):
        if s["stop_id"] not in served:
            continue
        stops.append({
            "code": s.get("stop_code") or s["stop_id"],
            "name": s["stop_name"],
            "lat": s["stop_lat"].strip(),
            "lon": s["stop_lon"].strip(),
            "routes": sorted(served[s["stop_id"]]),
        })
    with open(INDEX, "w", encoding="utf-8") as f:
        json.dump({"built": time.time(), "stops": stops}, f)
    return stops


def load_index(refresh=False):
    if not refresh and os.path.exists(INDEX):
        with open(INDEX, encoding="utf-8") as f:
            idx = json.load(f)
        if time.time() - idx["built"] < MAX_AGE_DAYS * 86400:
            return idx["stops"]
    return build_index()


def find_key(cli_key):
    if cli_key:
        return cli_key
    if os.getenv("SWIFTLY_API_KEY"):
        return os.getenv("SWIFTLY_API_KEY")
    for path in (os.path.join(HERE, "..", "settings.toml"), os.path.join(HERE, "..", "src", "settings.toml"),
                 os.path.join(HERE, "settings.toml")):
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                for line in f:
                    k, _, v = line.partition("=")
                    if k.strip() == "SWIFTLY_API_KEY":
                        return v.strip().strip('"')
    return None


def live(stop, key, agency, route=None):
    req = urllib.request.Request(LIVE_URL.format(agency=agency, stop=int(stop)), headers={"Authorization": key})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.load(r)["data"]["predictionsData"]
    print("    live now:")
    shown = 0
    for p in data:
        short = p["routeShortName"].upper()
        if route and route not in (short, short.split("-")[0], str(p["routeId"]).upper()):
            continue
        for d in p["destinations"]:
            mins = ", ".join(str(x["min"]) for x in d["predictions"])
            print("      route %-10s %-38s %s" % (p["routeShortName"], d["headsign"],
                                                  mins + " min" if mins else "none soon"))
            shown += 1
    if not shown:
        print("      (nothing returned)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("words", nargs="*", help="words in the stop name, or a stop number")
    ap.add_argument("--route", help="only stops served by this route, e.g. 22, 26, RL")
    ap.add_argument("--live", action="store_true", help="also show live arrivals (needs API key)")
    ap.add_argument("--key", help="Swiftly API key (otherwise env/settings.toml)")
    ap.add_argument("--agency", default="cleveland")
    ap.add_argument("--refresh", action="store_true", help="re-download schedule data now")
    ap.add_argument("--limit", type=int, default=25)
    args = ap.parse_args()
    if not args.words and not args.route:
        ap.error("give some words from the stop name, a stop number, or --route")

    stops = load_index(args.refresh)
    words = [w.lower() for w in args.words]
    route = args.route.upper() if args.route else None
    hits = []
    for s in stops:
        code = s["code"].lstrip("0")
        if words and not all(w in s["name"].lower() or w.lstrip("0") == code for w in words):
            continue
        if route and not any(route in (r.upper(), r.upper().split("-")[0]) for r, _ in s["routes"]):
            continue
        hits.append(s)

    key = find_key(args.key) if args.live else None
    if args.live and not key:
        print("No API key found for --live; see settings.toml.example", file=sys.stderr)
    for s in hits[: args.limit]:
        print("stop %-6s %s   (map: https://maps.google.com/?q=%s,%s)" % (
            s["code"].lstrip("0"), s["name"], s["lat"], s["lon"]))
        for r, headsign in s["routes"]:
            if route and route not in (r.upper(), r.upper().split("-")[0]):
                continue
            print("    route %-10s toward: %s" % (r, headsign))
        if key:
            try:
                live(s["code"], key, args.agency, route)
            except Exception as e:  # pylint: disable=broad-except
                print("    live lookup failed:", e)
        print()
    if len(hits) > args.limit:
        print("... %d more matches; add words or --route to narrow it down" % (len(hits) - args.limit))
    if not hits:
        print("No matching stops.")


if __name__ == "__main__":
    main()
