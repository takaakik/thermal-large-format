#!/usr/bin/env python3

from __future__ import annotations

import sys
import time

import RPi.GPIO as GPIO

from capture_and_print import capture_and_print


BUTTON_PIN = 17
BOUNCE_TIME_MS = 300


def wait_until_released() -> None:
    """ボタンが離されるまで待つ。"""
    while GPIO.input(BUTTON_PIN) == GPIO.LOW:
        time.sleep(0.01)


def main() -> int:
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(
        BUTTON_PIN,
        GPIO.IN,
        pull_up_down=GPIO.PUD_UP,
    )

    print("Ready. Press the shutter button.")

    try:
        while True:
            GPIO.wait_for_edge(
                BUTTON_PIN,
                GPIO.FALLING,
                bouncetime=BOUNCE_TIME_MS,
            )

            print("Capture!")

            # 押しっぱなしによる再検出を防ぐ
            wait_until_released()

            try:
                # この処理が終わるまで次の撮影は受け付けない
                original_path, print_path = capture_and_print(
                    print_enabled=True,
                    rotate_clockwise=True,
                )

                print(f"Completed: {original_path}")
                print(f"Completed: {print_path}")
                print("Ready.")

            except Exception as exc:
                print(f"Capture/print failed: {exc}", file=sys.stderr)
                print("Ready.")

    except KeyboardInterrupt:
        print("\nStopped.")

    finally:
        GPIO.cleanup()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
