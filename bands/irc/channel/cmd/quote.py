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

    def _cmd_help(self):
        msg = f"{c.LRED}usage{c.RES}\n"
        msg += f"{c.WHITE}├ {c.LGREEN}add{c.RES}    [target] [quoted message]\n"
        msg += f"{c.WHITE}├ {c.LGREEN}user{c.RES}   [target]\n"
        msg += f"{c.WHITE}├ {c.LGREEN}random{c.RES}\n"
        msg += f"{c.WHITE}└ {c.LGREEN}help{c.RES}"

        self.channel.send_query(msg)

    def _cmd_random(self):
        with self.quote.mutex:
            quotes = self.quote.read_quotes()["quotes"]

        if len(quotes) == 0:
            self.channel.send_query(f"{c.ERR} no quotes on record.")
            return

        random.shuffle(quotes)
        quote = quotes.pop(random.randrange(len(quotes)))

        tstamp = datetime.datetime.fromtimestamp(int(quote["timestamp"])).strftime(
            "%Y/%m/%d %T"
        )

        msg = f"{quote['quoted_user_nick']} ({quote['quoted_user_login']}): \""
        msg += f"{quote['quoted_msg']}\" @ {tstamp} "
        msg += f"[{quote['added_by_nick']} ({quote['added_by_login']})]"

        self.channel.send_query(f"{c.INFO} {msg}")

    def _cmd_user(self):
        # no nick
        try:
            get_user = self.user_args[1]
        except IndexError:
            self.channel.send_query(f"{c.ERR} must provide a nick.")
            return

        with self.quote.mutex:
            quotes = self.quote.read_quotes()["quotes"]

        users_quotes = []
        for item in quotes:
            if get_user == item["quoted_user_nick"]:
                users_quotes.append(item)

        if len(users_quotes) == 0:
            self.channel.send_query(f"{c.ERR} {get_user} has no recorded quotes.")
            return

        random.shuffle(users_quotes)
        quote = users_quotes.pop(random.randrange(len(users_quotes)))
        tstamp = datetime.datetime.fromtimestamp(int(quote["timestamp"])).strftime(
            "%Y/%m/%d %T"
        )

        msg = f"{quote['quoted_user_nick']} ({quote['quoted_user_login']}): \""
        msg += f"{quote['quoted_msg']}\" @ {tstamp} "
        msg += f"[{quote['added_by_nick']} ({quote['added_by_login']})]"

        self.channel.send_query(f"{c.INFO} {msg}")

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
            if channeluser.nick == quoted_user:
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

        # compose jayson
        quote = {
            "timestamp": time.strftime("%s"),
            "quoted_user_nick": user.nick,
            "quoted_user_login": user.login,
            "quoted_msg": quoted_msg,
            "channel": self.channel.name,
            "server": self.channel.server.name,
            "added_by_nick": self.user.nick,
            "added_by_login": self.user.login,
        }

        with self.quote.mutex:
            quotes = self.quote.read_quotes()
            quotes["quotes"].append(quote)
            self.quote.write_quotes(quotes)

        self.channel.send_query(f"{c.INFO} quote added.")

    def _run(self):
        if len(self.user_args) == 0 or self.user_args[0] == "help":
            self._cmd_help()
            return

        if self.user_args[0] == "add":
            self._cmd_add()
            return

        if self.user_args[0] == "user":
            self._cmd_user()
            return

        if self.user_args[0] == "random":
            self._cmd_random()
            return

        self._cmd_help()
