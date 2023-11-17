from bands.colors import MIRCColors

# pylint: disable=invalid-name
c = MIRCColors()


# pylint: disable=too-few-public-methods
class Auth:
    def __init__(self, user, user_args):
        self.user = user
        self.user_args = user_args

        self._run()

    def _run(self):
        if len(self.user_args) == 0:
            self.user.server.logger.warning(
                "%s ran ?auth without providing a secret", self.user.name
            )

            errmsg = f"{c.ERR} a secret is necessary."
            self.user.send_query(errmsg)
            return

        if self.user_args[0] == self.user.server.secret:
            self.user.server.admin = self.user.name

            self.user.server.logger.warning(
                "%s now has admin perms in %s", self.user.name, self.user.server.name
            )

            msg = f"{c.INFO} you are now authorized as the admin user "
            msg += f"for {self.user.server.name}."
            self.user.send_query(msg)
            return

        self.user.server.logger.warning("%s provided incorrect secret", self.user.name)

        errmsg = f"{c.ERR} incorrect secret provided."
        self.user.send_query(errmsg)
