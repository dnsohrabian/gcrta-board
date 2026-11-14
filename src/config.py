# Transit board configuration: the only file most people need to edit.
# Wi-Fi password and API key live in settings.toml (see settings.toml.example).
#
# HOW TO FIND YOUR STOPS
#   The "stop" is the stop number printed on the bus-stop sign, also shown in the Transit app.
#   Or, on a computer:  python tools/find_stops.py "lorain w 117"   (searches every GCRTA stop)
#   Bus stops are one direction only, so use the stop on the side of the street you board from.
#   Rail stations have a separate stop number for each platform/direction.
#
# Each arrival entry:
#   "stop"   : stop number (int or str)                                    REQUIRED
#   "route"  : route as GCRTA writes it, e.g. "22", "26", "RL"           REQUIRED
#   "label"  : text in the colored route badge, 1-2 characters            (default: route)
#   "color"  : badge color, 0xRRGGBB                                       (default: gray)
#   "min_minutes": hide arrivals sooner than this, i.e. buses you can't make (default: MIN_MINUTES)
#   "headsign": only count trips whose destination contains this text, e.g. "airport" (optional)
# The destination shown next to the badge comes from the live data (e.g. "WESTGATE TC").

# Route badge colors. Similar brightness so no badge glows, and distinct for color-blind
# viewers too (blue is lighter than magenta, orange lighter than red).
BLUE, MAGENTA, GREEN, ORANGE, RED = 0x30A8FF, 0xC848C8, 0x20A040, 0xFF9020, 0xE0202C

# ---------------------------------------------------------------------------
# PAGES: the board rotates through these. Each page shows its 3 soonest routes.
# These are Ohio City stops (Lorain & Fulton, Detroit & W 38th). Replace them with your own.
# ---------------------------------------------------------------------------
PAGES = [
    {
        "title": "INBOUND",  # toward downtown
        "arrivals": [
            {"stop": 5810, "route": "22", "color": BLUE},                            # Lorain & Fulton
            {"stop": 4774, "route": "45", "color": MAGENTA},                         # Fulton & Lorain
            {"stop": 11355, "route": "26", "color": GREEN},                          # Detroit & W 38th
            {"stop": 11355, "route": "71", "color": ORANGE},                         # Detroit & W 38th
            {"stop": 28902, "route": "RL", "color": RED, "min_minutes": 10},         # W 25th-Ohio City
        ],
    },
    {
        "title": "OUTBOUND",
        "arrivals": [
            {"stop": 5811, "route": "22", "color": BLUE},                            # Lorain & Fulton Pl
            {"stop": 10847, "route": "45", "color": MAGENTA},                        # Fulton & Lorain
            {"stop": 3447, "route": "26", "color": GREEN},                           # Detroit & W 38th
            {"stop": 3447, "route": "71", "color": ORANGE},                          # Detroit & W 38th
            {"stop": 28901, "route": "RL", "color": RED, "min_minutes": 10},         # W 25th-Ohio City
        ],
    },
]

# ---------------------------------------------------------------------------
# Behaviour
# ---------------------------------------------------------------------------
AGENCY = "cleveland"     # Swiftly agency key (GCRTA = "cleveland")
MIN_MINUTES = 4          # default cutoff: hide arrivals sooner than this
TIMES_PER_ROW = 1        # 1: next arrival only, large  |  2: next two, e.g. "5,31", smaller
PAGE_SECONDS = 8         # how long each page stays on screen
FETCH_SECONDS = 30       # how often each stop is refreshed (GCRTA data updates ~every 30 s)
STALE_SECONDS = 180      # drop a stop's data if it couldn't be refreshed for this long
CLOCK_SYNC_HOURS = 6     # how often to re-sync the clock from the internet
CLOCK_24H = True         # 15:53 (True) or 3:53 (False)
DEBUG = True             # print fetch timings and free memory to the serial console

# ---------------------------------------------------------------------------
# Display (64x32 panel; the layout is described at the top of screen.py)
# ---------------------------------------------------------------------------
BIT_DEPTH = 5            # color depth 1-6; higher = smoother colors, more CPU spent on the panel
FONT = "lib/5x7.bdf"     # minutes (TIMES_PER_ROW = 1) and messages
SMALL_FONT = "lib/4x6.bdf"  # everything else
# Colors are 0xRRGGBB as on a computer screen; the board gamma-corrects them for the LEDs.
# Brightness sets importance and color sets kind: a dim header, bright neutral words,
# amber numbers. Route color lives only in the badges.
TITLE_COLOR = 0x5878B0   # page title (dim, so it reads as a header)
CLOCK_COLOR = 0x5878B0   # same as the title: one header strip
DEST_COLOR = 0xC0C0C0    # destination text
TIME_COLOR = 0xFFB000    # minutes
MESSAGE_COLOR = 0xFFB000 # "NO DATA", "NONE SOON", "CONNECTING"
