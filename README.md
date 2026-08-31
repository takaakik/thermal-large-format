# thermal-large-format

A Raspberry Pi based A4 thermal paper camera.

`thermal-large-format` is a standalone digital camera that captures a live
USB camera image and immediately prints it as a monochrome A4 thermal
photograph.

The current version uses a Raspberry Pi 4 and a Brother PocketJet PJ-763.
Images are converted to 1-bit using Atkinson dithering and sent directly
through Brother's raster converter, avoiding the slower conventional
PostScript/Ghostscript print path.

## Features

- Fullscreen live view
- Physical shutter button
- A4 direct thermal printing
- 300 dpi, 2400 x 3300 pixel print pipeline
- Atkinson dithering implemented in C
- Direct Brother raster output for faster printing
- Approximately 5 seconds from shutter press to print start
- Original and processed images saved locally
- Long-press self-test print
- Designed for standalone battery-powered use

## Hardware

Current hardware:

- Raspberry Pi 4 Model B, 4 GB
- Raspberry Pi OS 64-bit
- UVC USB camera (`/dev/video0`)
- Brother PocketJet PJ-763
- 7-inch 1024 x 600 HDMI display
- Momentary shutter button
  - GPIO 17 / physical pin 11
  - GND / physical pin 9
- USB power bank for Raspberry Pi / display / camera
- Brother battery for the PJ-763

## Controls

The physical shutter button has two functions:

- **Short press:** capture the current live-view frame and print it
- **Long press (3 seconds):** print a self-test sheet

The self-test reports:

- Camera status
- Printer status
- Wi-Fi SSID
- IPv4 address
- mDNS hostname
- CPU temperature
- Free disk space
- System uptime
- SSH connection addresses
- Date and time

This is useful when operating the camera without a keyboard or when the
Raspberry Pi's current network address is unknown.

## Image pipeline

The photographic print pipeline is:

    USB camera
        |
        v
    live OpenCV frame
        |
        v
    PIL image
        |
        v
    EXIF transpose / rotation
        |
        v
    ImageOps.fit(2400 x 3300, LANCZOS)
        |
        v
    grayscale
        |
        v
    gamma correction
        |
        v
    Atkinson dithering (C)
        |
        v
    1-bit image
        |
        v
    PPM
        |
        v
    Brother rastertobrpt1
        |
        v
    CUPS raw queue
        |
        v
    PJ-763

Resizing is performed **before** dithering. Resampling an already dithered
1-bit image can create moire and other unwanted patterns.

## System packages

    sudo apt update
    sudo apt install \
      cups \
      v4l-utils \
      python3-opencv \
      python3-rpi.gpio \
      python3-venv \
      gcc

## Python environment

The virtual environment uses the system OpenCV and RPi.GPIO packages:

    cd ~/thermal-large-format
    python3 -m venv --system-site-packages venv
    source venv/bin/activate
    pip install -r requirements.txt

## Brother PJ-763 driver

This project requires Brother's Linux/Raspbian driver for the PJ-763.

The Brother driver is proprietary software and is **not included in this
repository**. Download and install the appropriate driver separately from
Brother.

The current system uses Brother PJ-763 printer driver version 2.0.4.

The driver provides:

    /opt/brother/PTouch/pj763/lpd/rastertobrpt1
    /opt/brother/PTouch/pj763/inf/brmediatype
    /opt/brother/PTouch/pj763/inf/paperinfpj1

`thermal-large-format` calls `rastertobrpt1` directly and submits the
resulting Brother raster data to CUPS using a raw queue.

Confirm that the printer is visible:

    lsusb | grep Brother
    /usr/sbin/lpinfo -v | grep Brother
    lpstat -p PJ-763

Expected USB device:

    04f9:2078 Brother Industries, Ltd PJ-763

## Build the Atkinson dithering library

The Atkinson algorithm is implemented in `atkinson.c`.

Build it on the Raspberry Pi:

    gcc -O3 -shared -fPIC atkinson.c -o libatkinson.so

`libatkinson.so` is a generated binary and should not be committed to the
repository.

## Printer configuration

The direct raster pipeline uses the PJ-763 configuration file included with
this project.

Important settings include:

    Halftone=BINARY
    Density=3
    Resolution=300
    MediaSize=A4

Halftoning is performed by the project itself, so the Brother raster stage
receives an already prepared 1-bit image.

## Run manually

Activate the virtual environment:

    cd ~/thermal-large-format
    source venv/bin/activate

Run the camera:

    python thermal_camera.py

Do not run a second copy while the systemd service is active, because both
processes would attempt to use the same camera and GPIO shutter button.

## systemd service

Install the service:

    sudo cp thermal-camera.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable --now thermal-camera.service

Check status:

    systemctl status thermal-camera.service

Follow logs:

    journalctl -u thermal-camera.service -f

After editing the Python code:

    python3 -m py_compile thermal_camera.py capture_and_print.py
    sudo systemctl restart thermal-camera.service

## Output files

Captured images are stored in `output/`.

Typical files:

    YYYYMMDD-HHMMSS-original.jpg
    YYYYMMDD-HHMMSS-print.png

`original.jpg` contains the captured camera image.

`print.png` contains the final 2400 x 3300 pixel monochrome image prepared
for the PJ-763.

## Project structure

    thermal_camera.py
        Live view, GPIO shutter handling, and self-test

    capture_and_print.py
        Image processing and PJ-763 print pipeline

    atkinson.c
        Atkinson dithering implementation

    brpj763rc-test
        PJ-763 raster configuration

    thermal-camera.service
        systemd service definition

    requirements.txt
        Python dependencies

    output/
        Captured and processed images

## Notes

The project originally used a Phomemo M08F A4 thermal printer. The current
PJ-763 version uses a different print architecture and the old M08F setup is
no longer required.

The Brother CUPS wrapper includes components that are not native ARM64
executables. This project therefore uses the ARM-compatible
`rastertobrpt1` component directly rather than relying on the complete
Brother CUPS conversion chain.

The PJ-763 itself remains controlled through CUPS as a raw printer queue.

## License

The original source code in this repository is released under the MIT
License. See `LICENSE`.

Brother printer drivers, utilities, and other Brother software are not part
of this project and remain subject to Brother's own licensing terms.
