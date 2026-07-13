import time
import RPi.GPIO as GPIO

BUTTON_PIN = 17

GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

print("Ready")

try:
    while True:
        GPIO.wait_for_edge(
            BUTTON_PIN,
            GPIO.FALLING,
            bouncetime=300,
        )

        print("Capture!")

        # ボタンを離すまで待つ
        while GPIO.input(BUTTON_PIN) == GPIO.LOW:
            time.sleep(0.01)

finally:
    GPIO.cleanup()
