import json

from threading import Lock

from .log import set_logger


class Quote:
    def __init__(self, debug=False):
        self.logger = None
        self.debug = debug

        self.mutex = Lock()

        self.file = None

        self._first_run()

    def _first_run(self):
        self.logger = set_logger(__name__, self.debug)
        self.logger.info("initialized")

    def read_quotes(self):
        self.logger.debug("reading quotes file")

        with open(self.file, "r", encoding="utf-8") as file:
            quotes = json.loads(file.read())

        return quotes

    def write_quotes(self, quotes):
        self.logger.debug("writing quotes file")

        with open(self.file, "w", encoding="utf-8") as file:
            file.write(json.dumps(quotes))
