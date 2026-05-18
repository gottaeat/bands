import datetime

from bands.colors import MIRCColors

c = MIRCColors()


class Quote:
    def __init__(self, channel, user, user_args):
        self.channel = channel
        self.user = user
        self.user_args = user_args

        self.logger = self.channel.logger.getChild(self.__class__.__name__)
        self.db = self.channel.server.config.db

        self._run()

    def _cmd_help(self):
        self.channel.send_query(
            f"{c.WHITE}├ {c.LGREEN}add{c.RES}    [nick] [quoted message]\n"
            f"{c.WHITE}├ {c.LGREEN}get{c.RES}    [nick]\n"
            f"{c.WHITE}└ {c.LGREEN}random{c.RES}"
        )

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

        self.db.add_quote(
            self.channel.server.name,
            self.channel.name,
            user.nick,
            chat_line["chat"],
            chat_line["tstamp"],
        )

        self.channel.send_query(f"{c.INFO} quote added.")

    def _cmd_get(self):
        # no nick
        try:
            quoted_user = self.user_args[1]
        except IndexError:
            return self.channel.send_query(f"{c.ERR} must provide a nick.")

        quote = self.db.random_quote(
            self.channel.server.name,
            self.channel.name,
            quoted_user,
        )

        if not quote:
            return self.channel.send_query(
                f"{c.ERR} {quoted_user} has no recorded quotes in "
                f"{self.channel.name}."
            )

        # user does exist
        nick, quoted_msg, timestamp = quote
        tstamp = datetime.datetime.utcfromtimestamp(int(timestamp))

        msg = f'{nick} @ {tstamp} UTC: "{quoted_msg}"'
        self.channel.send_query(f"{c.INFO} {msg}")

    def _cmd_random(self):
        quote = self.db.random_quote(self.channel.server.name, self.channel.name)

        if not quote:
            return self.channel.send_query(
                f"{c.ERR} {self.channel.name} does not have " "anyone quoted."
            )

        nick, quoted_msg, timestamp = quote
        tstamp = datetime.datetime.utcfromtimestamp(int(timestamp))

        msg = f'{nick} @ {tstamp} UTC: "{quoted_msg}"'
        self.channel.send_query(f"{c.INFO} {msg}")
