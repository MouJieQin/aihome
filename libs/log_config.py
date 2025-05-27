import logging
from logging.handlers import TimedRotatingFileHandler
import colorlog


class CustomFormatter(logging.Formatter):
    grey = "\x1b[38;20m"
    green = "\x1b[32;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "%(asctime)s - %(levelname)s: %(message)s"  # type: ignore

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: green + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%H:%M:%S")
        return formatter.format(record)


def setup_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    file_handler = TimedRotatingFileHandler(
        filename="logs/run.log",
        when="D",
        interval=1,
        backupCount=30,
    )
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s -%(module)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(CustomFormatter())
    logger.addHandler(console_handler)

    return logger


logger = setup_logger()
