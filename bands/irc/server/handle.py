import datetime
import re
import time

import bands.irc.channel.cmd as ChanCMD
import bands.irc.user.cmd as UserCMD

from bands.colors import ANSIColors
from bands.irc.util import chop_userline, streamline_modes

from bands.irc.user import User
from bands.irc.channel import Channel, ChannelUser

ac = ANSIColors()


class Handle:
    def __init__(self, server):
        self.server = server
        self.logger = server.logger
        self.sock_ops = server.sock_ops

        # user and channels
        self.channels = server.channels
        self.channel_obj = server.channel_obj
        self.users = server.users

    # -- object generators begin -- #
    def _gen_channel(self, channel_name):
        # if channel already exists, return its object
        for channel in self.channel_obj:
            if channel.name == channel_name:
                return channel

        # if not, gen and return it
        channel = Channel(self.server)
        channel.name = channel_name

        self.channel_obj.append(channel)
        self.channels.append(channel.name)

        self.logger.debug("generated Channel: %s", channel.name)

        return channel

    def _gen_user(self, user_nick, user_login):
        # if user alread exists, return the corresponding user object
        for user in self.users:
            if user.nick == user_nick and user.login == user_login:
                return user

        # if user does not exist, create it
        user = User(self.server)
        user.nick = user_nick
        user.login = user_login
        user.char_limit = 512 - len(f"PRIVMSG {user.nick} :".encode("utf-8"))

        self.users.append(user)

        self.logger.debug(
            "generated User: %s (%s) [%s]",
            user.nick,
            user.login,
            user.char_limit,
        )

        # return the created user obj
        return user

    # -- object generators end -- #

    # -- channel events begin -- #
    def channel_msg(self, channel_name, user_line, msg):
        user_nick = chop_userline(user_line)["nick"]

        # get channel object
        for chan in self.channel_obj:
            if chan.name == channel_name:
                channel = chan
                break

        # get channeluser object
        for channeluser in channel.user_list:
            if channeluser.nick == user_nick:
                user = channeluser
                break

        # add msg to chats of user
        if len(user.chats) >= 10:
            user.chats = user.chats[1:]

        user.chats.append(
            {
                "tstamp": int(time.strftime("%s")),
                "chat": re.sub("^:", "", " ".join(msg)),
            }
        )

        # cmd handling
        if msg[0] not in ChanCMD.CMDS:
            return

        cmd = msg[0]
        user_args = msg[1:]

        # print cmd invocation
        self.logger.info(
            "%s%s%s %s %s",
            f"{ac.BMGN}[{ac.BWHI}{user.nick} ({user.login})",
            f"{ac.BRED}¦",
            f"{ac.BGRN}{channel.name}{ac.BMGN}]",
            f"{ac.BCYN}{cmd}",
            f"{' '.join(user_args)}{ac.RES}",
        )

        # set tstamp
        tstamp = int(time.strftime("%s"))

        # if this is channel init
        if not channel.tstamp:
            channel.tstamp = tstamp

            ChanCMD.CMDS[cmd](channel, user, user_args)

            return

        # see if a User exists for the ChannelUser
        for serveruser in self.users:
            if serveruser.nick == user.nick and serveruser.login == user.login:
                corresp_user = serveruser

        # ratelimit if not authed user
        ratelimit = True

        try:
            if corresp_user == self.server.admin:
                ratelimit = False
        except UnboundLocalError:
            pass

        if ratelimit and tstamp - channel.tstamp < 2:
            self.logger.debug("ignoring cmd %s in %s (ratelimited)", cmd, channel.name)

            return

        # update tstamp
        channel.tstamp = tstamp

        # exec
        ChanCMD.CMDS[cmd](channel, user, user_args)

    def bot_invite(self, user_line, channel_name):
        user_line = chop_userline(user_line)
        user_nick = user_line["nick"]
        user_login = user_line["login"]

        self.logger.info(
            "%s (%s) has invited us to %s", user_nick, user_login, channel_name
        )

        #        if not self.server.admin:
        #            self.logger.warning("no admin user for %s, not joining", self.server.name)
        #            return
        #
        #        if (
        #            user_nick != self.server.admin.user
        #            and user_login != self.server.admin.login
        #        ):
        #            self.logger.warning(
        #                "%s is not the admin for %s, not joining", user_nick, self.server.name
        #            )
        #            return
        #
        #        self.logger.warning("%s is the admin user, joining", user_nick)
        #        self.sock_ops.send_join(channel_name)

    def bot_ban(self, channel_name):
        if channel_name in self.channels:
            self.channels.remove(channel_name)

        for chan in self.channel_obj:
            if chan.name == channel_name:
                self.channel_obj.remove(chan)

        self.logger.info("we are banned from %s, removing from lists", channel_name)

        if len(self.channels) == 0:
            self.logger.info("channels list is empty, quitting")
            self.sock_ops.connected = False
            self.server.stop()

    def initial_topic_msg(self, channel_name, msg):
        for chan in self.channel_obj:
            if chan.name == channel_name:
                channel = chan
                break

        try:
            topic_msg = " ".join(msg).lstrip(":")
        except:
            self.logger.warning("setting the topic for %s failed", channel_name)
            return

        channel.topic_msg = topic_msg

        self.logger.info("topic for %s: %s", channel.name, channel.topic_msg)

    def initial_topic_meta(self, channel_name, user_line, tstamp):
        for chan in self.channel_obj:
            if chan.name == channel_name:
                channel = chan
                break

        try:
            topic_tstamp = datetime.datetime.fromtimestamp(int(tstamp)).strftime(
                "%Y/%m/%d %T"
            )
        except:
            self.logger.warning(
                "setting the topic timestamp for %s failed", channel_name
            )
            return

        user_line = chop_userline(user_line)

        channel.topic_nick = user_line["nick"]
        channel.topic_login = user_line["login"]
        channel.topic_tstamp = topic_tstamp

        self.logger.info(
            "topic for %s set by %s (%s) at %s",
            channel.name,
            channel.topic_nick,
            channel.topic_login,
            channel.topic_tstamp,
        )

    def topic(self, channel_name, user_line, msg):
        for chan in self.channel_obj:
            if chan.name == channel_name:
                channel = chan
                break

        try:
            topic_msg = " ".join(msg).lstrip(":")
        except:
            self.logger.warning("updating the topic for %s failed", channel_name)
            return

        user_line = chop_userline(user_line)

        channel.topic_msg = topic_msg
        channel.topic_nick = user_line["nick"]
        channel.topic_login = user_line["login"]
        channel.topic_tstamp = time.strftime("%Y/%m/%d %T")

        self.logger.info(
            "topic for %s updated by %s (%s) to: %s",
            channel.name,
            channel.topic_nick,
            channel.topic_login,
            channel.topic_msg,
        )

    def who(self, channel_name, user_nick, user_ircname, user_hostname, user_props):
        self.logger.debug("parsing WHO for %s", channel_name)

        # get channel obj
        for chan in self.channel_obj:
            if chan.name == channel_name:
                channel = chan
                break

        # gen user
        user = ChannelUser()
        user.nick = user_nick
        user.login = f"{user_ircname}@{user_hostname}"

        user.owner = "~" in user_props
        user.admin = "&" in user_props
        user.op = "@" in user_props
        user.hop = "%" in user_props
        user.voiced = "+" in user_props

        # append
        channel.user_list.append(user)

    # -- channel events end -- #

    # -- user events begin -- #
    def user_msg(self, user_line, cmd, user_args):
        user_line = chop_userline(user_line)
        user_nick = user_line["nick"]
        user_login = user_line["login"]

        user = self._gen_user(user_nick, user_login)

        self.logger.info(
            "%s%s%s %s %s",
            f"{ac.BMGN}[{ac.BWHI}{user.nick} ({user.login})",
            f"{ac.BRED}¦",
            f"{ac.BGRN}PM{ac.BMGN}]",
            f"{ac.BCYN}{cmd}",
            f"{' '.join(user_args)}{ac.RES}",
        )

        tstamp = int(time.strftime("%s"))

        if not user.tstamp:
            user.tstamp = tstamp

            UserCMD.CMDS[cmd](user, user_args)

            return

        if user != self.server.admin:
            if tstamp - user.tstamp < 2:
                self.logger.debug("ignoring cmd %s in %s (ratelimited)", cmd, user.nick)

                return

        user.tstamp = tstamp

        UserCMD.CMDS[cmd](user, user_args)

    def mode(self, user_line, channel_name, modes, user_nicks):
        try:
            user_line = chop_userline(user_line)
            user_nick = user_line["nick"]
            user_login = user_line["login"]
        except IndexError:
            user_nick = "server"
            user_login = self.server.socket.address

        for chan in self.channel_obj:
            if chan.name == channel_name:
                channel = chan
                break

        mode_data = streamline_modes(modes, user_nicks)
        for mode_user, mode_info in mode_data.items():
            for user_obj in channel.user_list:
                if user_obj.nick == mode_user:
                    if mode_info["mode"] == "v":
                        user_obj.voiced = mode_info["action"]

                    if mode_info["mode"] == "h":
                        user_obj.hop = mode_info["action"]

                    if mode_info["mode"] == "o":
                        user_obj.op = mode_info["action"]

                    if mode_info["mode"] == "a":
                        user_obj.admin = mode_info["action"]

                    if mode_info["mode"] == "q":
                        user_obj.owner = mode_info["action"]

                    self.logger.debug(
                        "[%s] mode %s -> %s for %s (%s) by %s (%s)",
                        channel.name,
                        mode_info["mode"],
                        mode_info["action"],
                        user_obj.nick,
                        user_obj.login,
                        user_nick,
                        user_login,
                    )

    def nick(self, user_line, user_new_nick):
        user_line = chop_userline(user_line)
        user_old_nick = user_line["nick"]
        user_login = user_line["login"]

        # 0. bot
        if user_old_nick == self.server.botname:
            self.server.botname = user_new_nick
            self.logger.info("changed the bot name to %s", user_new_nick)

        # 1. channeluser obj
        for channel in self.channel_obj:
            for channeluser in channel.user_list:
                if (
                    channeluser.nick == user_old_nick
                    and channeluser.login == user_login
                ):
                    self.logger.debug(
                        "updating %s (%s)'s nick to %s in %s",
                        channeluser.nick,
                        channeluser.login,
                        user_new_nick,
                        channel.name,
                    )

                    channeluser.nick = user_new_nick

        # 2. user obj
        for user_obj in self.users:
            if user_obj.nick == user_old_nick and user_obj.login == user_login:
                user = user_obj
                break

        try:
            if user:
                self.logger.debug(
                    "%s (%s) changed their nick to %s, updating the user object",
                    user.nick,
                    user.login,
                    user_new_nick,
                )

                user.nick = user_new_nick
        except UnboundLocalError:
            pass

    def chghost(self, user_line, user_new_ircname, user_new_hostname):
        user_line = chop_userline(user_line)
        user_nick = user_line["nick"]

        user_old_login = user_line["login"]
        user_new_login = f"{user_new_ircname}@{user_new_hostname}"

        # 1. channeluser obj
        for channel in self.channel_obj:
            for channeluser in channel.user_list:
                if (
                    channeluser.nick == user_nick
                    and channeluser.login == user_old_login
                ):
                    self.logger.debug(
                        "%s (%s) changed host to %s, updating their object for %s",
                        channeluser.nick,
                        channeluser.login,
                        user_new_login,
                        channel.name,
                    )

                    channeluser.login = user_new_login

        # 2. user obj
        for user_obj in self.users:
            if user_obj.nick == user_nick and user_obj.login == user_old_login:
                user = user_obj
                break

        try:
            if user:
                self.logger.debug(
                    "%s (%s) changed host to %s, updating the user object",
                    user.nick,
                    user.login,
                    user_new_login,
                )

                user.login = user_new_login
        except UnboundLocalError:
            pass

    def join(self, user_line, channel_name):
        # some ircd's send channel name w/ a :
        channel_name = re.sub(r"^:", "", channel_name)

        user_line_chop = chop_userline(user_line)
        user_nick = user_line_chop["nick"]
        user_login = user_line_chop["login"]

        # bot join
        if user_nick == self.server.botname:
            channel = self._gen_channel(channel_name)

            if not channel.char_limit:
                channel.char_limit = 512 - len(
                    f"{user_line} PRIVMSG {channel.name} :\r\n".encode("utf-8")
                )

                self.logger.debug(
                    "char_limit for %s is set to %s", channel.name, channel.char_limit
                )

            self.sock_ops.send_raw(f"WHO {channel.name}")
            self.logger.debug("sent WHO for %s", channel.name)

            return

        # user join
        for chan in self.channel_obj:
            if chan.name == channel_name:
                channel = chan
                break

        user = ChannelUser()
        user.nick = user_nick
        user.login = user_login

        channel.user_list.append(user)

        self.logger.debug("user %s (%s) joined %s", user.nick, user.login, channel.name)

    def part(self, user_line, channel_name, msg):
        user_line = chop_userline(user_line)
        user_nick = user_line["nick"]

        # bot part
        if user_nick == self.server.botname:
            # get corresponding channel object
            for channel_obj in self.channel_obj:
                if channel_obj.name == channel_name:
                    channel = channel_obj
                    break

            # check whether we recognize channel
            try:
                if channel:
                    pass
            except NameError:
                errmsg = "bot PART'ed but corresponding channel object was not "
                errmsg += "found.\nbot state is questionable."
                self.logger.warning(errmsg)
                return

            if channel_name not in self.channels:
                errmsg = "bot PART'ed but the channel it left does not exist "
                errmsg += "channels list.\n bot state is questionable."
                self.logger.warning(errmsg)
                return

            # nuke
            self.channels.remove(channel.name)
            self.channel_obj.remove(channel)
            self.logger.info("left and nuked %s in %s", channel_name, self.server.name)

            return

        # user part
        user_login = user_line["login"]
        reason = " ".join(msg).lstrip(":")

        # get channel object
        for chan in self.channel_obj:
            if chan.name == channel_name:
                channel = chan
                break

        # get channeluser object
        for channeluser in channel.user_list:
            if channeluser.nick == user_nick and channeluser.login == user_login:
                user = channeluser
                break

        channel.user_list.remove(user)

        self.logger.debug(
            "removed %s (%s) from %s, user left (%s)",
            user.nick,
            user.login,
            channel.name,
            reason,
        )

    def kick(self, user_line, channel_name, kicked_user, reason):
        user_line = chop_userline(user_line)
        user_nick = user_line["nick"]
        user_login = user_line["login"]

        for chan in self.channel_obj:
            if chan.name == channel_name:
                channel = chan
                break

        # bot kicked
        if kicked_user == self.server.botname:
            self.logger.warning(
                "%s (%s) has kicked us from %s (%s)",
                user_nick,
                user_login,
                channel.name,
                reason,
            )

            self.channels.remove(channel.name)
            self.channel_obj.remove(channel)

            self.sock_ops.send_join(channel_name)

            return

        # user kicked
        for channeluser in channel.user_list:
            if channeluser.nick == kicked_user:
                user = channeluser
                break

        channel.user_list.remove(user)

        self.logger.debug(
            "%s (%s) has kicked %s (%s) from %s (%s)",
            user_nick,
            user_login,
            user.nick,
            user.login,
            channel.name,
            reason,
        )

    def quit(self, user_line, msg):
        user_line = chop_userline(user_line)
        user_nick = user_line["nick"]
        user_login = user_line["login"]

        reason = " ".join(msg).lstrip(":")

        # remove from Channel().user_list's
        for channel in self.channel_obj:
            for channeluser in channel.user_list:
                if channeluser.nick == user_nick and channeluser.login == user_login:
                    channel.user_list.remove(channeluser)

                    self.logger.debug(
                        "removed %s (%s) from %s, user quit (%s)",
                        channeluser.nick,
                        channeluser.login,
                        channel.name,
                        reason,
                    )

        # remove from Server().users
        for user in self.users:
            if user.nick == user_nick and user.login == user_login:
                self.users.remove(user)

                self.logger.debug(
                    "removed %s (%s) from global users, user quit (%s)",
                    user.nick,
                    user.login,
                    reason,
                )

    # -- user events end -- #
