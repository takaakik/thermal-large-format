#!/usr/bin/env python3

import cv2
import time
import shutil
import socket
import subprocess
import RPi.GPIO as GPIO

from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from capture_and_print import (
    capture_and_print,
    send_to_printer,
)


BUTTON_PIN = 17
LONG_PRESS_SECONDS = 3.0

WINDOW_NAME = "Thermal Camera"

PRINT_WIDTH = 2400
PRINT_HEIGHT = 3300

FONT_PATH = Path(
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
)


def get_wifi_ssid():
    try:
        result = subprocess.run(
            [
                "nmcli",
                "-t",
                "-f",
                "ACTIVE,SSID",
                "device",
                "wifi",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )

        for line in result.stdout.splitlines():
            if line.startswith("yes:"):
                return line.split(":", 1)[1]

    except Exception:
        pass

    return "Not connected"


def get_ipv4():
    try:
        result = subprocess.run(
            ["hostname", "-I"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        for address in result.stdout.split():
            if ":" not in address:
                return address

    except Exception:
        pass

    return "Unavailable"


def get_cpu_temperature():
    try:
        value = Path(
            "/sys/class/thermal/thermal_zone0/temp"
        ).read_text().strip()

        return f"{int(value) / 1000:.1f} C"

    except Exception:
        return "Unavailable"


def get_disk_free():
    try:
        usage = shutil.disk_usage("/")
        free_gb = usage.free / (1024 ** 3)

        return f"{free_gb:.1f} GB"

    except Exception:
        return "Unavailable"


def get_uptime():
    try:
        seconds = float(
            Path("/proc/uptime")
            .read_text()
            .split()[0]
        )

        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)

        if hours >= 24:
            days = hours // 24
            hours %= 24
            return f"{days}d {hours}h {minutes}m"

        return f"{hours}h {minutes}m"

    except Exception:
        return "Unavailable"


def get_printer_status():
    try:
        result = subprocess.run(
            [
                "lpstat",
                "-p",
                "PJ-763",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )

        text = (
            result.stdout
            + result.stderr
        ).lower()

        if (
            result.returncode == 0
            and "disabled" not in text
        ):
            return "OK"

    except Exception:
        pass

    return "NOT READY"


def create_self_test_image(
    camera_ok=True,
):
    image = Image.new(
        "1",
        (PRINT_WIDTH, PRINT_HEIGHT),
        1,
    )

    draw = ImageDraw.Draw(image)

    try:
        title_font = ImageFont.truetype(
            str(FONT_PATH),
            110,
        )

        body_font = ImageFont.truetype(
            str(FONT_PATH),
            68,
        )

        small_font = ImageFont.truetype(
            str(FONT_PATH),
            50,
        )

    except Exception:
        title_font = ImageFont.load_default()
        body_font = title_font
        small_font = title_font

    hostname = socket.gethostname() + ".local"

    values = [
        (
            "Camera",
            "OK" if camera_ok else "NOT READY",
        ),
        (
            "Printer",
            get_printer_status(),
        ),
        (
            "Wi-Fi",
            get_wifi_ssid(),
        ),
        (
            "IPv4",
            get_ipv4(),
        ),
        (
            "Hostname",
            hostname,
        ),
        (
            "CPU Temp",
            get_cpu_temperature(),
        ),
        (
            "Disk Free",
            get_disk_free(),
        ),
        (
            "Uptime",
            get_uptime(),
        ),
    ]

    x = 180
    y = 220

    draw.text(
        (x, y),
        "ONE SHOT",
        font=title_font,
        fill=0,
    )

    y += 150

    draw.text(
        (x, y),
        "SELF TEST",
        font=title_font,
        fill=0,
    )

    y += 210

    draw.line(
        (
            x,
            y,
            PRINT_WIDTH - x,
            y,
        ),
        fill=0,
        width=8,
    )

    y += 130

    for label, value in values:
        draw.text(
            (x, y),
            f"{label:<12} {value}",
            font=body_font,
            fill=0,
        )

        y += 125

    y += 50

    draw.line(
        (
            x,
            y,
            PRINT_WIDTH - x,
            y,
        ),
        fill=0,
        width=4,
    )

    y += 100

    draw.text(
        (x, y),
        "SSH:",
        font=body_font,
        fill=0,
    )

    y += 110

    draw.text(
        (x, y),
        f"tak@{hostname}",
        font=body_font,
        fill=0,
    )

    y += 110

    ipv4 = get_ipv4()

    if ipv4 != "Unavailable":
        draw.text(
            (x, y),
            f"tak@{ipv4}",
            font=body_font,
            fill=0,
        )

    y = PRINT_HEIGHT - 260

    timestamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    draw.text(
        (x, y),
        timestamp,
        font=small_font,
        fill=0,
    )

    return image


def print_self_test(
    camera_ok=True,
):
    print("SELF TEST", flush=True)

    image = create_self_test_image(
        camera_ok=camera_ok,
    )

    try:
        response = send_to_printer(image)
        print(
            f"Self test submitted: {response}",
            flush=True,
        )

    except Exception as e:
        print(
            f"Self test print failed: {e}",
            flush=True,
        )


def capture_frame_and_print(frame):
    print("Capture!", flush=True)

    rgb = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2RGB,
    )

    image = Image.fromarray(rgb)

    try:
        capture_and_print(
            image=image,
        )

    except RuntimeError as e:
        print(e, flush=True)


def main():
    GPIO.setmode(GPIO.BCM)

    GPIO.setup(
        BUTTON_PIN,
        GPIO.IN,
        pull_up_down=GPIO.PUD_UP,
    )

    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print(
            "Cannot open camera.",
            flush=True,
        )
        return

    cv2.namedWindow(
        WINDOW_NAME,
        cv2.WINDOW_NORMAL,
    )

    cv2.setWindowProperty(
        WINDOW_NAME,
        cv2.WND_PROP_FULLSCREEN,
        cv2.WINDOW_FULLSCREEN,
    )

    button_down = False
    press_started = None
    long_press_done = False

    try:
        while True:
            ret, frame = cap.read()

            if not ret:
                continue

            cv2.imshow(
                WINDOW_NAME,
                frame,
            )

            if cv2.waitKey(1) == 27:
                break

            pressed = (
                GPIO.input(BUTTON_PIN)
                == GPIO.LOW
            )

            # Button just pressed.
            if pressed and not button_down:
                button_down = True
                press_started = time.monotonic()
                long_press_done = False

            # Button still held.
            elif (
                pressed
                and button_down
                and not long_press_done
            ):
                held = (
                    time.monotonic()
                    - press_started
                )

                if held >= LONG_PRESS_SECONDS:
                    long_press_done = True

                    print_self_test(
                        camera_ok=cap.isOpened(),
                    )

            # Button released.
            elif (
                not pressed
                and button_down
            ):
                held = (
                    time.monotonic()
                    - press_started
                )

                button_down = False
                press_started = None

                # Long press already performed.
                if long_press_done:
                    continue

                # Short press.
                if held < LONG_PRESS_SECONDS:
                    capture_frame_and_print(
                        frame,
                    )

    finally:
        cap.release()

        cv2.destroyAllWindows()

        GPIO.cleanup()


if __name__ == "__main__":
    main()