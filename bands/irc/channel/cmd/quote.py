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
        if not self.user_args:
            return self._cmd_help()

        cmd = self.user_args[0]

        if cmd in ("add", "get", "random"):
            return getattr(self, f"_cmd_{cmd}")()

        self._cmd_help()

    def _cmd_add(self):
        # no nick
        try:
            quoted_user = self.user_args[1]
        except IndexError:
            return self.channel.send_query(f"{c.ERR} must provide a nick.")

        # get ChannelUser
        try:
            user = self.channel.users[quoted_user.lower()]
        except KeyError:
            return self.channel.send_query(f"{c.ERR} no such nick: {quoted_user}.")

        # list to str
        quoted_msg = " ".join(self.user_args[2:])

        # no quote
        if not quoted_msg:
            return self.channel.send_query(f"{c.ERR} no quote body.")

        # self quote
        if user == self.user:
            return self.channel.send_query(f"{c.ERR} cannot quote yourself.")

        # check if said
        chat_line = None
        for user_chat in user.chats:
            if user_chat["chat"] == quoted_msg:
                chat_line = user_chat
                break

        if not chat_line:
            return self.channel.send_query(f"{c.ERR} {user.nick} never said that.")

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
                self.channel.server.logger.info("created quotes entry for the server")

            # entry for channel does not exist
            if (
                self.channel.name
                not in quotes["quotes"][0][self.channel.server.name][0].keys()
            ):
                quotes["quotes"][0][self.channel.server.name][0][self.channel.name] = []
                self.logger.info("created quotes entry for the channel")

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
            return self.channel.send_query(f"{c.ERR} must provide a nick.")

        # read jayson
        with self.quote.mutex:
            quotes = self.quote.read_quotes()

        # entry for server does not exist
        if self.channel.server.name not in quotes["quotes"][0].keys():
            err_msg = f"{c.ERR} {self.channel.server.name} does not have "
            err_msg += "anyone quoted."
            return self.channel.send_query(err_msg)

        # entry for channel does not exist
        if (
            self.channel.name
            not in quotes["quotes"][0][self.channel.server.name][0].keys()
        ):
            err_msg = f"{c.ERR} {self.channel.name} does not have anyone quoted"
            return self.channel.send_query(err_msg)

        # find user entries
        users_quotes = []
        for item in quotes["quotes"][0][self.channel.server.name][0][self.channel.name]:
            if item["nick"].lower() == quoted_user.lower():
                users_quotes.append(item)

        # user does not exist
        if not users_quotes:
            err_msg = f"{c.ERR} {quoted_user} has no recorded quotes in "
            err_msg += f"{self.channel.name}."
            return self.channel.send_query(err_msg)

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
            return self.channel.send_query(err_msg)

        # entry for channel does not exist
        if (
            self.channel.name
            not in quotes["quotes"][0][self.channel.server.name][0].keys()
        ):
            err_msg = f"{c.ERR} {self.channel.name} does not have "
            err_msg += "anyone quoted."
            return self.channel.send_query(err_msg)

        # get channel entries
        channel_quotes = quotes["quotes"][0][self.channel.server.name][0][
            self.channel.name
        ]

        random.shuffle(channel_quotes)
        quote = channel_quotes.pop(random.randrange(len(channel_quotes)))
        tstamp = datetime.datetime.utcfromtimestamp(int(quote["timestamp"]))

        msg = f"{quote['nick']} @ {tstamp} UTC: \"{quote['msg']}\""
        self.channel.send_query(f"{c.INFO} {msg}")
