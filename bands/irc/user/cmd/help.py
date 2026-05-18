from bands.colors import MIRCColors
from bands import __version__ as pkg_version

c = MIRCColors()


class Help:
    def __init__(self, user, user_args):
        self.user = user
        self.user_args = user_args

        self._run()

    def _run(self):
        if self.user == self.user.server.admin:
            return self.user.send_query(
                f"{c.WHITE}├ {c.LGREEN}?auth{c.RES} [secret]\n"
                f"{c.WHITE}└ {c.LGREEN}?rcon{c.RES} help\n"
            )

        self.user.send_query(f"{c.WHITE}└ {c.LGREEN}?auth{c.RES} [secret]\n")
