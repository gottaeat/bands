import json
import os
import random
import re

from bands.colors import MIRCColors

c = MIRCColors()


class Quake:
    QUAKE_FILE = (
        f"{os.path.dirname(os.path.realpath(__file__))}/../../../static/quake3.json"
    )

    def __init__(self, channel, user, user_args):
        self.channel = channel
        self.user = user
        self.user_args = user_args

        self._run()

    def _quake(self):
        with open(self.QUAKE_FILE, "r", encoding="utf-8") as quake_file:
            quotes = json.loads(quake_file.read())["quotes"]

        quote = re.sub(
            r"REPLACECHANNELNAME",
            f"{c.ORANGE}{self.channel.name}{c.RES}",
            re.sub(
                r"REPLACEUSERNICK",
                f"{c.LGREEN}{self.user.nick}{c.RES}",
                re.sub(
                    r"REPLACEBOTNAME",
                    f"{c.PINK}{self.channel.server.botname}{c.RES}",
                    quotes.pop(random.randrange(len(quotes))),
                ),
            ),
        )

        self.channel.send_query(quote)

    def _run(self):
        self._quake()
