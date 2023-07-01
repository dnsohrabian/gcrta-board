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

1. [Prep the MatrixPortal and LED board](https://learn.adafruit.com/adafruit-matrixportal-m4/prep-the-matrixportal) using Adafruit's guide.
2. [Install CircuitPython.](https://learn.adafruit.com/adafruit-matrixportal-m4/install-circuitpython) Click "Download .UF2 Now" and follow steps.
### Adding the gcrta-board  code

3. Drag (copy) the `src/lib` folder from this repository onto *CIRCUITPY* drive.
5. Drag (copy) all the individual Python files inside `/src` onto *CIRCUITPY* drive. Do not copy the folder itself.

At this point your *CIRCUITPY* drive should look like:
```
I:\
│   api.py
|   code.py
│   config.py
│   secrets.py
│   time_set.py
│   train_board.py
│
└───\lib folder, including all files in it
```
### Internet and Adafruit IO config

6. To connect to  internet, you need to open *secrets.py* and add your wifi ssid and password to respective `secrets` dict keys that say `"enter_your_info"`.
7. Register for an [adafruitio](https://io.adafruit.com/) account and get a username and API key.
The board needs to regularly synchronize its onboard clock using a free time service through adafruit io. It's free and intended to support hobby projects.
8. Add your aio username and API key to the `secrets` dict in *secrets.py*.

## Transit board config

The board should reload and start showing you default routes! You now need to configure it to your liking. 

### Customize your stops in the *config.py*.  

9. Each route/stop/direction combination requires a Python dict with these 3 key:values. The 3rd key, *params*, is a nested dictionary object with 6 key-values.
    - route_name: *str*, what will display, like "26" or "HL"
    - route_color: *int*, hex color for bar (e.g. 0xff0000 for red)
    - params: *dict*, the GCRTA Next Connect API request parameters, explained below
      - 'routeID': ⚠ *Get from NextConnect*  
      - 'directionID': ⚠ _Get from NextConnect_  
      - 'stopID': ⚠ _Get from NextConnect_  
      - 'cutoff': *int* Trips arriving sooner than this time will be tossed out because they are impossible to reach the stop in time
      - 'tpID': 0,
      - 'useArrivalTimes': 'false'

**The board can only fit 3 rows on it.** If you are fetching more than 3 routes, it will display the 3
soonest arrivals in order of their arrival

### Gettings `params` from GCRTA NextConnect

10. Go to [GCRTA NextConnect Live Departure Times](http://nextconnect.riderta.com/LiveDepartureTimes). This is an endpoint that delivers
live departure updates from RTA's TransitMaster system, which is the central brain of RTA's operations, scheduling, and 
serving the RTA real time feed. This board essentially simulates using this website.
11. For each route/direction/stop combo, you need to:
    1. Enter the desired route, direction, and stop on NextConnect.
    2. Open devtools for your browser (Ctrl + Shift + I) --*Chrome is recommended if you aren't familiar with this*
    3. Go to "Network" tab
    4. Wait up to 15 seconds for the browser to fetch the update again (it automatically does this)
    5. You should see a network action appear called *getStopTimes*. Click on it
    6. Click on *Payload*
    7. Use the parameters from that payload to fill out the `params` dict in the desired route dict.

## Finish line
12. Upon saving your `config.py` with your desired routes, the board will reboot and populate with your configured route/direction/stops. 🎉🎉🎉