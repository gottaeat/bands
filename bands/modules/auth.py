from bands.util import MIRCColors

# pylint: disable=invalid-name
c = MIRCColors()


# pylint: disable=too-few-public-methods
class Auth:
    def __init__(self, user):
        self.user = user

    def _run(self, user_args):
        if len(user_args) == 0:
            errmsg = f"{c.GREEN}[{c.LRED}E{c.GREEN}] "
            errmsg += f"{c.LRED}a secret is necessary.{c.RES}"
            self.user.send_query(errmsg)

            return

        if user_args == self.user.server.secret:
            self.user.server.admin = self.user.name

            msg = f"{c.GREEN}[{c.LBLUE}I{c.GREEN}] "
            msg += f"{c.LGREEN}{self.user.name} {c.WHITE}now has {c.LRED}admin "
            msg += f"perms {c.WHITE}in {c.GREEN}{self.user.server.name}.{c.RES}"
            self.user.send_query(msg)

            return

        errmsg = f"{c.GREEN}[{c.LRED}E{c.GREEN}] "
        errmsg += f"{c.LRED}secret is incorrect.{c.RES}"
        self.user.send_query(errmsg)

    def print(self, user_args):
        self._run(user_args)
