import time

from bands.colors import MIRCColors
from bands.irc.util import unilen

c = MIRCColors()


class Point:
    def __init__(self, channel, user, user_args):
        self.channel = channel
        self.user = user
        self.user_args = user_args

        self.db = self.channel.server.config.db

        self._run()

    def _cmd_help(self):
        self.channel.send_query(
            f"{c.WHITE}├ {c.LGREEN}up{c.RES}   [nick]\n"
            f"{c.WHITE}├ {c.LGREEN}down{c.RES} [nick]\n"
            f"{c.WHITE}├ {c.LGREEN}get{c.RES}  [nick]\n"
            f"{c.WHITE}└ {c.LGREEN}stats{c.RES}"
        )

    def _run(self):
        if not self.user_args:
            return self._cmd_help()

        cmd = self.user_args[0]

        if cmd in ("up", "down"):
            return self._cmd_point(cmd)

        if cmd in ("get", "stats"):
            return getattr(self, f"_cmd_{cmd}")()

        self._cmd_help()

    def _cmd_point(self, action):
        # a user can invoke point every 10 seconds
        if (
            self.user.used_point_tstamp
            and int(time.strftime("%s")) - self.user.used_point_tstamp <= 10
        ):
            return

        # no nick
        try:
            pointed_user = self.user_args[1]
        except IndexError:
            return self.channel.send_query(f"{c.ERR} must provide a nick.")

        # get ChannelUser
        try:
            user = self.channel.users[pointed_user.lower()]
        except KeyError:
            return self.channel.send_query(f"{c.ERR} no such nick: {pointed_user}.")

        # self point
        if user == self.user:
            return self.channel.send_query(f"{c.ERR} cannot point yourself.")

        # a user can be pointed every 30 seconds
        if (
            user.got_pointed_tstamp
            and int(time.strftime("%s")) - user.got_pointed_tstamp <= 30
        ):
            return

        # alter points
        point_amount = 1 if action == "up" else -1
        user_points = self.db.alter_point(
            self.channel.server.name,
            user.nick,
            point_amount,
        )

        # update timestamps on successful point
        self.user.used_point_tstamp = int(time.strftime("%s"))
        user.got_pointed_tstamp = int(time.strftime("%s"))

        self.channel.send_query(
            f"{c.INFO} {c.LGREEN}{self.user.nick} {c.WHITE}pointed {action} "
            f"{c.ORANGE}{user.nick}{c.RES} "
            f"(this user now has {c.WHITE}{user_points}{c.RES} "
            "internet relay points!!!)"
        )

    def _cmd_get(self):
        # no nick
        try:
            pointed_user = self.user_args[1]
        except IndexError:
            return self.channel.send_query(f"{c.ERR} must provide a nick.")

        point_entry = self.db.get_point(self.channel.server.name, pointed_user)

        # user does not exist
        if not point_entry:
            return self.channel.send_query(
                f"{c.ERR} {pointed_user} has never been pointed in "
                f"{self.channel.server.name}."
            )

        # user exists
        nick, user_points = point_entry

        self.channel.send_query(
            f"{c.INFO} {c.LGREEN}{nick}{c.RES} has "
            f"{c.WHITE}{user_points}{c.RES} internet relay points in "
            f"{self.channel.server.name}!!1! fuck !"
        )

    def _cmd_stats(self):
        top_five = self.db.top_points(self.channel.server.name)

        # entry for server does not exist
        if not top_five:
            return self.channel.send_query(
                f"{c.ERR} {self.channel.server.name} does not have " "anyone pointed."
            )

        msg = f"{c.INFO} {self.channel.server.name} hall of fame:\n"

        # calculate width
        max_len = 0
        for point_entry in top_five:
            max_len = max(max_len, unilen(point_entry[0]))

        # gen prompt
        index = 1
        for point_entry in top_five:
            nick, points = point_entry
            msg += f"{c.LRED}#{index} {c.WHITE}{nick :<{max_len}} {c.LGREEN}{points}\n"
            index += 1

        self.channel.send_query(msg)
