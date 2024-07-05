from bands.colors import MIRCColors
from bands.irc.util import unilen

c = MIRCColors()


class WAQuery:
    def __init__(self, channel, user, user_args):
        self.channel = channel
        self.user = user
        self.user_args = user_args

        self.logger = self.channel.logger.getChild(self.__class__.__name__)
        self.wa_client = channel.server.config.wa_client

        self._run()

    def _query(self):
        if self.wa_client is None:
            self.channel.send_query(f"{c.ERR} no api key provided.")
            return

        user_Q = " ".join(self.user_args[0:])

        if unilen(user_Q) > 300:
            err_msg = f"{c.ERR} query wider than 300 characters."
            self.channel.send_query(err_msg)
            return

        self.channel.send_query(f"{c.INFO} {self.user.nick}, querying: {user_Q}")

        try:
            query = self.wa_client.query(user_Q)
            response = next(query.results).text
        except StopIteration:
            self.channel.send_query(f"{c.ERR} no response.")
            return
        except:
            self.channel.send_query(f"{c.ERR} query failed.")
            self.logger.exception("query failed")

        if response is None:
            self.channel.send_query(f"{c.ERR} no plaintext response.")
            return

        for line in response.split("\n"):
            self.channel.send_query(f"{c.INFO} {line}")

    def _run(self):
        if len(self.user_args) == 0:
            self.channel.send_query(f"{c.ERR} an argument is required.")
            return

        self._query()
