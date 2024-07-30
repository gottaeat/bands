import json
import os
import random

from bands.irc.util import unilen
from bands.colors import MIRCColors

c = MIRCColors()


class Advice:
    ADV_FILE = (
        f"{os.path.dirname(os.path.realpath(__file__))}/../../../static/advices.json"
    )

    def __init__(self, channel, user, user_args):
        self.channel = channel
        self.user = user
        self.user_args = user_args

        self._run()

    def _advice(self):
        if not self.user_args:
            target = self.user.nick
        else:
            if len(self.user_args) > 1:
                errmsg = f"{c.ERR} multicast advice support is disabled."
                return self.channel.send_query(errmsg)

            target = self.user_args[0]

        if unilen(target) > self.channel.server.USER_NICKLIMIT:
            errmsg = f"{c.ERR} person in need of advice is wider than "
            errmsg += f"{self.channel.server.USER_NICKLIMIT} chars."
            return self.channel.send_query(errmsg)

        with open(self.ADV_FILE, "r", encoding="utf-8") as adv_file:
            advices = json.loads(adv_file.read())["advices"]

        advice = advices.pop(random.randrange(len(advices)))

        self.channel.send_query(
            f"{c.WHITE}{target}{c.LBLUE},{c.RES} {c.GREEN}{advice}{c.RES}\n"
        )

    def _run(self):
        self._advice()
