# gcrta-board 
`A real-time LED transit arrival board for Clevelanders`

This project is a modded Cleveland version of the [dc-metro](https://github.com/metro-sign/dc-metro) transit board.
It uses the same hardware and general display, with capability to poll the [Greater Cleveland Regional Transit Authority](http://www.riderta.com/)
live trip updates and ⌚.

It uses a friendly version of Micropython (which is Python meant for
embedded devices) called CircuitPython. CP is developed by the makers of the hardware, [Adafruit](https://www.adafruit.com/), who makes and sells 
educational and hobby electronics/coding products, provides great resources and is woman-owned in NYC. Check em out.

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
    - ***For now you need to use the custom *.uf2* file in this project root***.  
    It is a version of CircuitPython that
      @dhalbert, one of the CP developers, made as a temporary workaround
    - In version 8 & onwards, the issue should be resolved and you will 
      want to download CircuitPython loader [from Adafruit](https://circuitpython.org/board/matrixportal_m4/).
    - Drag the downloaded _.uf2_ file into the root of the _MATRIXBOOT_ volume.
    - The board will automatically flash the version of CircuitPython and remount as _CIRCUITPY_.
    - If something goes wrong, refer to the [Adafruit Documentation](https://learn.adafruit.com/adafruit-matrixportal-m4/install-circuitpython).
### Adding the project code

4. Drag (copy) the `src/lib` folder from this repository onto *CIRCUITPY* drive.
   - Holds dependencies and libraries from Adafruit. They could require updates eventually.
5. Drag (copy) all the individual Python files in `/src` onto *CIRCUITPY* drive.

At this point your *CIRCUITPY* drive should look like:
```
I:\
│   code.py
│   train_board.py
│   config.py
│   api.py
│   secrets.py
│   time_set.py
│
└───/lib -including all files in it
```

### Internet and Adafruit IO config

7. To connect to  internet, you need to open *secrets.py* and add your wifi ssid and password to respective `secrets` dict keys.
8. **Register for an [adafruitio](https://io.adafruit.com/) account and get a username and API key.**
The board needs to regularly synchronize its onboard clock using a free time service through adafruit io. It's free and there to support hobby projects. 
9. Add your aio username and API key to the `secrets` dict in *secrets.py*.

### Transit board config

The board should reload and start showing you default routes!  

You customize the routes to grab, and other options, in the *config.py*.  

12. Each route/stop/direction combination requires a dict with these 3 key:values. 
    The 3rd key is a nested dictionary object with 6 key-values.
    - route_name: *str*, used as a label, like "26" or "HL"
    - route_color: *int*, provide as hex color code in format like *0xff0000* which is red.This deterimnes the route color bar
    - params: *dict*, the GCRTA Next Connect API request, info below:  
      - 'routeID': ⚠ *Get from NextConnect*  
      - 'directionID': ⚠ _Get from NextConnect_  
      - 'stopID': ⚠ _Get from NextConnect_  
      - 'cutoff': *int* Trips arriving sooner than this time will be tossed out because they are impossible to reach the stop in time
      - 'tpID': 0,
      - 'useArrivalTimes': 'false'


Each route dict like above represents a single route at a single stop going one direction.

**The board can only fit 3 rows on it.** If you are fetching more than 3 routes, it will display the 3
soonest arrivals in order of their arrival

### Gettings `params` from GCRTA NextConnect

13. Go to [GCRTA NextConnect Live Departure Times](http://nextconnect.riderta.com/LiveDepartureTimes). This is an endpoint that delivers
live departure updates from RTA's TransitMaster system, which is the brains of RTA's operations, including scheduling, and 
serving the RTA real time feed that is used by Google Maps and Transit App, etc.  The board essentially simulates using this website.
14. For each route/direction/stop combo, you need to:
    1. Enter the desired route, direction, and stop.
    2. Open devtools for your browser (Ctrl + Shift + I) --*Chrome is recommended if you aren't familiar with this*
    3. Go to "Network" tab
    4. Wait up to 15 seconds for the browser to fetch the update again (it automatically does this)
    5. You should see a network action appear called *getStopTimes*. Click on it
    6. Click on *Payload*
    7. Use the parameters from that payload to fill out the `params` dict in the desired route dict.

### Watch the board update

15. Upon saving, the board will reboot and start to populate with your configured route/direction/stops. 🎉🎉🎉

🚌🚌🚌
