import logging
import sys

from .colors import ANSIColors

c = ANSIColors()


class ShutdownHandler(logging.StreamHandler):
    def emit(self, record):
        if record.levelno >= logging.ERROR:
            sys.exit(1)


class BandsFormatter(logging.Formatter):
    _FMT_DATE = "%H:%M:%S"
    _FMT_BEGIN = f"{c.BBLK}[{c.LCYN}%(asctime)s{c.BBLK}][{c.BWHI}%(name)s{c.BBLK}]["
    _FMT_END = f"{c.BBLK}]{c.RES}"
    _FORMATS = {
        logging.NOTSET: c.LCYN,
        logging.DEBUG: c.BWHI,
        logging.INFO: c.BBLU,
        logging.WARNING: c.LGRN,
        logging.ERROR: c.LRED,
        logging.CRITICAL: c.LRED,
    }

    def format(self, record):
        finfmt = f"{self._FMT_BEGIN}{self._FORMATS.get(record.levelno)}"
        finfmt += f"%(levelname)-.1s{self._FMT_END} %(message)s"

        return logging.Formatter(
            fmt=finfmt, datefmt=self._FMT_DATE, validate=True
        ).format(record)


def set_root_logger(debug=False):
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG if debug else logging.INFO)

    formatter = BandsFormatter()
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.addHandler(ShutdownHandler())
