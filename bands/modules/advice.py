import json
import os
import random

from bands.util import MIRCColors


# pylint: disable=too-few-public-methods
class Advice:
    ADV_FILE = f"{os.path.dirname(os.path.realpath(__file__))}/../files/advices.json"

    def __init__(self):
        # pylint: disable=invalid-name
        self.c = MIRCColors()

        self.adv_data = None

    def _parse_json(self):
        with open(self.ADV_FILE, "r", encoding="utf-8") as adv_file:
            self.adv_data = json.loads(adv_file.read())["advices"]

    def _run(self, user, user_args):
        if user_args:
            if len(user_args.split(" ")) > 1:
                finmsg = f"{self.c.WHITE}{user}{self.c.LBLUE},{self.c.RES} "
                finmsg += f"{self.c.LRED}multicast advice support disabled.{self.c.RES}"
                return finmsg

            target = user_args
        else:
            target = user

        self._parse_json()

        random.shuffle(self.adv_data)
        advice = self.adv_data.pop(random.randrange(len(self.adv_data)))

        finmsg = f"{self.c.WHITE}{target}{self.c.LBLUE},{self.c.RES} "
        finmsg += f"{self.c.GREEN}{advice}{self.c.RES}\n"

        return finmsg

    def print(self, core, user, user_args=None):
        msg = self._run(user, user_args)

        for line in msg.split("\n"):
            core.send_query(line)
