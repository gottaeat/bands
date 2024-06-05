from bands.colors import MIRCColors

c = MIRCColors()


class Auth:
    def __init__(self, user, user_args):
        self.user = user
        self.user_args = user_args

        self._run()

    def _run(self):
        if not self.user.server.allow_admin:
            self.user.server.logger.warning(
                "%s (%s) tried to auth when authentication is disabled",
                self.user.nick,
                self.user.login,
            )

            self.user.send_query(f"{c.ERR} authentication is disabled.")
            return

        # auth is disabled server-wide
        if self.user.server.bad_pw_attempts >= 12:
            self.user.server.logger.warning(
                "%s (%s) tried to auth when authentication is disabled",
                self.user.nick,
                self.user.login,
            )

            self.user.send_query(f"{c.ERR} authentication is disabled.")
            return

        # auth is disabled for user
        if self.user.bad_pw_attempts >= 3:
            self.user.server.logger.warning(
                "%s (%s) failed 3 times in total when trying to authenticate",
                self.user.nick,
                self.user.login,
            )

            self.user.send_query(f"{c.ERR} authentication is disabled.")
            return

        # user provided no password
        if len(self.user_args) == 0:
            self.user.bad_pw_attempts += 1
            self.user.server.bad_pw_attempts += 1

            self.user.server.logger.warning(
                "%s (%s) ran ?auth without providing a secret (%s/3)",
                self.user.nick,
                self.user.login,
                self.user.bad_pw_attempts,
            )

            errmsg = f"{c.ERR} a secret is necessary. ({self.user.bad_pw_attempts}/3)"
            self.user.send_query(errmsg)
            return

        # user provided correct pass
        if self.user_args[0] == self.user.server.secret:
            self.user.server.admin = self.user

            self.user.server.logger.warning(
                "%s (%s) now has admin perms in %s",
                self.user.nick,
                self.user.login,
                self.user.server.name,
            )

            msg = f"{c.INFO} you are now authorized as the admin user "
            msg += f"for {self.user.server.name}."
            self.user.send_query(msg)
            return

        # user provided wrong pass
        self.user.bad_pw_attempts += 1
        self.user.server.bad_pw_attempts += 1

        self.user.server.logger.warning(
            "%s (%s) provided incorrect secret (%s/3)",
            self.user.nick,
            self.user.login,
            self.user.bad_pw_attempts,
        )

        errmsg = f"{c.ERR} incorrect secret provided. ({self.user.bad_pw_attempts}/3)"
        self.user.send_query(errmsg)
