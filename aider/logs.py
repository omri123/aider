import logging
import os


def initialize_logger():
    """Should be called once"""
    logger = logging.getLogger("aider")
    logger.setLevel(logging.INFO)

    if os.path.exists(".aider.log"):
        os.remove(".aider.log")

    logger.handlers.clear()
    handler = logging.FileHandler(".aider.log")
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def get_logger():
    return logging.getLogger("aider")
