import openai


# pylint: disable=too-few-public-methods
class AI:
    def __init__(self):
        self.openai = openai

        self.keys = None
        self.key_index = -1

    def rotate_key(self):
        if self.keys:
            if self.key_index >= 3:
                self.key_index = 0
            else:
                self.key_index += 1

            self.openai.api_key = self.keys[self.key_index]["key"]
        else:
            self.openai.api_key = None
