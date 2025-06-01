# Import the logging module which provides a flexible framework for emitting log messages
import logging

# Import TimedRotatingFileHandler from logging.handlers to create log files that rotate at certain intervals
from logging.handlers import TimedRotatingFileHandler


class CustomFormatter(logging.Formatter):
    """
    A custom formatter class for logging that adds color to log messages based on their level.
    """

    # ANSI escape code for grey text
    grey = "\x1b[38;20m"
    # ANSI escape code for green text
    green = "\x1b[32;20m"
    # ANSI escape code for yellow text
    yellow = "\x1b[33;20m"
    # ANSI escape code for red text
    red = "\x1b[31;20m"
    # ANSI escape code for bold red text
    bold_red = "\x1b[31;1m"
    # ANSI escape code to reset text color
    reset = "\x1b[0m"
    # The base log format string used for all log levels
    log_format = "%(asctime)s - %(levelname)s: %(message)s"

    # A dictionary mapping log levels to their corresponding colored log formats
    FORMATS = {
        logging.DEBUG: grey + log_format + reset,
        logging.INFO: green + log_format + reset,
        logging.WARNING: yellow + log_format + reset,
        logging.ERROR: red + log_format + reset,
        logging.CRITICAL: bold_red + log_format + reset,
    }

    def format(self, record):
        """
        Format the specified log record and return the formatted string.

        Args:
            record (logging.LogRecord): The log record to be formatted.

        Returns:
            str: The formatted log message with color based on the log level.
        """
        # Get the appropriate log format based on the log record's level
        log_fmt = self.FORMATS.get(record.levelno)
        # Create a new Formatter instance with the selected format and time format
        formatter = logging.Formatter(log_fmt, datefmt="%H:%M:%S")
        # Return the formatted log message
        return formatter.format(record)


def setup_logger():
    """
    Set up and configure a logger with both file and console handlers.

    Returns:
        logging.Logger: A configured logger instance.
    """
    # Get the root logger
    logger = logging.getLogger()
    import os

    log_level = os.getenv("LOG_LEVEL", "INFO")
    if log_level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        logger.setLevel(getattr(logging, log_level))
    else:
        logger.setLevel(logging.INFO)

    # Create a TimedRotatingFileHandler that rotates log files daily
    file_handler = TimedRotatingFileHandler(
        # The path to the log file
        filename="logs/run.log",
        # Rotate the log file daily
        when="D",
        # Rotate every 1 day
        interval=1,
        # Keep a maximum of 30 backup log files
        backupCount=30,
    )
    # Create a formatter for the file handler
    file_formatter = logging.Formatter(
        # The log format string for the file handler
        "%(asctime)s - %(name)s - %(levelname)s -%(module)s: %(message)s",
        # The date format string for the file handler
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler.setFormatter(file_formatter)
    # Add the file handler to the logger
    logger.addHandler(file_handler)

    # Create a StreamHandler for logging to the console
    console_handler = logging.StreamHandler()
    # Set the custom formatter for the console handler
    console_handler.setFormatter(CustomFormatter())
    # Add the console handler to the logger
    logger.addHandler(console_handler)

    # Return the configured logger
    return logger


# Set up and get the configured logger
logger = setup_logger()
