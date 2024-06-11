from bands.colors import MIRCColors

c = MIRCColors()


class Help:
    def __init__(self, user, user_args):
        self.user = user
        self.user_args = user_args

        self._run()

    def _run(self):
        if self.user == self.user.server.admin:
            msg = f"{c.WHITE}│  ├ {c.LGREEN}?auth{c.RES}   [secret]\n"
            msg += f"{c.WHITE}│  └ {c.LGREEN}?rcon{c.RES}   [dc|raw|status]\n"
        else:
            msg = f"{c.WHITE}│  └ {c.LGREEN}?auth{c.RES}   [secret]\n"

        msg += f"{c.WHITE}└ {c.LRED}src{c.RES}        https://github.com/gottaeat/bands"
        self.user.send_query(msg)
