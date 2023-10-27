import logging

from threading import Lock

import openai

from .log import ShutdownHandler
from .log import BandsFormatter


# pylint: disable=too-few-public-methods
class AI:
    def __init__(self, debug=None):
        self.openai = openai

        self.logger = None
        self.debug = debug

        self.mutex = Lock()

        self.keys = None
        self.key_index = -1

    def first_run(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG if self.debug else logging.INFO)

        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG if self.debug else logging.INFO)

        handler.setFormatter(BandsFormatter())

        self.logger.addHandler(handler)
        self.logger.addHandler(ShutdownHandler())

        self.logger.info("initialized")

        self.rotate_key()

    def rotate_key(self):
        self.logger.info("rotating keys")

        if self.keys:
            if self.key_index >= (len(self.keys) - 1):
                self.key_index = 0
            else:
                self.key_index += 1

            self.logger.info("rotated keys, current key index is: %s", self.key_index)

            self.openai.api_key = self.keys[self.key_index]["key"]
        else:
            self.openai.api_key = None
            self.logger.warning("OpenAI api key is set to None")
