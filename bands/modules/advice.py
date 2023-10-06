import json
import os
import random

from bands.util import unilen
from bands.util import MIRCColors

# pylint: disable=invalid-name
c = MIRCColors()


# pylint: disable=too-few-public-methods
class Advice:
    ADV_FILE = f"{os.path.dirname(os.path.realpath(__file__))}/../files/advices.json"

    def __init__(self):
        self.adv_data = None

    def _parse_json(self):
        with open(self.ADV_FILE, "r", encoding="utf-8") as adv_file:
            self.adv_data = json.loads(adv_file.read())["advices"]

    def _run(self, core, user, user_args):
        if user_args:
            if len(user_args.split(" ")) > 1:
                finmsg = f"{c.WHITE}{user}{c.LBLUE},{c.RES} "
                finmsg += f"{c.LRED}multicast advice support disabled.{c.RES}"

                return finmsg

            target = user_args
        else:
            target = user

        if unilen(str(target)) > core.USER_NICKLIMIT:
            finmsg = f"{c.WHITE}{user}{c.LBLUE},{c.RES} "
            finmsg += f"{c.LRED}person in need of advice is wider than "
            finmsg += f"{core.USER_NICKLIMIT} chars.{c.RES}"

            return finmsg

        self._parse_json()

        random.shuffle(self.adv_data)
        advice = self.adv_data.pop(random.randrange(len(self.adv_data)))

        finmsg = f"{c.WHITE}{target}{c.LBLUE},{c.RES} "
        finmsg += f"{c.GREEN}{advice}{c.RES}\n"

        return finmsg

    def print(self, core, user, user_args=None):
        msg = self._run(core, user, user_args)

        for line in msg.split("\n"):
            core.send_query(line)
