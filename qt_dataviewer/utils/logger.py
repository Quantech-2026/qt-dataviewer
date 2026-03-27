import logging
import os
import sys

from .configuration import get_configuration


def configure_logging():
    cfg = get_configuration()
    if not cfg.get("logging.enabled", True):
        return
    path = cfg.get("logging.file_location", "~/.qt-dataviewer/logs")
    filename = cfg.get("logging.file_name", "qt-dataviewer.log")
    file_level = cfg.get("logging.file_level", "INFO")
    file_format = "%(asctime)s | %(name)s | %(levelname)s | %(module)s | %(funcName)s:%(lineno)d | %(message)s"
    console_level = cfg.get("logging.console_level", "WARNING")

    path = os.path.expanduser(path)
    os.makedirs(path, exist_ok=True)
    file = os.path.join(path, filename)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    for handler in root_logger.handlers:
        handler.close()
        root_logger.removeHandler(handler)

    file_handler = logging.handlers.TimedRotatingFileHandler(
        file,
        when="midnight",
        backupCount=15,
        encoding="utf-8"
    )

    file_handler.setLevel(file_level)
    file_handler.setFormatter(logging.Formatter(file_format))
    root_logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler(stream=sys.stderr)
    stream_handler.setLevel(console_level)
    stream_handler.setFormatter(logging.Formatter(file_format))
    root_logger.addHandler(stream_handler)

    logger = logging.getLogger(__name__)
    logger.info("Start logging")

    for name in ["matplotlib", "h5py", "qcodes"]:
        logging.getLogger(name).setLevel(logging.INFO)
