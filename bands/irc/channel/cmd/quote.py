import datetime
import random

from bands.colors import MIRCColors

c = MIRCColors()


class Quote:
    def __init__(self, channel, user, user_args):
        self.channel = channel
        self.user = user
        self.user_args = user_args

        self.logger = self.channel.logger.getChild(self.__class__.__name__)
        self.quote = self.channel.server.config.quote

        self._run()

    def _cmd_help(self):
        msg = f"{c.WHITE}├ {c.LGREEN}add{c.RES}    [nick] [quoted message]\n"
        msg += f"{c.WHITE}├ {c.LGREEN}get{c.RES}    [nick]\n"
        msg += f"{c.WHITE}└ {c.LGREEN}random{c.RES}"

        self.channel.send_query(msg)

    def _run(self):
        if len(self.user_args) == 0:
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
        for user_chat in user.chats:
            if user_chat["chat"] == quoted_msg:
                chat_line = user_chat
                break

        try:
            if chat_line:
                pass
        except UnboundLocalError:
            self.channel.send_query(f"{c.ERR} {user.nick} never said that.")
            return

        # gen quote
        quote = {
            "timestamp": chat_line["tstamp"],
            "nick": user.nick,
            "msg": chat_line["chat"],
        }

        # update jayson
        with self.quote.mutex:
            quotes = self.quote.read_quotes()

            # entry for server does not exist
            if self.channel.server.name not in quotes["quotes"][0].keys():
                quotes["quotes"][0][self.channel.server.name] = [{}]

                self.logger.info(
                    "created quote entry for: %s", self.channel.server.name
                )

            # entry for channel does not exist
            if (
                self.channel.name
                not in quotes["quotes"][0][self.channel.server.name][0].keys()
            ):
                quotes["quotes"][0][self.channel.server.name][0][self.channel.name] = []

                self.logger.info(
                    "created quote entry for %s in %s",
                    self.channel.name,
                    self.channel.server.name,
                )

            # update and write quotes
            quotes["quotes"][0][self.channel.server.name][0][self.channel.name].append(
                quote
            )

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

        # entry for channel does not exist
        if (
            self.channel.name
            not in quotes["quotes"][0][self.channel.server.name][0].keys()
        ):
            err_msg = f"{c.ERR} {self.channel.name} does not have "
            err_msg += "anyone quoted."
            self.channel.send_query(err_msg)
            return

        # find user entries
        users_quotes = []
        for item in quotes["quotes"][0][self.channel.server.name][0][self.channel.name]:
            if item["nick"].lower() == quoted_user.lower():
                users_quotes.append(item)

        # user does not exist
        if len(users_quotes) == 0:
            err_msg = f"{c.ERR} {quoted_user} has no recorded quotes in "
            err_msg += f"{self.channel.name}."
            self.channel.send_query(err_msg)

            return

        # user does exist
        random.shuffle(users_quotes)
        quote = users_quotes.pop(random.randrange(len(users_quotes)))
        tstamp = datetime.datetime.utcfromtimestamp(int(quote["timestamp"]))

        msg = f"{quote['nick']} @ {tstamp} UTC: \"{quote['msg']}\""
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

        # entry for channel does not exist
        if (
            self.channel.name
            not in quotes["quotes"][0][self.channel.server.name][0].keys()
        ):
            err_msg = f"{c.ERR} {self.channel.name} does not have "
            err_msg += "anyone quoted."
            self.channel.send_query(err_msg)
            return

        # get channel entries
        channel_quotes = quotes["quotes"][0][self.channel.server.name][0][
            self.channel.name
        ]

        random.shuffle(channel_quotes)
        quote = channel_quotes.pop(random.randrange(len(channel_quotes)))
        tstamp = datetime.datetime.utcfromtimestamp(int(quote["timestamp"]))

        msg = f"{quote['nick']} @ {tstamp} UTC: \"{quote['msg']}\""
        self.channel.send_query(f"{c.INFO} {msg}")
