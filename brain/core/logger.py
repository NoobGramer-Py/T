import logging
import sys
from datetime import datetime


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)

    class Formatter(logging.Formatter):
        LEVELS = {
            logging.DEBUG:    "\033[90mDEBUG\033[0m",
            logging.INFO:     "\033[36mINFO \033[0m",
            logging.WARNING:  "\033[33mWARN \033[0m",
            logging.ERROR:    "\033[31mERROR\033[0m",
            logging.CRITICAL: "\033[35mCRIT \033[0m",
        }

        def format(self, record: logging.LogRecord) -> str:
            level = self.LEVELS.get(record.levelno, record.levelname)
            time  = datetime.now().strftime("%H:%M:%S")
            return f"[{time}] {level} [{record.name}] {record.getMessage()}"

    handler.setFormatter(Formatter())
    logger.addHandler(handler)
    logger.propagate = False
    return logger
