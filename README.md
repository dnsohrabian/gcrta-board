# gcrta-board
Your very own live-update LED transit departure board in Cleveland

### This project is an adaptation of the [dc-metro](https://github.com/metro-sign/dc-metro) transit arrival board for Greater Cleveland Regional Transit Authority.

A guide on how to set up your own board will be developed going forward.

Steps are:
1. Get MatrixPortal M4 and LED matrix from Adafruit
2. Bootload CircuitPython with the .uf2 in this repository
3. Copy all /src content to the flash memory of the MP
4. Customize routes to fetch (directions and background info on how to coming soon)
4. Customize route colors (need to make this all in the configuration file to be easier)
