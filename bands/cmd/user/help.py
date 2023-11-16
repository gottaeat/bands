from bands.colors import MIRCColors

# pylint: disable=invalid-name
c = MIRCColors()


# pylint: disable=too-few-public-methods
class Help:
    def __init__(self, user, user_args):
        self.user = user
        self.user_args = user_args

        self._run()

    def _run(self):
        msg = f"{c.WHITE}├ {c.LRED}usage{c.RES}\n"

        if self.user.name == self.user.server.admin:
            msg += f"{c.WHITE}│  ├ {c.LGREEN}?auth{c.RES}   [secret]\n"
            msg += f"{c.WHITE}│  └ {c.LGREEN}?openai{c.RES} [load|status]\n"
            msg += f"{c.WHITE}└ {c.LRED}src{c.RES}        https://github.com/gottaeat/bands"
        else:
            msg += f"{c.WHITE}│  └ {c.LGREEN}?auth{c.RES} [secret]\n"
            msg += (
                f"{c.WHITE}└ {c.LRED}src{c.RES}      https://github.com/gottaeat/bands"
            )

        self.user.send_query(msg)
