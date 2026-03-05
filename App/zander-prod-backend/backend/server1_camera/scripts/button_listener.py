"""
GPIO Button Listener for Raspberry Pi 3.

Monitors GPIO pin 23 for button presses and triggers capture workflows
on Server 1 (camera service). Supports two modes:
  - "label":     capture → upload to Label Studio (default)
  - "inference":  capture → run inference → print prediction

The mode is controlled via the BUTTON_MODE environment variable.

Wiring (active-low with internal pull-up):
  - One leg of the button → GPIO 23 (physical pin 16)
  - Other leg           → GND    (physical pin 14)
"""

import os
import sys
import time
import signal
import logging
import requests

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [button-listener] %(levelname)s %(message)s",
)
logger = logging.getLogger("button_listener")

SERVER1_URL = os.getenv("SERVER1_URL", "http://pcb-server1-camera:8001")
BUTTON_GPIO_PIN = int(os.getenv("BUTTON_GPIO_PIN", "23"))
DEBOUNCE_MS = int(os.getenv("DEBOUNCE_MS", "300"))
BUTTON_MODE = os.getenv("BUTTON_MODE", "label")  # "label" or "inference"

# Try to import RPi.GPIO; if unavailable, exit gracefully
try:
    import RPi.GPIO as GPIO
except ImportError:
    logger.error(
        "RPi.GPIO is not available. "
        "This script is meant to run on a Raspberry Pi. Exiting."
    )
    sys.exit(1)


def trigger_capture_label():
    """Trigger capture + upload to Label Studio via Server 1."""
    try:
        logger.info("Button pressed → triggering capture (label mode)")
        r = requests.post(f"{SERVER1_URL}/api/v1/capture", timeout=30)
        r.raise_for_status()
        data = r.json()
        logger.info(f"Capture OK: {data.get('image_name', '?')} → Label Studio")
    except requests.RequestException as e:
        logger.error(f"Capture (label) failed: {e}")


def trigger_capture_inference():
    """Trigger capture + inference via Server 1 button route."""
    try:
        logger.info("Button pressed → triggering capture (inference mode)")
        r = requests.post(f"{SERVER1_URL}/api/v1/button-capture-predict", timeout=60)
        r.raise_for_status()
        data = r.json()
        quality = data.get("overall_quality", "?")
        count = data.get("detection_count", 0)
        logger.info(f"Inference result: quality={quality}, detections={count}")
    except requests.RequestException as e:
        logger.error(f"Capture (inference) failed: {e}")


def button_callback(channel):
    """Called on button press (falling edge on GPIO pin)."""
    if BUTTON_MODE == "inference":
        trigger_capture_inference()
    else:
        trigger_capture_label()


def main():
    logger.info(
        f"Starting button listener: GPIO={BUTTON_GPIO_PIN}, "
        f"mode={BUTTON_MODE}, server={SERVER1_URL}"
    )

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(BUTTON_GPIO_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    GPIO.add_event_detect(
        BUTTON_GPIO_PIN,
        GPIO.FALLING,
        callback=button_callback,
        bouncetime=DEBOUNCE_MS,
    )

    logger.info("Listening for button presses… (Ctrl+C to stop)")

    # Keep the process alive
    stop = False

    def handle_signal(signum, frame):
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        while not stop:
            time.sleep(1)
    finally:
        GPIO.cleanup()
        logger.info("GPIO cleaned up. Exiting.")


if __name__ == "__main__":
    main()
