from bands.colors import MIRCColors

c = MIRCColors()


class WAQuery:
    def __init__(self, channel, user, user_args):
        self.channel = channel
        self.user = user
        self.user_args = user_args

        self.wa_client = channel.server.config.wa_client

        self._run()

    def _cmd_help(self):
        self.channel.send_query(f"{c.WHITE}└ {c.LGREEN}[query]{c.RES}")

    def _query(self):
        if self.wa_client is None:
            self.channel.send_query(f"{c.ERR} no api key provided.")
            return

        user_Q = " ".join(self.user_args[0:])
        self.channel.send_query(f"{c.INFO} {self.user.nick}, querying: {user_Q}")

        try:
            query = self.wa_client.query(user_Q)
            response = next(query.results).text
        except StopIteration:
            self.channel.send_query(f"{c.ERR} no response.")
            return
        except Exception as exc:
            self.channel.server.logger.warning("%s failed with:\n%s", __name__, exc)
            self.channel.send_query(f"{c.ERR} query failed.")
            return

        for line in response.split("\n"):
            self.channel.send_query(f"{c.INFO} {line}")

    def _run(self):
        if len(self.user_args) == 0:
            self._cmd_help()
            return

        self._query()
