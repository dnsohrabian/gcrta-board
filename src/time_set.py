from config import config
import adafruit_requests as requests
import gc
import rtc
import time

time_format = "%Y-%m-%d %H:%M:%S.%L %j %u %z %Z"
time_zone = config['timezone']

TIME_SERVICE = (
    "https://io.adafruit.com/api/v2/%s/integrations/time/strftime?x-aio-key=%s"
)

def url_encode(url):
    """
    A function to perform minimal URL encoding
    """
    url = url.replace(" ", "+")
    url = url.replace("%", "%25")
    url = url.replace(":", "%3A")
    return url

def get_strftime(time_format= time_format, location=time_zone):
    """
    Fetch a custom strftime relative to your location.
    :param str location: Your city and country, e.g. ``"America/New_York"``.
    """
    # pylint: disable=line-too-long
    api_url = None
    reply = None
    try:
        aio_username = config["aio_username"]
        aio_key = config["aio_key"]
    except KeyError:
        raise KeyError(
            "\n\nOur time service requires a login/password to rate-limit. Please register for a free adafruit.io account and place the user/key in your secrets file under 'aio_username' and 'aio_key'"  # pylint: disable=line-too-long
        ) from KeyError

    if location:
        print("Getting time for timezone", location)
        api_url = (TIME_SERVICE + "&tz=%s") % (aio_username, aio_key, location)
    else:  # we'll try to figure it out from the IP address
        print("Getting time from IP address")
        api_url = TIME_SERVICE % (aio_username, aio_key)
    api_url += "&fmt=" + url_encode(time_format)

    try:
        response = requests.get(api_url, timeout=10)
        if response.status_code != 200:
            print(response)
            error_message = (
                "Error connecting to Adafruit IO. The response was: "
                + response.text
            )
            raise RuntimeError
        reply = response.text
    except KeyError:
        raise KeyError(
            "Was unable to lookup the time, try setting secrets['timezone'] according to http://worldtimeapi.org/timezones"  # pylint: disable=line-too-long
        ) from KeyError
    # now clean up
    response.close()
    response = None
    gc.collect()

    return reply


def get_local_time(loc=time_zone):
    # pylint: disable=line-too-long
    """
    Fetch and "set" the local time of this microcontroller to the local time at the location, using an internet time API.
    :param str location: Your city and country, e.g. ``"America/New_York"``.
    """
    reply = get_strftime(time_format, location=loc)
    if reply:
        times = reply.split(" ")
        the_date = times[0]
        the_time = times[1]
        year_day = int(times[2])
        week_day = int(times[3])
        is_dst = None  # no way to know yet
        year, month, mday = [int(x) for x in the_date.split("-")]
        the_time = the_time.split(".")[0]
        hours, minutes, seconds = [int(x) for x in the_time.split(":")]
        now = time.struct_time(
            (year, month, mday, hours, minutes, seconds, week_day, year_day, is_dst)
        )

        if rtc is not None:
            rtc.RTC().datetime = now

    return reply
