import time

from bands.colors import MIRCColors
from bands.irc.util import unilen

# pylint: disable=invalid-name
c = MIRCColors()


# pylint: disable=too-few-public-methods
class Doot:
    def __init__(self, channel, user, user_args):
        self.channel = channel
        self.user = user
        self.user_args = user_args

        self.doot = self.channel.server.doot

        self._run()

    def _cmd_help(self):
        msg = f"{c.LRED}usage{c.RES}\n"
        msg += f"{c.WHITE}├ {c.LGREEN}up{c.RES}   [target]\n"
        msg += f"{c.WHITE}├ {c.LGREEN}down{c.RES} [target]\n"
        msg += f"{c.WHITE}├ {c.LGREEN}get{c.RES}  [target]\n"
        msg += f"{c.WHITE}├ {c.LGREEN}stats{c.RES}\n"
        msg += f"{c.WHITE}└ {c.LGREEN}help {c.RES}"

        self.channel.send_query(msg)

    def _run(self):
        if len(self.user_args) == 0 or self.user_args[0] == "help":
            self._cmd_help()
            return

        if self.user_args[0] == "up":
            self._alter_doot("up")
            return

        if self.user_args[0] == "down":
            self._alter_doot("down")
            return

        if self.user_args[0] == "get":
            self._cmd_get()
            return

        if self.user_args[0] == "stats":
            self._cmd_stats()
            return

        self._cmd_help()

    # pylint: disable=too-many-branches
    def _alter_doot(self, action):
        # dirty prevent spam
        if self.user.doot_tstamp:
            if int(time.strftime("%s")) - self.user.doot_tstamp <= 10:
                return

        # no nick
        try:
            dooted_user = self.user_args[1]
        except IndexError:
            self.channel.send_query(f"{c.ERR} must provide a nick.")
            return

        # get ChannelUser
        for channeluser in self.channel.user_list:
            if channeluser.nick.lower() == dooted_user.lower():
                user = channeluser
                break

        # self doot || no ChannelUser obj
        try:
            if user.nick == self.user.nick and user.login == self.user.login:
                self.channel.send_query(f"{c.ERR} cannot doot yourself.")
                return
        except UnboundLocalError:
            self.channel.send_query(f"{c.ERR} no such nick: {dooted_user}.")
            return

        self.user.doot_tstamp = int(time.strftime("%s"))

        # update jayson
        with self.doot.mutex:
            doots = self.doot.read_doots()

            # entry for server does not exist
            if self.channel.server.name not in doots["doots"][0].keys():
                doots["doots"][0][self.channel.server.name] = []

                self.channel.server.logger.info(
                    "created doot entry for: %s", self.channel.server.name
                )

            # find user entry
            user_exists = (False, None)
            for index, doot_user_entry in enumerate(
                doots["doots"][0][self.channel.server.name]
            ):
                if doot_user_entry["nick"].lower() == user.nick.lower():
                    user_exists = (True, index)
                    break

            # user does not exist, initialize it
            if not user_exists[0]:
                if action == "up":
                    dooted_user_dict = {"nick": user.nick, "doots": 1}
                if action == "down":
                    dooted_user_dict = {"nick": user.nick, "doots": -1}

                doots["doots"][0][self.channel.server.name].append(dooted_user_dict)
            # user exists
            else:
                if action == "up":
                    doots["doots"][0][self.channel.server.name][user_exists[1]][
                        "doots"
                    ] += 1
                if action == "down":
                    doots["doots"][0][self.channel.server.name][user_exists[1]][
                        "doots"
                    ] -= 1

            self.doot.write_doots(doots)

        # prompt
        if user_exists[0]:
            user_doots = doots["doots"][0][self.channel.server.name][user_exists[1]][
                "doots"
            ]
        else:
            user_doots = dooted_user_dict["doots"]

        msg = f"{c.INFO} {c.LGREEN}{self.user.nick} {c.WHITE}{action}dooted "
        msg += f"{c.ORANGE}{user.nick}{c.RES} "
        msg += f"(this user now has {c.WHITE}{user_doots}{c.RES} "
        msg += "internet relay points!!!)"

        self.channel.send_query(msg)

    def _cmd_get(self):
        # no nick
        try:
            dooted_user = self.user_args[1]
        except IndexError:
            self.channel.send_query(f"{c.ERR} must provide a nick.")
            return

        # get ChannelUser
        for channeluser in self.channel.user_list:
            if channeluser.nick.lower() == dooted_user.lower():
                user = channeluser
                break

        # no ChannelUser obj
        try:
            if user:
                pass
        except UnboundLocalError:
            self.channel.send_query(f"{c.ERR} no such nick: {dooted_user}.")
            return

        # read jayson
        with self.doot.mutex:
            doots = self.doot.read_doots()

        # entry for server does not exist
        if self.channel.server.name not in doots["doots"][0].keys():
            err_msg = f"{c.ERR} {self.channel.server.name} does not have "
            err_msg += "anyone dooted."
            self.channel.send_query(err_msg)
            return

        # find user entry
        user_exists = (False, None)
        for index, doot_user_entry in enumerate(
            doots["doots"][0][self.channel.server.name]
        ):
            if doot_user_entry["nick"].lower() == user.nick.lower():
                user_exists = (True, index)
                break

        # user does not exist
        if not user_exists[0]:
            err_msg = f"{c.ERR} {user.nick} has never been dooted in "
            err_msg += f"{self.channel.server.name}."
            self.channel.send_query(err_msg)
        # user exists
        else:
            user_doots = doots["doots"][0][self.channel.server.name][user_exists[1]][
                "doots"
            ]

            msg = f"{c.INFO} {c.LGREEN}{user.nick}{c.RES} has "
            msg += f"{c.WHITE}{user_doots}{c.RES} internet points in "
            msg += f"{self.channel.server.name}!!1! fuck !"
            self.channel.send_query(msg)

    def _cmd_stats(self):
        # read jayson
        with self.doot.mutex:
            doots = self.doot.read_doots()

        # entry for server does not exist
        if self.channel.server.name not in doots["doots"][0].keys():
            err_msg = f"{c.ERR} {self.channel.server.name} does not have "
            err_msg += "anyone dooted."
            self.channel.send_query(err_msg)
            return

        msg = f"{c.INFO} {self.channel.server.name} hall of fame:\n"

        # top 5
        top_five = sorted(
            doots["doots"][0][self.channel.server.name],
            key=lambda x: x["doots"],
            reverse=True,
        )[:5]

        # calculate width
        max_len = 0

        for doot_entry in top_five:
            itemlen = unilen(doot_entry["nick"])

            if itemlen > max_len:
                max_len = itemlen

        # gen prompt
        index = 1
        for doot_entry in top_five:
            msg += f"{c.LRED}#{index} "
            msg += f"{c.WHITE}{doot_entry['nick'] :<{max_len}} {c.LGREEN}{doot_entry['doots']}\n"
            index += 1

        self.channel.send_query(msg)
