import json
import os
import random
import re

from bands.colors import MIRCColors

# pylint: disable=invalid-name
c = MIRCColors()


# pylint: disable=too-few-public-methods
class Quake:
    QUAKE_FILE = (
        f"{os.path.dirname(os.path.realpath(__file__))}/../../../static/quake3.json"
    )

    def __init__(self, channel, user, user_args):
        self.channel = channel
        self.user = user
        self.user_args = user_args

        self.quake_data = None
        self.quote = None

        self._run()

    def _parse_json(self):
        with open(self.QUAKE_FILE, "r", encoding="utf-8") as quake_file:
            self.quake_data = json.loads(quake_file.read())["quotes"]

    def _pull(self):
        random.shuffle(self.quake_data)
        self.quote = re.sub(
            r"REPLACECHANNELNAME",
            f"{c.ORANGE}{self.channel.name}{c.RES}",
            re.sub(
                r"REPLACEUSERNICK",
                f"{c.LGREEN}{self.user.nick}{c.RES}",
                self.quake_data.pop(random.randrange(len(self.quake_data))),
            ),
        )

    def _run(self):
        self._parse_json()
        self._pull()

        self.channel.send_query(self.quote)
