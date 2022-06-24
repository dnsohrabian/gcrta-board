import time
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
import api # module sets up my internet
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
    except RuntimeError as e:
        print("could not connect to AP, retrying: ", e)
        continue
print("Connected to", str(esp.ssid, "utf-8"), "\tRSSI:", esp.rssi)

# after internet connects, I set the local time with aio
time_set.get_local_time()
print("Set to local time.")

# create API object which has method to fetch all predictions in a list
transit_api = api.RealTimeAPI(esp)

# create TrainBoard object which manages the Matrix object, and displayio groups
# the TrainBoard manages Train objects that can update, hide, or show themselves
# using displayio methods. It also updates a small time stamp to latest update

t = train_board.TrainBoard(transit_api.fetch_predictions)

counter = 0
while True:
    counter += 1
    if counter > 120: # six hours or so between time resync
        try:
            time_set.get_local_time()
            counter = 0
        except Exception as e:
            print("Time sync error.")
    t.refresh() # main train board refresh
    begin =time.monotonic()
    while time.monotonic()-begin <30:
        # for row in t.trains[:3]:
        #     row.destination_label.update()
        #     t.display.refresh(minimum_frames_per_second=0)
        pass
