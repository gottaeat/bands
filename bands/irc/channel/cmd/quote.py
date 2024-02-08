import datetime
import random
import time

from bands.colors import MIRCColors

# pylint: disable=invalid-name
c = MIRCColors()


# pylint: disable=too-few-public-methods
class Quote:
    def __init__(self, channel, user, user_args):
        self.channel = channel
        self.user = user
        self.user_args = user_args

        self.quote = self.channel.server.quote

        self._run()

    @staticmethod
    def _get_tstamp(epoch):
        tstamp_obj = datetime.datetime.fromtimestamp(int(epoch)).astimezone()
        tzone = tstamp_obj.tzinfo.tzname(tstamp_obj)

        return f"{tstamp_obj.strftime('%Y/%m/%d %T')} {tzone}"

    def _cmd_help(self):
        msg = f"{c.LRED}usage{c.RES}\n"
        msg += f"{c.WHITE}├ {c.LGREEN}add{c.RES}    [nick] [quoted message]\n"
        msg += f"{c.WHITE}├ {c.LGREEN}get{c.RES}    [nick]\n"
        msg += f"{c.WHITE}├ {c.LGREEN}random{c.RES}\n"
        msg += f"{c.WHITE}└ {c.LGREEN}help{c.RES}"

        self.channel.send_query(msg)

    def _run(self):
        if len(self.user_args) == 0 or self.user_args[0] == "help":
            self._cmd_help()
            return

        if self.user_args[0] == "add":
            self._cmd_add()
            return

        if self.user_args[0] == "get":
            self._cmd_get()
            return

        if self.user_args[0] == "random":
            self._cmd_random()
            return

        self._cmd_help()

    def _cmd_add(self):
        # no nick
        try:
            quoted_user = self.user_args[1]
        except IndexError:
            self.channel.send_query(f"{c.ERR} must provide a nick.")
            return

        # list to str
        quoted_msg = " ".join(self.user_args[2:])

        # no quote
        if len(quoted_msg) == 0:
            self.channel.send_query(f"{c.ERR} no quote body.")
            return

        # get ChannelUser
        for channeluser in self.channel.user_list:
            if channeluser.nick.lower() == quoted_user.lower():
                user = channeluser
                break

        # self quote || no ChannelUser obj
        try:
            if user.nick == self.user.nick and user.login == self.user.login:
                self.channel.send_query(f"{c.ERR} cannot quote yourself.")
                return
        except UnboundLocalError:
            self.channel.send_query(f"{c.ERR} no such nick: {quoted_user}.")
            return

        # check if said
        if quoted_msg not in user.chats:
            self.channel.send_query(f"{c.ERR} {user.nick} never said that.")
            return

        # update jayson
        with self.quote.mutex:
            quotes = self.quote.read_quotes()

            # entry for server does not exist
            if self.channel.server.name not in quotes["quotes"][0].keys():
                quotes["quotes"][0][self.channel.server.name] = []

                self.channel.server.logger.info(
                    "created quote entry for: %s", self.channel.server.name
                )

            # gen quote
            quote = {
                "timestamp": time.strftime("%s"),
                "nick": user.nick,
                "msg": quoted_msg,
            }

            quotes["quotes"][0][self.channel.server.name].append(quote)

            self.quote.write_quotes(quotes)

        self.channel.send_query(f"{c.INFO} quote added.")

    def _cmd_get(self):
        # no nick
        try:
            quoted_user = self.user_args[1]
        except IndexError:
            self.channel.send_query(f"{c.ERR} must provide a nick.")
            return

        # read jayson
        with self.quote.mutex:
            quotes = self.quote.read_quotes()

        # entry for server does not exist
        if self.channel.server.name not in quotes["quotes"][0].keys():
            err_msg = f"{c.ERR} {self.channel.server.name} does not have "
            err_msg += "anyone quoted."
            self.channel.send_query(err_msg)
            return

        # find user entries
        users_quotes = []
        for item in quotes["quotes"][0][self.channel.server.name]:
            if item["nick"].lower() == quoted_user.lower():
                users_quotes.append(item)

        # user does not exist
        if len(users_quotes) == 0:
            err_msg = f"{c.ERR} {quoted_user} has no recorded quotes in "
            err_msg = "{self.channel.server.name}."
            self.channel.send_query(err_msg)

            return

        # user does exist
        random.shuffle(users_quotes)
        quote = users_quotes.pop(random.randrange(len(users_quotes)))
        tstamp = self._get_tstamp(quote["timestamp"])

        msg = f"{quote['nick']} @ {tstamp}: \"{quote['msg']}\""
        self.channel.send_query(f"{c.INFO} {msg}")

    def _cmd_random(self):
        # read jayson
        with self.quote.mutex:
            quotes = self.quote.read_quotes()

        # entry for server does not exist
        if self.channel.server.name not in quotes["quotes"][0].keys():
            err_msg = f"{c.ERR} {self.channel.server.name} does not have "
            err_msg += "anyone quoted."
            self.channel.send_query(err_msg)

            return

        # get server entries
        server_quotes = quotes["quotes"][0][self.channel.server.name]

        random.shuffle(server_quotes)
        quote = server_quotes.pop(random.randrange(len(server_quotes)))
        tstamp = self._get_tstamp(quote["timestamp"])

        msg = f"{quote['nick']} @ {tstamp}: \"{quote['msg']}\""
        self.channel.send_query(f"{c.INFO} {msg}")
