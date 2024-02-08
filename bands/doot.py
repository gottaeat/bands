import json
import logging

from threading import Lock

from .log import BandsFormatter
from .log import ShutdownHandler


class Doot:
    def __init__(self, debug=None):
        self.logger = None
        self.debug = debug

        self.mutex = Lock()

        self.file = None

        self._first_run()

    def _first_run(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG if self.debug else logging.INFO)

        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG if self.debug else logging.INFO)

        handler.setFormatter(BandsFormatter())

        self.logger.addHandler(handler)
        self.logger.addHandler(ShutdownHandler())

        self.logger.info("initialized")

    def read_doots(self):
        self.logger.debug("reading doots file")

        with open(self.file, "r", encoding="utf-8") as file:
            doots = json.loads(file.read())

        return doots

    def write_doots(self, doots):
        self.logger.debug("writing doots file")

        with open(self.file, "w", encoding="utf-8") as file:
            file.write(json.dumps(doots))
