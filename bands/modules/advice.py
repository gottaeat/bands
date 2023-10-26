import json
import os
import random

from bands.util import unilen
from bands.colors import MIRCColors

# pylint: disable=invalid-name
c = MIRCColors()


# pylint: disable=too-few-public-methods
class Advice:
    ADV_FILE = f"{os.path.dirname(os.path.realpath(__file__))}/../files/advices.json"

    def __init__(self, channel, user, user_args):
        self.channel = channel
        self.user = user
        self.user_args = user_args

        self.adv_data = None

        self.channel.send_query(self._run())

    def _parse_json(self):
        with open(self.ADV_FILE, "r", encoding="utf-8") as adv_file:
            self.adv_data = json.loads(adv_file.read())["advices"]

    def _run(self):
        if len(self.user_args) > 0:
            if len(self.user_args) > 1:
                finmsg = f"{c.WHITE}{self.user.name}{c.LBLUE},{c.RES} "
                finmsg += f"{c.LRED}multicast advice support disabled.{c.RES}"

                return finmsg

            target = self.user_args[0]
        else:
            target = self.user.name

        if unilen(target) > self.channel.server.USER_NICKLIMIT:
            finmsg = f"{c.WHITE}{self.user.name}{c.LBLUE},{c.RES} "
            finmsg += f"{c.LRED}person in need of advice is wider than "
            finmsg += f"{self.channel.server.USER_NICKLIMIT} chars.{c.RES}"

            return finmsg

        self._parse_json()

        random.shuffle(self.adv_data)
        advice = self.adv_data.pop(random.randrange(len(self.adv_data)))

        finmsg = f"{c.WHITE}{target}{c.LBLUE},{c.RES} "
        finmsg += f"{c.GREEN}{advice}{c.RES}\n"

        return finmsg
