from adafruit_bitmap_font import bitmap_font
from secrets import secrets


##### ROUTE CONFIG #####
"""
Every arrival estimate requires a specific route config for each route-stop-direction combo.
The board is designed to use two lists of route configs (dictionaries): one in each direction of the route.
I choose to use A to denote inbound and B to denote outbound for the same route.

Each route config entry has the following dictionary format:

route_LETTERNUMBER = {
    "route_name": "22-E", --- How the board labels this arrival time on left-hand of  board
    "route_color": 0x######, --- The color of the line next to the name, as hexadecimal number
    "params": {
        "routeID": {int}, 
        "directionID": {int},
        "stopID": {int},
        "tpID": 0,
        "useArrivalTimes": "false",
    },
    "cutoff": 5,
}

The (slightly) tedious part is gathering the routeID, directionID and stopID for each entry.
To do this:
    1) go to the riderta.com homep
    2) click Real-Time Departures
    3) press F12 to open dev tools in your browser
    4) Click "Network" tab of the dev tool panel
    5) Choose your route, direction, and stop on the website
    6) Find the getStopTimes entry in the Network activity under "Name".
    7) Go to "Payload" for that entry and observe

"""
# INBOUND ROUTES
route_1A = {
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
route_2A = {
    "route_name": "45-N",
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
route_3A = {
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
route_4A = {
    "route_name": "71-N",
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
route_5A = {
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

routes_in = [route_1A, route_2A, route_3A, route_4A, route_5A]

# OUTBOUND ROUTES
route_1B = {
    "route_name": "22-W",
    "route_color": 0x0011AA,
    "params": {
        "routeID": 139,
        "directionID": 14,
        "stopID": 13364,
        "tpID": 0,
        "useArrivalTimes": "false",
    },
    "cutoff": 5,
}

route_2B = {
    "route_name": "45-S",
    "route_color": 0xA81995,
    "params": {
        "routeID": 60,
        "directionID": 7,
        "stopID": 831,
        "tpID": 0,
        "useArrivalTimes": "false",
    },
    "cutoff": 5,
}

route_3B = {
    "route_name": "26-W",
    "route_color": 0x22CF19,
    "params": {
        "routeID": 165,
        "directionID": 14,
        "stopID": 9185,
        "tpID": 0,
        "useArrivalTimes": "false",
    },
    "cutoff": 5,
}
route_4B = {
    "route_name": "71-S",
    "route_color": 0xDE4E00,
    "params": {
        "routeID": 193,
        "directionID": 7,
        "stopID": 9185,
        "tpID": 0,
        "useArrivalTimes": "false",
    },
    "cutoff": 5,
}
route_5B = {
    "route_name": "RL-W",
    "route_color": 0xDD0000,
    "params": {
        "routeID": 147,
        "directionID": 14,
        "stopID": 17564,
        "tpID": 0,
        "useArrivalTimes": "false",
    },
    "cutoff": 15,
}
routes_out = [route_1B, route_2B, route_3B, route_4B, route_5B]

##### MAIN CONFIG #####
config = {
    # Route lists, passed from above
    "routes_in": routes_in,
    "routes_out": routes_out,
    # Wifi and aio credentials
    "wifi_ssid": secrets["ssid"],
    "wifi_password": secrets["password"],
    "aio_username": secrets["aio_username"],
    "aio_key": secrets["aio_key"],
    # Time Zone
    "timezone": "America/New_York",
    # API and fetch settings
    "api_url": "https://webwatch.gcrta.vontascloud.com/TMWebWatch/Arrivals.aspx/getStopTimes",  # the transit authority API
    "refresh_interval": 15, # Seconds
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
    "loading_time_msg": "RIDE LE BUS",
    # Heading text
    "heading_text": "ROUTE    MINUTES",
    "heading_color": 0xFFFFFF,  # red
    # Clock text
    "clock_color": 0x00008B,
    # Train color bar settings
    "train_line_height": 6,
    "train_line_width": 2,
    "min_label_characters": 5,
}
