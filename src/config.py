from adafruit_bitmap_font import bitmap_font
from secrets import secrets

"""Insert the NextConnect request dictionaries for your chosen routes.
At the NextConnect url, can look at Developer Mode in Chrome (Ctrl+Shft+I), go to Network tab, set it
up for the stop you want, then click on the 'getStopTimes' request, and look
at Payload tab to see what their API is calling. Add it as a dict below for each route you set up below for the 'params'
key in each route.
"""

# These are dicts of POST payload data for specific transit stops. The transit authority API uses this structure.

route_1 = {
    "route_name": "22-E",
    "route_color": 0x0011AA,
    "params": {
        "routeID": 139,
        "directionID": 3,
        "stopID": 13363,
        "tpID": 0,
        "useArrivalTimes": "false",
    },
    "cutoff": 5,
}
route_2 = {
    "route_name": "45-E",
    "route_color": 0xA81995,
    "params": {
        "routeID": 60,
        "directionID": 5,
        "stopID": 12925,
        "tpID": 0,
        "useArrivalTimes": "false",
    },
    "cutoff": 5,
}
route_3 = {
    "route_name": "26-E",
    "route_color": 0x22CF19,
    "params": {
        "routeID": 165,
        "directionID": 3,
        "stopID": 1342,
        "tpID": 0,
        "useArrivalTimes": "false",
    },
    "cutoff": 5,
}
route_4 = {
    "route_name": "71-E",
    "route_color": 0xDE4E00,
    "params": {
        "routeID": 193,
        "directionID": 5,
        "stopID": 1342,
        "tpID": 0,
        "useArrivalTimes": "false",
    },
    "cutoff": 5,
}
route_5 = {
    "route_name": "RL-E",
    "route_color": 0xDD0000,
    "params": {
        "routeID": 147,
        "directionID": 3,
        "stopID": 16125,
        "tpID": 919,
        "useArrivalTimes": "false",
    },
    "cutoff": 15,
}

# you can feasibly add as many as you like but the board can only show 3 at a time and the network requests take time

routes = [route_1, route_2, route_3, route_4, route_5]

config = {
    #########################
    # Network Configuration #
    #########################
    # Wifi and aio credentials
    "wifi_ssid": secrets["ssid"],
    "wifi_password": secrets["password"],
    "aio_username": secrets["aio_username"],
    "aio_key": secrets["aio_key"],
    # Time settings
    "timezone": "America/New_York",
    # API and fetch settings
    "api_url": "https://webwatch.gcrta.vontascloud.com/TMWebWatch/Arrivals.aspx/getStopTimes",  # the transit authority API
    "refresh_interval": 30,  # GCRTA feed seems to update every 30 seconds
    "cutoff_min": 4,  # minimum minutes til arrival to remove buses you won't make it to
    # Display Settings
    "matrix_width": 64,
    "num_routes_display": 3,
    "font": bitmap_font.load_font("lib/5x7.bdf"),
    "time_font": bitmap_font.load_font("lib/4x6.bdf"),
    # Core text settings
    "character_width": 5,
    "character_height": 7,
    "text_padding": 3,
    "text_color": 0x552200,
    "dest_color": 0xFF7500,
    "not_live_flag": False,  # adds character after minute if update is scheduled and not live (static)
    "live_char": ".",  # character to use to flag if a static update
    # Loading indicator and text settings
    "loading_route_text": "--",
    "loading_destination_text": "---",
    "loading_min_text": "---",
    "loading_line_color": 0xFF00FF,  # purple
    "loading_time_msg": "ride rta",
    # Heading text
    "heading_text": "ROUTE    MINUTES",
    "heading_color": 0x00008B,  # red
    # Clock text
    "clock_color": 0x00008B,
    # Train color bar settings
    "train_line_height": 6,
    "train_line_width": 2,
    "min_label_characters": 5,
    # Five routes above stored under this key for API use
    "routes": routes
}
