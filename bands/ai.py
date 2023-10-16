import json
import os

import openai


class AI:
    _OPENAI_KEYS_FILE = (
        f"{os.path.dirname(os.path.realpath(__file__))}/files/openai_keys.json"
    )

    def __init__(self):
        self.openai = openai

        self.keys = None
        self.key_index = -1

        self.run()

    def run(self):
        self.parse_json()
        self.rotate_key()

    def parse_json(self):
        if os.path.isfile(self._OPENAI_KEYS_FILE):
            with open(self._OPENAI_KEYS_FILE, "r", encoding="utf-8") as keys_file:
                self.keys = json.loads(keys_file.read())["openai_keys"]
        else:
            self.keys = None

    def rotate_key(self):
        if not self.keys:
            self.openai.api_key = None
            return

        if self.key_index >= 3:
            self.key_index = 0
        else:
            self.key_index += 1

        self.openai.api_key = self.keys[self.key_index]["key"]
