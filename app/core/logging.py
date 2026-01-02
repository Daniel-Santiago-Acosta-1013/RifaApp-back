import logging


def configure_logging() -> logging.Logger:
    logger = logging.getLogger("rifaapp")
    if not logger.handlers:
        logging.basicConfig(level=logging.INFO)
    return logger
