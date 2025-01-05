# type: ignore

import time
import supervisor

# internet setup modules
import board
import busio
from digitalio import DigitalInOut
import adafruit_requests as requests
import adafruit_esp32spi.adafruit_esp32spi_socket as socket
from adafruit_esp32spi import adafruit_esp32spi

# config is one dict container. it sets certain parameters for the API.
# most of it is truly not customizable and will break the whole library if changed

from config import config

# other pieces of my code in root
import api  # module sets up my internet
import time_set
import train_board

# Connecting to internet, grabbed straight from Internet Connect!

esp32_cs = DigitalInOut(board.ESP_CS)
esp32_ready = DigitalInOut(board.ESP_BUSY)
esp32_reset = DigitalInOut(board.ESP_RESET)

spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)
requests.set_socket(socket, esp)

print("Connecting to AP...")
while not esp.is_connected:
    try:
        esp.connect_AP(config["wifi_ssid"], config["wifi_password"])
    except (RuntimeError, ConnectionError) as e:
        print("could not connect to AP, retrying: ", e)
        continue
print("Connected to", str(esp.ssid, "utf-8"), "\tRSSI:", esp.rssi)

# after internet connects, I set the local time with aio
time_set.get_local_time()
print("Set to local time.")

# Create API object which has method to fetch all predictions in a list
# The API object requires the wifi device (esp) object to control requests
transit_api = api.RealTimeAPI(esp)

# Create the TrainBoard object which orchestrates the display,
t = train_board.TrainBoard(transit_api.fetch_predictions)

# Set up key timings
sleep_seconds = config["refresh_interval"]  # number of seconds to wait between cycles
clock_reset_minutes = 180 # How often to reset the board's clock, in minutes
cycles_until_clock_reset = (clock_reset_minutes * 60)/ sleep_seconds  # number of cycles until clock is synchronized again

# Set loop parameters to starting state
inbound = False
counter = 0

while True:
    counter += 1
    inbound = not inbound
    print(
        f"Beginning cycle {counter} of {cycles_until_clock_reset}, Direction: {"Inbound" if inbound else "Outbound"}"
    )
    if (
        counter > cycles_until_clock_reset
    ):  # this block tells it to resync the clock from Adafruit clock service, by default 6 hours if cycle = 30 seconds
        try:
            time_set.get_local_time()  # this is done because the onboard clock starts lagging
            counter = 0
            print("Reset cycle counter to 0. Updated time")
        except Exception as e:
            print("Time sync error.")
    t.loading_dot_grp.hidden = (
        False  # Corner blue dot on LED panel to indicate it's running its cycle
    )
    try:
        if inbound:
            t.refresh(
                config["routes_in"], direction="in"
            )  # Main update function, grabs all routes info via API object and updates text and graphic objects
        else:
            t.refresh(config["routes_out"], direction="out")
    except (
        ConnectionError
    ):  # If the error catching and resetting in the above code fails, it's code red, time to soft reset
        supervisor.reload()
    t.loading_dot_grp.hidden = True  # Dot off while not actively fetching new data

    # Sleep between fetching more updates
    # This loop will flip between directions twice during sleep
    begin = time.monotonic()
    direction_flip_times = 2
    direction_flips = 0
    flip_duration = sleep_seconds / direction_flip_times
    print(
        f"Sleeping {sleep_seconds} seconds with direction flip every {flip_duration} seconds"
    )
    while direction_flips < direction_flip_times:
        time.sleep(flip_duration)
        t.flip_direction()
        direction_flips += 1
