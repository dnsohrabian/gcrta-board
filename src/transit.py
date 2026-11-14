"""Real-time arrivals from Swiftly, GCRTA's official real-time data provider.

Each configured stop is one small request (~1-6 KB of JSON). Stops are refreshed one
at a time so the display never freezes for long. Arrivals are stored as
time.monotonic() deadlines, so minutes count down between fetches and do not
depend on the board's clock.
"""
import gc
import time

import config

URL = "https://api.goswift.ly/real-time/%s/predictions?stop=%s&number=%d"
FETCHED = 4  # arrivals requested per route and destination, extra in case some are under the cutoff


def _norm(route):
    return str(route).strip().upper()


def _destination(headsign):
    """'Lorain To Westgate Tc' -> 'WESTGATE TC', 'Red Line - Airport' -> 'AIRPORT'."""
    h = headsign.upper()
    for sep in (" TO ", " - "):
        if sep in h:
            return h.split(sep)[-1].strip()
    return h.strip()


def _matches(wanted, route):
    """True if a configured route ("26", "26-26A", "RL", "66") names this Swiftly route."""
    short = _norm(route.get("routeShortName", ""))
    return wanted in (short, short.split("-")[0], _norm(route.get("routeId", "")))


class Stop:
    def __init__(self, stop_id):
        self.id = stop_id
        self.routes = set()  # configured routes at this stop (normalized)
        self.arrivals = {}   # route -> [(deadline, headsign_lower, destination), ...]
        self.due = 0.0       # monotonic time of the next fetch
        self.loaded = None   # monotonic time of the last successful fetch

    def fresh(self, now):
        return self.loaded is not None and now - self.loaded <= config.STALE_SECONDS


class Transit:
    def __init__(self, session, api_key, on_network_trouble):
        self.session = session
        self.headers = {"Authorization": api_key}
        self.on_network_trouble = on_network_trouble  # called after repeated failures
        self.failures = 0
        self.last_success = time.monotonic()
        self.server_utc = None  # (utc_seconds, monotonic) from the latest response
        self.stops = {}
        for page in config.PAGES:
            for a in page["arrivals"]:
                stop_id = str(a["stop"])
                self.stops.setdefault(stop_id, Stop(stop_id)).routes.add(_norm(a["route"]))
        self._queue = list(self.stops.values())

    def refresh_next(self, now):
        """Fetch the next stop that is due, if any. Returns True if new data arrived."""
        for stop in self._queue:
            if stop.due <= now:
                self._queue.remove(stop)
                self._queue.append(stop)  # round-robin
                return self._fetch(stop)
        return False

    def busy(self, now):
        return any(stop.due <= now for stop in self._queue)

    def _fetch(self, stop):
        start = time.monotonic()
        payload = None
        try:
            url = URL % (config.AGENCY, stop.id, FETCHED)
            r = self.session.get(url, headers=self.headers, timeout=15)
            try:
                if r.status_code == 200:
                    payload = r.json()
                else:
                    print("Stop %s: HTTP %d %s" % (stop.id, r.status_code, r.text[:100]))
            finally:
                r.close()
        except Exception as e:  # pylint: disable=broad-except
            # network errors, adafruit_requests' own exceptions, bad JSON, low memory
            print("Stop %s: %r" % (stop.id, e))

        now = time.monotonic()
        if payload is None:
            self.failures += 1
            stop.due = now + min(config.FETCH_SECONDS, 10 * self.failures)  # back off
            if self.failures % 3 == 0:
                self.on_network_trouble()
            return False

        self.failures = 0
        self.last_success = stop.loaded = now
        stop.due = now + config.FETCH_SECONDS
        try:
            stop.arrivals = self._parse(stop, payload["data"]["predictionsData"], now)
        except (KeyError, TypeError) as e:
            print("Stop %s: unexpected response (%r)" % (stop.id, e))
        payload = None
        gc.collect()
        if config.DEBUG:
            print("Stop %s: %d ms, free %d B" % (stop.id, (now - start) * 1000, gc.mem_free()))
        return True

    def _parse(self, stop, routes, now):
        arrivals = {route: [] for route in stop.routes}
        for route in routes:
            for wanted in stop.routes:
                if not _matches(wanted, route):
                    continue
                for dest in route["destinations"]:
                    headsign = dest.get("headsign", "")
                    name, headsign = _destination(headsign), headsign.lower()
                    for p in dest["predictions"]:
                        arrivals[wanted].append((now + p["sec"], headsign, name))
                        # "time" (arrival, UTC) minus "sec" (seconds away) is the server's clock
                        self.server_utc = (p["time"] - p["sec"], now)
        return arrivals

    def rows(self, page, now, limit):
        """Up to `limit` rows for one page, soonest first, and a status:
        ([(label, color, [minutes, ...], destination), ...], status)

        status is None when there are rows, otherwise "NO DATA" (nothing loaded yet)
        or "NONE SOON" (loaded, but no arrivals beyond the cutoffs).
        """
        found, loaded = [], False
        for a in page["arrivals"]:
            stop = self.stops[str(a["stop"])]
            if not stop.fresh(now):
                continue
            loaded = True
            cutoff = a.get("min_minutes", config.MIN_MINUTES)
            only = a.get("headsign", "").lower()
            upcoming = sorted(
                (int((deadline - now) // 60), name)
                for deadline, headsign, name in stop.arrivals.get(_norm(a["route"]), ())
                if only in headsign
            )
            upcoming = [u for u in upcoming if u[0] >= cutoff][: config.TIMES_PER_ROW]
            if upcoming:
                found.append((
                    a.get("label", str(a["route"])),
                    a.get("color", 0x808080),
                    [m for m, _ in upcoming],
                    upcoming[0][1],
                ))
        found.sort(key=lambda row: row[2][0])
        if found:
            return found[:limit], None
        return [], ("NONE SOON" if loaded else "NO DATA")
