# gcrta-board
`A real-time LED transit arrival board for Clevelanders`

Live GCRTA bus and rail arrivals on a 64x32 LED matrix, driven by an
[Adafruit Matrix Portal M4](https://www.adafruit.com/product/4745) running CircuitPython 10.
It started as a Cleveland version of the [dc-metro](https://github.com/metro-sign/dc-metro) board.

![The board showing outbound arrivals](img/Example1.jpg)

Each row shows a colored route badge, the destination (long names scroll) and the minutes
until the next arrival. Set `TIMES_PER_ROW = 2` to show the next two, like "15,29".
Pages rotate between groups of stops, e.g. inbound and outbound.

## Quick start
1. Get a Matrix Portal M4 and a 64x32 LED panel ([Hardware](#hardware)).
2. Install CircuitPython 10 and update the Wi-Fi chip's firmware to NINA 3.x ([Setup](#setup)).
3. Copy `src/` onto the `CIRCUITPY` drive, rename `settings.toml.example` to
   `settings.toml` and add your Wi-Fi.
4. Find your stop numbers: `python tools/find_stops.py lorain fulton`
   ([Find your stop numbers](#1-find-your-stop-numbers)).
5. Put them in `PAGES` in `config.py`, and set `min_minutes` to your walk to each stop
   ([Setting up your stops](#setting-up-your-stops)).

## Contents
- [Hardware](#hardware)
- [Setup](#setup)
- [Setting up your stops](#setting-up-your-stops)
  - [1. Find your stop numbers](#1-find-your-stop-numbers)
  - [2. Build your pages](#2-build-your-pages)
  - [3. Set walking-time cutoffs](#3-set-walking-time-cutoffs-with-min_minutes)
  - [Filtering by destination](#filtering-by-destination-with-headsign)
  - [Board-wide options](#board-wide-options)
  - [Checking your config](#checking-your-config)
- [How it behaves](#how-it-behaves)
- [Files](#files)
- [Credits](#credits)

## Hardware
- An [Adafruit Matrix Portal M4](https://www.adafruit.com/product/4745), a small computer
  with Wi-Fi that drives the panel
- A **64x32 RGB LED matrix** that works with the Matrix Portal:
  [3 mm](https://www.adafruit.com/product/2279), [4 mm](https://www.adafruit.com/product/2278),
  [5 mm](https://www.adafruit.com/product/2277) or [6 mm](https://www.adafruit.com/product/2276)
  pitch. Smaller pitch means a smaller, sharper board; 6 mm is about 15" x 7.5".
- A **USB-C power supply** (a 15 W phone charger is plenty for this display) and cable

## Setup
1. [Prepare the Matrix Portal and panel](https://learn.adafruit.com/adafruit-matrixportal-m4/prep-the-matrixportal)
   with Adafruit's guide.
2. [Install CircuitPython 10.x](https://circuitpython.org/board/matrixportal_m4/).
3. **Update the Wi-Fi chip's firmware to NINA 3.x.** Older firmware (1.7.x) can't make a
   secure connection to the Swiftly server, so every request fails with "ESP32 not
   responding". The board prints its firmware version to the serial console at startup.
   See Adafruit's [ESP32 firmware guide](https://learn.adafruit.com/upgrading-esp32-firmware).
4. Copy everything inside `src/` onto the `CIRCUITPY` drive, including the `lib` folder.
   `src/lib` holds the fonts and the CircuitPython 10 libraries the board needs.
5. Add your Wi-Fi. `settings.toml.example` is a template: on the `CIRCUITPY` drive,
   rename it to `settings.toml`, open it in any text editor and fill in your Wi-Fi:
   ```toml
   CIRCUITPY_WIFI_SSID = "your-network-name"      # your Wi-Fi network name
   CIRCUITPY_WIFI_PASSWORD = "your-wifi-password"
   ```
   - **API key:** already filled in. It's the key GCRTA publishes for public use.
   - **Time zone:** leave `TZ_OFFSET` and `TZ_DST` alone if you're on US Eastern time.

   `settings.toml` stays on your board; don't commit it or share it.

   > **Upgrading from an older version?** It kept Wi-Fi details in `secrets.py`, which is no
   > longer used. Move your network name and password into `settings.toml`, then delete
   > `secrets.py` from the drive. The Adafruit IO account is no longer needed either.
6. Edit `config.py` to use your stops (see [Setting up your stops](#setting-up-your-stops)). The board restarts
   whenever you save a file.

The drive should look like this:
```
CIRCUITPY
├── code.py  config.py  transit.py  clock.py  screen.py
├── settings.toml
└── lib/
```

## Setting up your stops
Everything about what the board shows lives in `src/config.py` (or `config.py` on the
`CIRCUITPY` drive). The example that ships with it shows Ohio City stops. Replace them with
your own in three steps:

1. Find the stop numbers you use.
2. Group them into pages, such as "INBOUND" and "OUTBOUND".
3. Set a walking-time cutoff, so the board skips buses you can't reach in time.

### 1. Find your stop numbers
A stop number is printed on the bus-stop sign and shown in the Transit app. Bus stops serve
one direction only, so use the stop on the side of the street you board from. At a rail
station, each platform has its own stop number.

You can also search every GCRTA stop from your computer (Python 3.8+, no packages needed):

```
python tools/find_stops.py lorain fulton             # stops whose name contains both words
python tools/find_stops.py lorain --route 22         # only stops served by route 22
python tools/find_stops.py 5810 --live               # live arrivals at stop 5810 right now
```

Each match lists its stop number, a map link, and every route that stops there with the
destination it heads toward:

```
stop 28902  W 25TH ST-OHIO CITY STATION   (map: https://maps.google.com/?q=41.484709,-81.701188)
    route RL         toward: Red Line - E. 55th Street
    route RL         toward: Red Line - Stokes / Windermere
    route RL         toward: Red Line - Tower City / Public Square
```

Use the map link to make sure you have the right side of the street. The first run
downloads GCRTA's schedule data (about 18 MB), and later runs are instant.

`--live` needs the API key. It reads the key from a `settings.toml` in the repo root,
`src/` or `tools/`, or you can pass it with `--key`. The key is already in
`src/settings.toml.example`.

### 2. Build your pages
`PAGES` is a list of pages, and the board rotates through them. Each page has a `title` and
a list of `arrivals`. Each entry in `arrivals` is one route at one stop:

```python
PAGES = [
    {
        "title": "TO WORK",
        "arrivals": [
            {"stop": 5810, "route": "22", "color": BLUE},
            {"stop": 11355, "route": "26", "color": GREEN},
            {"stop": 11355, "route": "71", "color": ORANGE},  # same stop, second route
        ],
    },
    {
        "title": "HOME",
        "arrivals": [
            {"stop": 5811, "route": "22", "color": BLUE},
            {"stop": 3447, "route": "26", "color": GREEN},
        ],
    },
]
```

- **Title:** shown in the top-left corner. It has room for about 10 characters.
- **One entry per route:** if two routes stop at the same stop, add one entry for each.
- **3 rows per page:** a page can list any number of entries. The board shows the 3 with the
  soonest arrivals and sorts them soonest first.
- **One page is fine:** if everything fits on one page, use a single page and the board
  won't rotate.

**Arrival entry options**

| Key | Required | What it does | Example |
|---|---|---|---|
| `stop` | yes | Stop number from the sign or `find_stops.py` | `5810` |
| `route` | yes | Route as GCRTA writes it. `"26"` also matches the `26-26A` variant. | `"22"`, `"RL"`, `"HL"` |
| `color` | no | Badge color, `0xRRGGBB` or one of the named colors at the top of `config.py`. Default: gray. | `BLUE`, `0x30A8FF` |
| `label` | no | Badge text, 1-2 characters. Default: the route. | `"R"` |
| `min_minutes` | no | Hide arrivals sooner than this many minutes. Default: `MIN_MINUTES` (4). | `10` |
| `headsign` | no | Only count trips whose destination contains this text (not case-sensitive) | `"airport"` |

The destination next to the badge (such as "WESTGATE TC") comes from the live data. You
don't set it.

### 3. Set walking-time cutoffs with `min_minutes`
There's no point showing a bus that leaves in 2 minutes if the stop is a 5-minute walk
away. The board hides any arrival sooner than the cutoff and shows the next one you can
make instead.

- **One default:** `MIN_MINUTES` near the bottom of `config.py` applies to every entry
  (default `4`). Set it to your walk to the nearest stop.
- **Per entry:** add `"min_minutes"` to a stop that's farther away. It overrides the
  default for that entry only.
- **Show everything:** set `"min_minutes": 0`.

```python
MIN_MINUTES = 3   # the bus stops on my corner are 3 minutes away

{"stop": 5810, "route": "22", "color": BLUE},                       # uses MIN_MINUTES (3)
{"stop": 28902, "route": "RL", "color": RED, "min_minutes": 10},    # rail station is a 10-minute walk
```

Minutes are rounded down, and an arrival exactly at the cutoff is shown. With
`"min_minutes": 10`, a train 10½ minutes away shows as `10`, and one 9 minutes away is
hidden.

If every arrival on a page is under its cutoff, the page reads `NONE SOON`. If you see that
often, the cutoff may be too high.

### Filtering by destination with `headsign`
Some routes send trips from the same stop to different places, such as a branch or a trip
that ends partway along the route. To show only the trips you want, add `"headsign"` with
part of the destination name. `find_stops.py` lists each route's destinations after
"toward:".

```python
# Inbound Red Line at W 25th: only trains going past downtown to Windermere,
# skipping the ones that end at Tower City or E. 55th
{"stop": 28902, "route": "RL", "color": RED, "headsign": "windermere"},
```

To show both branches as separate rows, add two entries with different `headsign` values,
and give them different `label`s so you can tell them apart.

### Board-wide options
These are near the bottom of `config.py`. The defaults work for most boards; the one you're
most likely to change is `MIN_MINUTES`.

<details>
<summary>All board-wide settings</summary>

| Setting | Default | What it does |
|---|---|---|
| `MIN_MINUTES` | `4` | Default walking-time cutoff for every entry (see above) |
| `TIMES_PER_ROW` | `1` | `1` shows the next arrival in large digits. `2` shows the next two, like "15,29", in smaller digits with less room for the destination. |
| `PAGE_SECONDS` | `8` | How long each page stays up. A page with a long destination stays until the name has scrolled around once. |
| `FETCH_SECONDS` | `30` | How often each stop is refreshed. GCRTA's data updates about every 30 s, so going lower doesn't help. |
| `STALE_SECONDS` | `180` | A stop that can't be refreshed for this long drops off the board instead of showing old times |
| `CLOCK_24H` | `True` | `True` shows 15:53, `False` shows 3:53 |
| `CLOCK_SYNC_MINUTES` | `10` | How often the clock re-syncs |
| `DEBUG` | `True` | Print request timings and free memory to the serial console |
| `BIT_DEPTH` | `5` | Color depth, 1-6 |
| `TITLE_COLOR`, `CLOCK_COLOR`, `DEST_COLOR`, `TIME_COLOR`, `MESSAGE_COLOR` | | Text colors, `0xRRGGBB` |

</details>

The time zone is set in `settings.toml`, not `config.py` (see Setup).

### Checking your config
- **Mistakes in `config.py`:** it is Python, so a missing comma, quote or bracket stops the
  board from starting. Connect to the [serial console](https://learn.adafruit.com/welcome-to-circuitpython/kattni-connecting-to-the-serial-console)
  to see the error and the line it's on.
- **Testing a stop:** before putting a stop on the board, run
  `python tools/find_stops.py <stop> --live --route <route>`. If it lists arrivals, the board
  will show them too, as long as they're past your cutoff.
- **A row never appears:** check the stop number (right side of the street?) and the
  `route` text, and make sure `headsign` matches part of a destination listed by
  `find_stops.py`.

## How it behaves
<details>
<summary>Refresh, scrolling, messages, clock and recovery</summary>

- **Refresh:** each stop is refreshed every `FETCH_SECONDS` (30 s by default), one at a
  time, and each request returns a few KB of JSON. Requests run in small pieces between scroll steps, so text keeps moving while data
  loads. A small dot left of the clock lights up during a request.
- **Scrolling:** destinations too long for their space pause briefly, then loop
  continuously. A page stays up until its longest destination has gone around once.
- **Countdown:** minutes count down on the board between refreshes.
- **Stale data:** a stop that can't be refreshed for `STALE_SECONDS` drops off rather than
  showing stale times.
- **Messages:** `NO DATA` means nothing has loaded yet. `NONE SOON` means data loaded but no
  arrivals passed the cutoffs.
- **Clock:** set from NTP through the Wi-Fi chip, with the Swiftly server time as a fallback.
  US daylight saving time is handled automatically.
- **Recovery:** after repeated failures the board resets Wi-Fi. If no data arrives for
  10 minutes, it soft-reloads.
- **Debugging:** with `DEBUG = True`, the serial console shows each request's time, the
  free memory and how smoothly text is scrolling.

</details>

## Files
<details>
<summary>What each file does</summary>

| File | Purpose |
|---|---|
| `src/code.py` | Startup, Wi-Fi, main loop |
| `src/config.py` | Your stops and display options |
| `src/transit.py` | Fetches and filters Swiftly predictions |
| `src/screen.py` | LED matrix layout |
| `src/clock.py` | Time sync and time zone |
| `src/settings.toml.example` | Template for Wi-Fi and API key (your copy stays private) |
| `src/lib/` | Fonts and CircuitPython 10 libraries |
| `tools/find_stops.py` | Stop finder, runs on your computer |
| `tools/preview.py` | For developers changing `screen.py`: draws the screen to a PNG on your computer |

</details>

## Credits
Arrival data is provided by the Greater Cleveland Regional Transit Authority (GCRTA)
through [Swiftly](https://www.goswift.ly/), its real-time data provider, under GCRTA's
[developer license](https://www.riderta.com/developers). This project is not affiliated
with or endorsed by GCRTA.

CircuitPython is a friendly version of Python for small devices, made by
[Adafruit](https://www.adafruit.com/), who make and sell educational and hobby electronics,
publish great guides, and are a woman-owned business in NYC. Check them out.
