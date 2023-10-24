from bands.util import unilen
from bands.util import drawbox
from bands.colors import MIRCColors

# pylint: disable=invalid-name
c = MIRCColors()


# pylint: disable=too-few-public-methods
class Piss:
    def __init__(self, channel):
        self.channel = channel

    def print(self, user, target):
        target = " ".join(target)

        if len(target) == 0:
            msg = f"{c.ORANGE}{user}{c.LBLUE}, "
            msg += f"{c.YELLOW}on who?{c.RES}"
            self.channel.send_query(msg)

            return

        if unilen(target) > self.channel.server.USER_NICKLIMIT:
            msg = f"{c.ORANGE}{user}{c.LBLUE}, {c.YELLOW}target "
            msg += f"{c.LRED}is wider than {self.channel.server.USER_NICKLIMIT} chars.{c.RES}"
            self.channel.send_query(msg)

            return

        msg = f"     {c.WHITE}ë{c.RES} \n"
        msg += f"   {c.WHITE}.-║- {c.LBLUE}<- {c.ORANGE}{user}{c.RES} \n"
        msg += f"   {c.ORANGE}╭{c.LRED}╰{c.WHITE}\\{c.RES} \n"
        msg += f"   {c.YELLOW}┊{c.WHITE}/ \\{c.RES} \n"
        msg += f"   {c.YELLOW}┊{c.RES} \n"
        msg += f" {c.YELLOW}{target}{c.RES} \n"

        msg = drawbox(msg, "single")
        msg += f"{c.WHITE} → {c.ORANGE}{target} "
        msg += f"{c.WHITE}just got {c.YELLOW}pissed on "
        msg += f"{c.WHITE}by {c.ORANGE}{user}"
        msg += f"{c.WHITE}.{c.RES}"

        self.channel.send_query(msg)
