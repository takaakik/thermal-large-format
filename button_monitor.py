#!/usr/bin/env python3
from __future__ import annotations

import sys
import time

import RPi.GPIO as GPIO

from capture_and_print import capture_and_print


BUTTON_PIN = 17
BOUNCE_TIME_MS = 300


def show_ready_message() -> None:
    print()
    print("===========================")
    print(" Thermal Camera Ready")
    print(" Press shutter button...")
    print("===========================")
    print()


def wait_until_released() -> None:
    """Wait until the shutter button is released."""
    while GPIO.input(BUTTON_PIN) == GPIO.LOW:
        time.sleep(0.01)


def main() -> int:
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(
        BUTTON_PIN,
        GPIO.IN,
        pull_up_down=GPIO.PUD_UP,
    )

    show_ready_message()

    try:
        while True:
            GPIO.wait_for_edge(
                BUTTON_PIN,
                GPIO.FALLING,
                bouncetime=BOUNCE_TIME_MS,
            )

            wait_until_released()
            print("Capture!")

            try:
                original_path, print_path = capture_and_print(
                    print_enabled=True,
                    rotate_clockwise=True,
                )

                print(f"Original: {original_path}")
                print(f"Print image: {print_path}")
                print("Completed.")

            except Exception as exc:
                print(
                    f"Capture/print failed: {exc}",
                    file=sys.stderr,
                )

            show_ready_message()

    except KeyboardInterrupt:
        print("\nStopped.")

    finally:
        GPIO.cleanup()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
