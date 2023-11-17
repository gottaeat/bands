import json
import os
import random

from bands.irc.util import unilen
from bands.colors import MIRCColors

# pylint: disable=invalid-name
c = MIRCColors()


# pylint: disable=too-few-public-methods
class Advice:
    ADV_FILE = (
        f"{os.path.dirname(os.path.realpath(__file__))}/../../../static/advices.json"
    )

    def __init__(self, channel, user, user_args):
        self.channel = channel
        self.user = user
        self.user_args = user_args

        self.adv_data = None
        self.advice = None

        self._run()

    def _parse_json(self):
        with open(self.ADV_FILE, "r", encoding="utf-8") as adv_file:
            self.adv_data = json.loads(adv_file.read())["advices"]

    def _pull(self):
        random.shuffle(self.adv_data)
        self.advice = self.adv_data.pop(random.randrange(len(self.adv_data)))

    def _run(self):
        if len(self.user_args) > 0:
            if len(self.user_args) > 1:
                errmsg = f"{c.ERR} multicast advice support is disabled."
                self.channel.send_query(errmsg)
                return

            target = self.user_args[0]
        else:
            target = self.user.name

        if unilen(target) > self.channel.server.USER_NICKLIMIT:
            errmsg = f"{c.ERR} person in need of advice is wider than "
            errmsg += f"{self.channel.server.USER_NICKLIMIT} chars."
            self.channel.send_query(errmsg)
            return

        self._parse_json()
        self._pull()

        msg = f"{c.WHITE}{target}{c.LBLUE},{c.RES} "
        msg += f"{c.GREEN}{self.advice}{c.RES}\n"
        self.channel.send_query(msg)
