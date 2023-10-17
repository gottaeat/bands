import json

import openai


class AI:
    def __init__(self):
        self.keys_file = None

        self.keys = None
        self.key_index = -1

        self.openai = openai

    def parse_json(self):
        try:
            with open(self.keys_file, "r", encoding="utf-8") as keys_file:
                self.keys = json.loads(keys_file.read())["openai_keys"]
        except Exception as exc:
            # pylint: disable=raise-missing-from
            raise ValueError(f"E: parsing {self.keys_file} failed:\n{exc}")

    def rotate_key(self):
        if self.key_index >= 3:
            self.key_index = 0
        else:
            self.key_index += 1

        self.openai.api_key = self.keys[self.key_index]["key"]

    def run(self):
        self.parse_json()
        self.rotate_key()
