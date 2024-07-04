import json

from threading import Lock


class Quote:
    def __init__(self, parent_logger):
        self.logger = parent_logger.getChild(self.__class__.__name__)

        self.mutex = Lock()

        self.file = None

        self._first_run()

    def _first_run(self):
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
