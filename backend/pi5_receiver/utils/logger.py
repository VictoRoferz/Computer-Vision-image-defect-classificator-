"""Logging configuration for PI5 Receiver service.

Provides structured logging with consistent formatting across the application.
"""

import logging
import sys
from typing import Optional


def setup_logger(
    name: str, level: str = "INFO", log_format: Optional[str] = None
) -> logging.Logger:
    """Configure and return a logger instance.

    Args:
        name: Logger name (typically __name__)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Optional custom format string

    Returns:
        logging.Logger: Configured logger instance
    """
    if log_format is None:
        log_format = (
            "%(asctime)s - %(name)s - %(levelname)s - "
            "%(funcName)s:%(lineno)d - %(message)s"
        )

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))

    # Formatter
    formatter = logging.Formatter(log_format)
    console_handler.setFormatter(formatter)

    # Add handler
    logger.addHandler(console_handler)

    return logger


def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    """Get or create a logger instance.

    Args:
        name: Logger name
        level: Logging level

    Returns:
        logging.Logger: Logger instance
    """
    return setup_logger(name, level)
