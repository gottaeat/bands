import json
import logging

from threading import Lock

from .log import BandsFormatter
from .log import ShutdownHandler


class Quote:
    def __init__(self, debug=None):
        self.logger = None
        self.debug = debug

        self.mutex = Lock()

        self.quotes_file = None

    def first_run(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG if self.debug else logging.INFO)

        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG if self.debug else logging.INFO)

        handler.setFormatter(BandsFormatter())

        self.logger.addHandler(handler)
        self.logger.addHandler(ShutdownHandler())

        self.logger.info("initialized")

    def read_quotes(self):
        self.logger.info("reading quotes file")

        with open(self.quotes_file, "r", encoding="utf-8") as file:
            quotes = json.loads(file.read())

        return quotes

    def write_quotes(self, quotes):
        self.logger.info("writing quotes file")

        with open(self.quotes_file, "w", encoding="utf-8") as file:
            file.write(json.dumps(quotes))
