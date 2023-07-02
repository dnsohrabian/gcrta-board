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
    except (RuntimeError, ConnectionError) as e:
        print("could not connect to AP, retrying: ", e)
        continue
print("Connected to", str(esp.ssid, "utf-8"), "\tRSSI:", esp.rssi)

# after internet connects, I set the local time with aio
time_set.get_local_time()
print("Set to local time.")

# create API object which has method to fetch all predictions in a list
# The API object requires the wifi device (esp) object to drive the 
# all the internet requests that go into the grabbing the transit data
# from the NextConnect platform

transit_api = api.RealTimeAPI(esp)

# create TrainBoard object which manages the Matrix object,

t = train_board.TrainBoard(transit_api.fetch_predictions)
# Finally, the API's main function is

counter = 0
while True:
    counter += 1
    if counter > 120: # this block tells it to resync the clock every 120 cycle, by default 6 hours if cycle = 30 seconds
        try:
            time_set.get_local_time() # this is done because the onboard clock starts getting inaccurate
            counter = 0
        except Exception as e:
            print("Time sync error.")
    t.loading_dot_grp.hidden = False # Corner blue dot on LED panel to indicate it's running its cycle
    t.refresh()  # Main update function, grabs all routes info via API object and updates text and graphic objects
    t.loading_dot_grp.hidden = True # Dot off while sleeping
    begin =time.monotonic()
    while time.monotonic()-begin <30:
        # for row in t.trains[:3]:
        #     row.destination_label.update()
        #     t.display.refresh(minimum_frames_per_second=0)
        pass
