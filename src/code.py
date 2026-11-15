# Transit arrivals board for the Adafruit Matrix Portal M4 (CircuitPython 10).
# Edit config.py for stops and display options, settings.toml for Wi-Fi and API key.
import gc
import os
import time

import board
import busio
import supervisor
from digitalio import DigitalInOut
from adafruit_esp32spi import adafruit_esp32spi

import config
import clock
import screen
import transit

# ------------------------------------------------------------------ settings
ssid = os.getenv("CIRCUITPY_WIFI_SSID")
password = os.getenv("CIRCUITPY_WIFI_PASSWORD")
if not ssid:
    raise RuntimeError("Set CIRCUITPY_WIFI_SSID and CIRCUITPY_WIFI_PASSWORD in settings.toml")
api_key = os.getenv("SWIFTLY_API_KEY")
if not api_key:
    raise RuntimeError("Set SWIFTLY_API_KEY in settings.toml (see settings.toml.example)")

# ------------------------------------------------------------------ display
pages = config.PAGES
display = screen.Screen()
display.show_message("GCRTA-BOARD", "CONNECTING")

# ------------------------------------------------------------------ Wi-Fi
esp32_cs = DigitalInOut(board.ESP_CS)
esp32_ready = DigitalInOut(board.ESP_BUSY)
esp32_reset = DigitalInOut(board.ESP_RESET)
spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)
print("ESP32 firmware:", esp.firmware_version)


def connect(max_tries=None):
    tries = 0
    while not esp.is_connected:
        tries += 1
        try:
            esp.connect_AP(ssid, password)
        except (OSError, RuntimeError, ConnectionError) as e:
            print("Wi-Fi connect failed (%d): %r" % (tries, e))
            if max_tries and tries >= max_tries:
                return False
            time.sleep(2)
    print("Connected to", esp.ap_info.ssid, "RSSI", esp.ap_info.rssi)
    return True


def reconnect():
    print("Resetting Wi-Fi")
    display.set_busy(True)
    arrivals.close()
    esp.reset()
    if not connect(max_tries=10):
        print("Wi-Fi did not come back; reloading")
        supervisor.reload()


connect()

# ------------------------------------------------------------------ main loop
arrivals = transit.Transit(esp, api_key, reconnect)
clock.sync(esp)

page_index = len(pages) - 1
next_page = 0.0
next_draw = 0.0
next_clock_sync = time.monotonic() + config.CLOCK_SYNC_MINUTES * 60
RELOAD_AFTER_SECONDS = 600  # no successful fetch for this long -> soft reset
STEP_BUDGET = 0.045  # s: do other work only when this much time is left before the next scroll step

while True:
    # Scroll first, the moment the step is due, then use the time until the next step
    # for at most one other short job, so nothing ever delays the motion.
    step_due = time.monotonic() + display.scroll()
    now = time.monotonic()

    if now - arrivals.last_success > RELOAD_AFTER_SECONDS:
        print("No data for %d s; reloading" % RELOAD_AFTER_SECONDS)
        supervisor.reload()

    if step_due - now < STEP_BUDGET:
        pass  # no time for anything else before the next step

    # Rotate pages, after every long destination on this one has gone round once
    elif now >= next_page and display.scrolled_all():
        page_index = (page_index + 1) % len(pages)
        next_page = now + config.PAGE_SECONDS
        next_draw = 0
        continue  # draw it right away

    # Redraw (also every few seconds so minutes count down)
    elif now >= next_draw:
        page = pages[page_index]
        rows, status = arrivals.rows(page, now, screen.ROWS)
        display.show_page(page["title"], rows, status)
        display.set_clock(clock.now_text() if clock.is_set() else "")
        next_draw = now + 5

    # One short piece of the request in flight (see transit.py)
    elif arrivals.fetching():
        if arrivals.poll():
            next_draw = 0  # show new data right away
        if not arrivals.fetching():
            display.set_busy(False)

    # Start refreshing the next stop that is due. Quick on an open connection; opening
    # one blocks for ~2 s, so that waits until nothing is moving.
    elif arrivals.due(now) and (arrivals.connected() or display.resting()):
        display.set_busy(True)
        blocking = not arrivals.connected()
        arrivals.start(now)
        if blocking:
            display.resume()
        if not arrivals.fetching():
            display.set_busy(False)

    # Keep the clock honest. The board's own clock drifts by minutes a day; the ESP32
    # keeps accurate NTP time, and asking it is quick.
    elif (now >= next_clock_sync or (not clock.is_set() and arrivals.server_utc)) and display.resting():
        clock.sync(esp, arrivals, tries=1)
        next_clock_sync = now + config.CLOCK_SYNC_MINUTES * 60
        next_draw = 0  # show the corrected time

    # Collect garbage (~17 ms) now, before Python does it at a random moment
    elif gc.mem_free() < 24000:
        gc.collect()

    # Sleep until the next step; check back sooner while there is work waiting
    busy = arrivals.fetching() or arrivals.due(now)
    time.sleep(max(0, min(step_due - time.monotonic(), 0.01 if busy else 0.1)))
