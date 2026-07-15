# thermal-large-format v1.0

Raspberry Pi 4 + USB camera + Phomemo M08F A4 thermal printer.

## Hardware

- Raspberry Pi 4 Model B, 4 GB
- Raspberry Pi OS 64-bit
- UVC USB camera (`/dev/video0`)
- Phomemo M08F
- Momentary shutter button
  - GPIO 17 / physical pin 11
  - GND / physical pin 9
- Suitable Raspberry Pi power supply or battery

## System packages

```bash
sudo apt update
sudo apt install \
  cups \
  v4l-utils \
  python3-opencv \
  python3-rpi.gpio \
  python3-venv
```

Install the official M08F Linux driver and confirm:

```bash
lpinfo -m | grep M08F
lpstat -p M08F
```

The queue should use `/etc/cups/ppd/M08F.ppd`.

## Python environment

This project expects the virtual environment to see the system OpenCV and
RPi.GPIO packages:

```bash
cd ~/thermal-large-format
python3 -m venv --system-site-packages venv
source venv/bin/activate
pip install -r requirements.txt
```

## Before first test

Clear old jobs and enable the printer:

```bash
cancel -a M08F
sudo cupsenable M08F
sudo cupsaccept M08F
```

Confirm that the M08F is visible:

```bash
/usr/sbin/lpinfo -v | grep M08F
lpstat -t
```

## Manual tests

Capture without printing:

```bash
source venv/bin/activate
python capture_and_print.py --no-print
```

Capture and print:

```bash
python capture_and_print.py
```

Run the shutter-button monitor manually:

```bash
python button_monitor.py
```

Do not run the manual monitor while the systemd service is active, because
both processes cannot claim GPIO 17 at the same time.

## Install the systemd service

```bash
sudo cp thermal-camera.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now thermal-camera
```

Check status and logs:

```bash
systemctl status thermal-camera
journalctl -u thermal-camera -f
```

After editing Python code:

```bash
python -m py_compile capture_and_print.py button_monitor.py
sudo systemctl restart thermal-camera
```

## Recovery

If CUPS disables the printer after a USB or paper error:

```bash
sudo systemctl stop thermal-camera
cancel -a M08F
sudo cupsenable M08F
sudo cupsaccept M08F
sudo systemctl start thermal-camera
```

The v1.0 program refuses to capture a new image when unfinished jobs already
exist. It also waits for the current job to complete before returning to the
ready state.

## Output

Images are stored in `output/`:

- `*-original.jpg`: full-resolution camera image
- `*-print.png`: A4, 1678 x 2373 px, grayscale, 203 dpi
