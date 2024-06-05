from bands.irc.util import unilen, drawbox
from bands.colors import MIRCColors

c = MIRCColors()


class Piss:
    def __init__(self, channel, user, user_args):
        self.channel = channel
        self.user = user
        self.user_args = user_args

        self._run()

    def _run(self):
        target = " ".join(self.user_args)

        if len(target) == 0:
            errmsg = f"{c.ERR} on who?"
            self.channel.send_query(errmsg)
            return

        if unilen(target) > self.channel.server.USER_NICKLIMIT:
            errmsg = f"{c.ERR} pissee is wider than "
            errmsg += f"{self.channel.server.USER_NICKLIMIT} chars."
            self.channel.send_query(errmsg)
            return

        msg = f"     {c.WHITE}ë{c.RES} \n"
        msg += f"   {c.WHITE}.-║- {c.LBLUE}<- {c.ORANGE}{self.user.nick}{c.RES} \n"
        msg += f"   {c.ORANGE}╭{c.LRED}╰{c.WHITE}\\{c.RES} \n"
        msg += f"   {c.YELLOW}┊{c.WHITE}/ \\{c.RES} \n"
        msg += f"   {c.YELLOW}┊{c.RES} \n"
        msg += f" {c.YELLOW}{target}{c.RES} \n"

        msg = drawbox(msg, "single")
        msg += f"{c.WHITE} → {c.ORANGE}{target} "
        msg += f"{c.WHITE}just got {c.YELLOW}pissed on "
        msg += f"{c.WHITE}by {c.ORANGE}{self.user.nick}"
        msg += f"{c.WHITE}.{c.RES}"

        self.channel.send_query(msg)
