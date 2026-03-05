# server1_camera/scripts/button_listener.py
"""
GPIO Button Listener for Raspberry Pi 3.

Monitors GPIO pin 23 for button presses and triggers capture workflows
on Server 1 (camera service). Supports two modes:
  - "label":     capture → upload to Label Studio (default)
  - "inference": capture → run inference → print prediction

The mode is controlled via the BUTTON_MODE environment variable.

Wiring (active-low with internal pull-up):
  - One leg of the button → GPIO 23 (physical pin 16)
  - Other leg           → GND    (physical pin 14)
"""

import os
import sys
import time
import requests

BUTTON_PIN = int(os.getenv("BUTTON_GPIO_PIN", "23"))  # BCM 23 = physischer Pin 16
BUTTON_MODE = os.getenv("BUTTON_MODE", "label")  # "label" or "inference"

SERVER1_URL = os.getenv("SERVER1_URL", "http://pcb-server1-camera:8001")
CAPTURE_ENDPOINT = f"{SERVER1_URL}/api/v1/capture"
INFERENCE_ENDPOINT = f"{SERVER1_URL}/api/v1/button-capture-predict"

# Try to import RPi.GPIO; if unavailable, exit gracefully
try:
    import RPi.GPIO as GPIO
except ImportError:
    print("[Button Listener] RPi.GPIO is not available. "
          "This script is meant to run on a Raspberry Pi. Exiting.")
    sys.exit(1)


def main():
    endpoint = INFERENCE_ENDPOINT if BUTTON_MODE == "inference" else CAPTURE_ENDPOINT
    print(f"[Button Listener] Starte GPIO Listener auf BCM {BUTTON_PIN}")
    print(f"[Button Listener] Modus: {BUTTON_MODE}")
    print(f"[Button Listener] Trigger-URL: {endpoint}")

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    last_state = GPIO.input(BUTTON_PIN)

    try:
        while True:
            state = GPIO.input(BUTTON_PIN)

            # Button hat seinen Zustand geändert:
            if state != last_state:
                if state == GPIO.LOW:
                    print(f"[Button Listener] Button GEDRUECKT – sende POST ({BUTTON_MODE})...")

                    try:
                        timeout = 60 if BUTTON_MODE == "inference" else 30
                        resp = requests.post(endpoint, timeout=timeout)
                        print(f"[Button Listener] Antwort: "
                              f"{resp.status_code} | {resp.text}")
                    except Exception as e:
                        print(f"[Button Listener] Fehler beim Request: {e}")

                else:
                    print("[Button Listener] Button LOSGELASSEN")

                last_state = state
                time.sleep(0.05)  # Entprellen

            time.sleep(0.01)

    except KeyboardInterrupt:
        print("[Button Listener] Stop durch KeyboardInterrupt")

    finally:
        GPIO.cleanup()
        print("[Button Listener] GPIO.cleanup() ausgefuehrt")


if __name__ == "__main__":
    main()
