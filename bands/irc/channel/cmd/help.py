from bands.colors import MIRCColors
from bands import __version__ as pkg_version

c = MIRCColors()


class Help:
    def __init__(self, channel, user, user_args):
        self.channel = channel
        self.user = user  # unused
        self.user_args = user_args  # unused

        self._run()

    def _run(self):
        # fmt: off
        msg  = f"{c.WHITE}│ ├ {c.LGREEN}?advice{c.RES} {{nick}}\n"
        msg += f"{c.WHITE}│ ├ {c.LGREEN}?ai{c.RES}     [query]\n"
        msg += f"{c.WHITE}│ ├ {c.LGREEN}?bands{c.RES}\n"
        msg += f"{c.WHITE}│ ├ {c.LGREEN}?bj{c.RES}     ?bj help\n"
        msg += f"{c.WHITE}│ ├ {c.LGREEN}?doot{c.RES}   ?doot help\n"
        msg += f"{c.WHITE}│ ├ {c.LGREEN}?piss{c.RES}   [nick]\n"
        msg += f"{c.WHITE}│ ├ {c.LGREEN}?quake{c.RES}\n"
        msg += f"{c.WHITE}│ ├ {c.LGREEN}?quote{c.RES}  ?quote help\n"
        msg += f"{c.WHITE}│ ├ {c.LGREEN}?tarot{c.RES}  ?tarot help\n"
        msg += f"{c.WHITE}│ └ {c.LGREEN}?wa{c.RES}     [query]\n"
        msg += f"{c.WHITE}├ {c.LRED}ver{c.RES}       {pkg_version}\n"
        msg += f"{c.WHITE}└ {c.LRED}src{c.RES}       https://github.com/gottaeat/bands"
        # fmt: on

        self.channel.send_query(msg)
