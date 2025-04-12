# logging_config.py
import logging
from config import LOG_LEVEL

def configure_logging():
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
