# gcrta-board
`A real-time LED transit departure board for Clevelanders`

This project is a modded Cleveland version of the [dc-metro](https://github.com/metro-sign/dc-metro) transit board.
It uses the same hardware and general display, with capability to poll the [Greater Cleveland Regional Transit Authority](http://www.riderta.com/)
live trip updates by itself and a clock ⌚.

It uses a friendly version of Micropython (which is Python meant for
embedded devices) called CircuitPython. CP is developed by the makers of the board, [Adafruit](https://www.adafruit.com/). They make 
all kinds of educational and hobby electronics/coding products, provide great resources and community spaces. Check em out.

![Example photo](/img/Example1.jpg)

# How To
## Hardware Needed
- An [Adafruit Matrix Portal](https://www.adafruit.com/product/4745) - $24.99
  - This is a single board microcontroller, a.k.a. *a small computer*
- A **64x32 RGB LED matrix** compatible with the _Matrix Portal_ - $39.99 _to_ $84.99
    - [64x32 RGB LED Matrix - 3mm pitch](https://www.adafruit.com/product/2279) Smallest, finer grid
    - [64x32 RGB LED Matrix - 4mm pitch](https://www.adafruit.com/product/2278)
    - [64x32 RGB LED Matrix - 5mm pitch](https://www.adafruit.com/product/2277)
    - [64x32 RGB LED Matrix - 6mm pitch](https://www.adafruit.com/product/2276) Less dense pixels, but bigger (15" x 7.5")
- A **USB-C power supply** (15w phone adapters should work fine for this code, but the panels can theoretically pull 20w if every pixel is on white)
- A **USB-C cable** that can connect your computer/power supply to the board

## Setup Overview
### Hardware and CircuitPython setup

1. [Prep the *MatrixPortal* and LED board](https://learn.adafruit.com/adafruit-matrixportal-m4/prep-the-matrixportal) using Adafruit's guide
2. Connect the board to your computer using a USB C cable. Double click the button on the board labeled _RESET_.
The board should mount onto your computer as a storage volume, most likely named _MATRIXBOOT_.
3. Flash your _Matrix Portal_ with the provided version of CircuitPython
    - In CircuitPython 7.3, there is a flaw that freezes when getting data from the internet.
    - ***For now you need to use the custom *.uf2* file from this project root***.  
    It is a version of CircuitPython that
      @dhalbert, one of the CP developers, made as a temporary workaround
    - In version 8 & onwards, the issue should be resolved and you will 
      want to download CircuitPython loader [from Adafruit](https://circuitpython.org/board/matrixportal_m4/).
    - Drag the downloaded _.uf2_ file into the root of the _MATRIXBOOT_ volume.
    - The board will automatically flash the version of CircuitPython and remount as _CIRCUITPY_.
    - If something goes wrong, refer to the [Adafruit Documentation](https://learn.adafruit.com/adafruit-matrixportal-m4/install-circuitpython).
### Adding the project code

4. Drag (copy) the `lib/` folder from this repository onto *CIRCUITPY* drive.
   - Holds dependencies and libraries from Adafruit. They could require updates eventually.
5. Drag (copy) all the individual Python files in `src/` onto *CIRCUITPY* drive.
   - These are the main project source code
     - code.py
     - api.py
     - train_board.py
     - time_set.py
     - config.py
     - secrets.py
6. The moment you drag these the board will attempt (and fail) to connect to internet.

### Internet and Adafruit IO config

7. To connect to the internet, you need to open *secrets.py* and add your wifi ssid and password to respective `secrets` dict keys.
8. The project needs accurate time to both 1) calculate the arrival minutes and 2) display a clock that verifies
the board is current.<br>
The board has a clock chip that can track time fairly well once it's set. But it needs to connect to a service
to fetch the time, and periodically sync the time to keep updates accurate. It is a transit board after all...
9. The *time_set.py* module has a function `get_local_time` that automatically syncs the on-board clock using an online feed provided by
Adafruit through [adafruitio](https://io.adafruit.com/). It's free and there to support hobby projects. Register for an
account and get a username and API key.
10. Add your aio username and API key to the `secrets` dict in *secrets.py*.

### Transit board config

11. At this point, the board should reload and start showing you routes!  
But you want it to show the stops/routes/direction that you choose. You manage this along with colors & other options
in the *config.py* file using the `config` dict object and `routes` objects.
12. Each route requires a dict object to be added. There are 3 keys per route
    - route_name: *str*, used as a label, like "26" or "HL"
    - route_color: *int*, provide as hex color code in format like *0xff0000* which is red.This deterimnes the route color bar
    - params: *dict* 