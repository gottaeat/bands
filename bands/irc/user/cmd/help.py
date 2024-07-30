from bands.colors import MIRCColors
from bands import __version__ as pkg_version

c = MIRCColors()


class Help:
    def __init__(self, user, user_args):
        self.user = user
        self.user_args = user_args

        self._run()

    def _run(self):
        # fmt: off
        if self.user == self.user.server.admin:
            msg  = f"{c.WHITE}│ ├ {c.LGREEN}?auth{c.RES} [secret]\n"
            msg += f"{c.WHITE}│ └ {c.LGREEN}?rcon{c.RES} help\n"
        else:
            msg  = f"{c.WHITE}│ └ {c.LGREEN}?auth{c.RES} [secret]\n"
        # fmt: on

        msg += f"{c.WHITE}│ {c.LRED}ver{c.RES} {pkg_version}\n"
        msg += f"{c.WHITE}└ {c.LRED}src{c.RES} https://github.com/gottaeat/bands"
        self.user.send_query(msg)
