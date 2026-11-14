"""Keeps the board's clock on local time. The clock is only used for the on-screen time;
arrival minutes come straight from the transit API and don't depend on it.

Time sources, in order: NTP via the ESP32 Wi-Fi chip, then the server time
embedded in the last transit API response. No accounts or keys needed.

settings.toml:
  TZ_OFFSET = -5     # standard-time offset from UTC in hours (Cleveland = -5)
  TZ_DST = "US"      # "US" applies US daylight saving rules, "none" disables DST
"""
import os
import time
import rtc

import config

TZ_OFFSET = os.getenv("TZ_OFFSET", -5)
TZ_DST = str(os.getenv("TZ_DST", "US")).upper()

_MIN_VALID = 1700000000  # anything earlier means "no time yet"


def _nth_sunday(year, month, n):
    first_wday = time.localtime(time.mktime((year, month, 1, 0, 0, 0, 0, -1, -1))).tm_wday  # Mon=0
    return 1 + (6 - first_wday) % 7 + 7 * (n - 1)


def utc_offset_seconds(utc):
    offset = int(TZ_OFFSET)
    if TZ_DST == "US":
        year = time.localtime(utc).tm_year
        # DST: 2:00 local standard time on the 2nd Sunday of March,
        # until 2:00 local daylight time (= 1:00 standard) on the 1st Sunday of November
        start = time.mktime((year, 3, _nth_sunday(year, 3, 2), 2, 0, 0, 0, -1, -1)) - offset * 3600
        end = time.mktime((year, 11, _nth_sunday(year, 11, 1), 1, 0, 0, 0, -1, -1)) - offset * 3600
        if start <= utc < end:
            offset += 1
    return offset * 3600


def set_from_utc(utc):
    rtc.RTC().datetime = time.localtime(int(utc) + utc_offset_seconds(int(utc)))


def sync(esp, transit=None, tries=5):
    """Set the clock. Returns True if it was set."""
    for _ in range(tries):
        try:
            utc = esp.get_time()[0]
            if utc > _MIN_VALID:
                set_from_utc(utc)
                print("Clock set from NTP:", now_text())
                return True
        except (OSError, ValueError, RuntimeError) as e:
            print("NTP not ready:", e)
        time.sleep(1)
    if transit is not None and transit.server_utc:
        utc, stamp = transit.server_utc
        set_from_utc(utc + (time.monotonic() - stamp))
        print("Clock set from transit server time:", now_text())
        return True
    print("Clock not set")
    return False


def is_set():
    return time.localtime().tm_year >= 2024


def now_text():
    t = time.localtime()
    hour = t.tm_hour if config.CLOCK_24H else (t.tm_hour % 12 or 12)
    return "%d:%02d" % (hour, t.tm_min)
