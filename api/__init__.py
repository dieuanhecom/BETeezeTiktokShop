import logging
import os

os.makedirs("logs", exist_ok=True)


class RelativePathFilter(logging.Filter):
    def filter(self, record):
        record.pathname = os.path.realpath(record.pathname).replace(os.getcwd(), "")[1:]
        return True


def setup_logging(logger, is_root=False, level=logging.INFO):
    # Set up the log formatter
    msg_format = "%(asctime)s [%(levelname)8s] %(message)s (%(name)s - %(pathname)s:%(lineno)d)"
    date_format = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(fmt=msg_format, datefmt=date_format)

    # File Handler
    file_handler = logging.FileHandler("logs/app.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.addFilter(RelativePathFilter())
    logger.addHandler(file_handler)

    # Stream Handler
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.addFilter(RelativePathFilter())
    logger.addHandler(stream_handler)

    if is_root:
        logger.propagate = False

    logger.setLevel(level)
