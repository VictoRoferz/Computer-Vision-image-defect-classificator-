"""Main entry point for PI3 Sender service.

This module initializes all components and starts the watcher service.
"""

import signal
import sys

from config import get_settings
from services import CameraService, SenderService, WatcherService
from utils.logger import get_logger

logger = get_logger(__name__)

# Global watcher instance for signal handling
watcher = None


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully.

    Args:
        signum: Signal number
        frame: Current stack frame
    """
    logger.info(f"Received signal {signum}, shutting down...")

    if watcher:
        watcher.stop()

    sys.exit(0)


def main():
    """Main entry point for PI3 Sender service."""
    global watcher

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("Starting PI3 Sender service...")

    # Load settings
    settings = get_settings()

    # Configure logging
    from utils.logger import setup_logger
    setup_logger(__name__, settings.LOG_LEVEL)

    # Initialize services
    camera_service = CameraService(settings)
    sender_service = SenderService(settings)

    # Check connectivity to PI5 Receiver
    logger.info("Checking connectivity to PI5 Receiver...")
    if not sender_service.health_check():
        logger.warning(
            "PI5 Receiver is not reachable. Service will continue but uploads may fail."
        )

    # Start watcher service
    watcher = WatcherService(settings, sender_service)

    try:
        logger.info("PI3 Sender service started successfully")
        watcher.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        # Cleanup
        camera_service.release()
        logger.info("PI3 Sender service stopped")


if __name__ == "__main__":
    main()
