"""Real-time arrivals from Swiftly, GCRTA's official real-time data provider.

Each configured stop is one small request (~1-6 KB of JSON). Arrivals are stored as
time.monotonic() deadlines, so minutes count down between fetches and do not depend on
the board's clock.

Fetching never freezes the display for long. Instead of adafruit_requests, which waits
for the whole response, this talks HTTP straight to the ESP32 Wi-Fi chip in small steps:
start() sends a request (~10 ms) and poll(), called between scroll steps, does one
short piece of work: check whether bytes have arrived, read them, or parse the result.
The connection is kept open between requests. Opening one is the only slow step: the
ESP32 does the TLS handshake (~2 s) in a single blocking command, so code.py only
(re)connects while the display is resting.
"""
import gc
import json
import time

import config

HOST = "api.goswift.ly"
PATH = "/real-time/%s/predictions?stop=%s&number=%d"
FETCHED = 4          # arrivals requested per route and destination, extra in case some are under the cutoff
TIMEOUT = 10         # seconds to wait for a complete response
READ_CHUNK = 2048    # bytes per read: a few ms over SPI
_ESTABLISHED = 4     # ESP32 socket state


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


def _unchunk(data):
    """Body of a 'Transfer-Encoding: chunked' response."""
    out, i = [], 0
    while True:
        eol = data.find(b"\r\n", i)
        size = int(data[i:eol].split(b";")[0], 16)
        if not size:
            return b"".join(out)
        out.append(data[eol + 2:eol + 2 + size])
        i = eol + 2 + size + 2


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
    def __init__(self, esp, api_key, on_network_trouble):
        self.esp = esp
        self.api_key = api_key
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

        self._sock = None     # ESP32 socket number of the open connection
        self._stop = None     # stop whose request is in flight
        self._data = b""      # response so far
        self._head = None     # (status, body start, content length or -1 if chunked, close?)
        self._body = None     # complete response body, waiting to be decoded
        self._payload = None  # decoded JSON, waiting to be used
        self._sent = 0.0      # monotonic time the request went out
        self._took = 0        # DEBUG: ms from request to complete response
        self._slowest = 0     # DEBUG: longest poll() step, ms

    # ---------------------------------------------------------------- state
    def due(self, now):
        """True if a stop is due for a refresh and no request is in flight."""
        return self._stop is None and any(stop.due <= now for stop in self._queue)

    def fetching(self):
        return self._stop is not None

    def connected(self):
        """False when the next start() has to open a connection: a ~2 s blocking handshake."""
        return self._sock is not None

    def close(self):
        """Drop the connection, e.g. before the ESP32 is reset."""
        if self._sock is not None:
            try:
                self.esp.socket_close(self._sock)
            except Exception:  # pylint: disable=broad-except
                pass
            self._sock = None
        self._stop, self._data, self._head = None, b"", None
        self._body = self._payload = None

    # ---------------------------------------------------------------- fetching
    def start(self, now):
        """Send the request for the next due stop. Quick (~10 ms) on an open connection.
        Opens the connection first if there is none, which blocks for the TLS handshake."""
        stop = None
        for s in self._queue:
            if s.due <= now:
                stop = s
                break
        if stop is None:
            return
        self._queue.remove(stop)
        self._queue.append(stop)  # round-robin
        self._stop, self._data, self._head = stop, b"", None
        self._body = self._payload = None
        try:
            if self._sock is not None and self.esp.socket_status(self._sock) != _ESTABLISHED:
                # the server closed the idle connection; open a new one
                self.esp.socket_close(self._sock)
                self._sock = None
            if self._sock is None:
                start = time.monotonic()
                self._sock = self.esp.get_socket()
                self.esp.socket_connect(self._sock, HOST, 443, conn_mode=self.esp.TLS_MODE)
                if config.DEBUG:
                    print("Connected to %s: %d ms" % (HOST, (time.monotonic() - start) * 1000))
            # one write: every write is a separate round trip to the ESP32
            request = "GET %s HTTP/1.1\r\nHost: %s\r\nAuthorization: %s\r\nConnection: keep-alive\r\n\r\n" % (
                PATH % (config.AGENCY, stop.id, FETCHED), HOST, self.api_key)
            self.esp.socket_write(self._sock, request.encode())
        except Exception as e:  # pylint: disable=broad-except
            self._fail(e)
            return
        self._sent = time.monotonic()

    def poll(self):
        """Do one short step of the request in flight. Returns True if new data arrived."""
        if self._stop is None:
            return False
        start = time.monotonic_ns()
        try:
            got = self._step()
        except Exception as e:  # pylint: disable=broad-except
            # network errors, bad HTTP or JSON, low memory
            self._fail(e)
            return False
        if config.DEBUG:
            self._slowest = max(self._slowest, (time.monotonic_ns() - start) // 1_000_000)
        return got

    def _step(self):
        """One piece of work, each a few ms to ~25 ms: receive, decode JSON, use the data."""
        if self._payload is not None:
            return self._use()
        if self._body is not None:
            self._payload = json.loads(self._body)
            self._body = None
            return False

        available = self.esp.socket_available(self._sock)
        if not available:
            if time.monotonic() - self._sent > TIMEOUT:
                raise OSError("timed out")
            return False
        self._data += self.esp.socket_read(self._sock, min(available, READ_CHUNK))

        if self._head is None:
            end = self._data.find(b"\r\n\r\n")
            if end < 0:
                return False
            lines = str(self._data[:end], "utf-8").lower().split("\r\n")
            length, close = None, False
            for line in lines[1:]:
                name, _, value = line.partition(":")
                value = value.strip()
                if name == "content-length":
                    length = int(value)
                elif name == "transfer-encoding" and "chunked" in value:
                    length = -1
                elif name == "connection" and value == "close":
                    close = True
            if length is None:
                raise ValueError("response has no length")
            self._head = (int(lines[0].split()[1]), end + 4, length, close)

        status, body_start, length, close = self._head
        if length < 0:
            if not self._data.endswith(b"0\r\n\r\n"):
                return False
            body = _unchunk(self._data[body_start:])
        else:
            if len(self._data) - body_start < length:
                return False
            body = self._data[body_start:body_start + length]

        # the whole response is in
        self._data, self._head = b"", None
        self._took = (time.monotonic() - self._sent) * 1000
        if close:
            self.esp.socket_close(self._sock)
            self._sock = None
        if status != 200:
            raise OSError("HTTP %d %s" % (status, str(body[:100], "utf-8")))
        self._body = body
        return False

    def _use(self):
        stop, payload = self._stop, self._payload
        self._stop = self._payload = None
        now = time.monotonic()
        self.failures = 0
        self.last_success = stop.loaded = now
        stop.due = now + config.FETCH_SECONDS
        try:
            stop.arrivals = self._parse(stop, payload["data"]["predictionsData"], now)
        except (KeyError, TypeError) as e:
            print("Stop %s: unexpected response (%r)" % (stop.id, e))
        if config.DEBUG:
            print("Stop %s: %d ms, longest step %d ms, free %d B" % (stop.id, self._took, self._slowest, gc.mem_free()))
            self._slowest = 0
        return True

    def _fail(self, error):
        stop = self._stop
        print("Stop %s: %r" % (stop.id if stop else "?", error))
        self.close()  # start over on a fresh connection
        self.failures += 1
        if stop is not None:
            stop.due = time.monotonic() + min(config.FETCH_SECONDS, 10 * self.failures)  # back off
        if self.failures % 3 == 0:
            self.on_network_trouble()

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
