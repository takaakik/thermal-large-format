#!/usr/bin/env python3

import cv2
import time
import RPi.GPIO as GPIO
from PIL import Image

from capture_and_print import capture_and_print

BUTTON_PIN = 17      # 使用しているGPIOに合わせてください

WINDOW_NAME = "Thermal Camera"


def main():
    printing = False

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Cannot open camera.")
        return

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(
        WINDOW_NAME,
        cv2.WND_PROP_FULLSCREEN,
        cv2.WINDOW_FULLSCREEN,
    )

    last_press = 0

    try:

        while True:

            ret, frame = cap.read()

            if not ret:
                continue

            cv2.imshow(WINDOW_NAME, frame)

            if cv2.waitKey(1) == 27:
                break

            # ボタン押下（チャタリング防止）
            if GPIO.input(BUTTON_PIN) == GPIO.LOW:

                now = time.time()

                if now - last_press > 0.5:

                    print("Capture!")

                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    image = Image.fromarray(rgb)

                    printing = True
                    try:
                        capture_and_print(image=image)
                    except RuntimeError as e:
                        print(e)
                    finally:
                        printing = False

                    last_press = now

    finally:

        cap.release()

        cv2.destroyAllWindows()

        GPIO.cleanup()


if __name__ == "__main__":
    main()
