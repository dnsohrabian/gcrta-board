# Transit arrivals board for the Adafruit Matrix Portal M4 (CircuitPython 10).
# Edit config.py for stops and display options, settings.toml for Wi-Fi and API key.
import gc
import os
import time

import board
import busio
import supervisor
from digitalio import DigitalInOut
import adafruit_connection_manager
import adafruit_requests
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

pool = adafruit_connection_manager.get_radio_socketpool(esp)
ssl_context = adafruit_connection_manager.get_radio_ssl_context(esp)
session = adafruit_requests.Session(pool, ssl_context)


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
    adafruit_connection_manager.connection_manager_close_all(pool)
    esp.reset()
    if not connect(max_tries=10):
        print("Wi-Fi did not come back; reloading")
        supervisor.reload()


connect()

# ------------------------------------------------------------------ main loop
arrivals = transit.Transit(session, api_key, reconnect)
clock.sync(esp)

page_index = len(pages) - 1
next_page = 0.0
next_draw = 0.0
next_clock_sync = time.monotonic() + config.CLOCK_SYNC_MINUTES * 60
RELOAD_AFTER_SECONDS = 600  # no successful fetch for this long -> soft reset

while True:
    now = time.monotonic()

    # 1. Refresh at most one stop per pass so the display keeps rotating. A fetch blocks
    #    for a second or two, so wait until no destination is mid-scroll.
    if arrivals.busy(now) and display.resting():
        display.set_busy(True)
        if arrivals.refresh_next(now):
            next_draw = 0  # show new data right away
        display.set_busy(False)
        display.resume()
        now = time.monotonic()
        if now - arrivals.last_success > RELOAD_AFTER_SECONDS:
            print("No data for %d s; reloading" % RELOAD_AFTER_SECONDS)
            supervisor.reload()

    # 2. Rotate pages, after every long destination on this one has scrolled once
    if now >= next_page and display.scrolled_all():
        page_index = (page_index + 1) % len(pages)
        next_page = now + config.PAGE_SECONDS
        next_draw = 0

    # 3. Redraw (also every few seconds so minutes count down)
    if now >= next_draw:
        page = pages[page_index]
        rows, status = arrivals.rows(page, now, screen.ROWS)
        display.show_page(page["title"], rows, status)
        display.set_clock(clock.now_text() if clock.is_set() else "")
        next_draw = now + 5

    # 4. Keep the clock honest. The board's own clock drifts by minutes a day; the ESP32
    #    keeps accurate NTP time, and asking it is quick.
    if (now >= next_clock_sync or (not clock.is_set() and arrivals.server_utc)) and display.resting():
        clock.sync(esp, arrivals, tries=1)
        next_clock_sync = now + config.CLOCK_SYNC_MINUTES * 60
        next_draw = 0  # show the corrected time

    # 5. Scroll long destinations, then sleep until the next pixel step is due so every
    #    step lasts the same time
    time.sleep(min(display.scroll(), 0.1))
