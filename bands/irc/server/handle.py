import datetime
import re
import time

import bands.irc.channel.cmd as ChanCMD
import bands.irc.user.cmd as UserCMD

from bands.colors import ANSIColors
from bands.irc.util import chop_userline

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

    # -- context handling -- #
    def _gen_channel(self, channel_name):
        # self.channels
        if channel_name not in self.channels:
            self.channels.append(channel_name)

            self.logger.debug("added %s to channels", channel_name)

        # self.channel_obj
        channel_objs = []
        for chan in self.channel_obj:
            channel_objs.append(chan.name)

        if channel_name not in channel_objs:
            chan = Channel(self.server)
            chan.name = channel_name
            self.channel_obj.append(chan)

            self.logger.debug("generated channel object for %s", channel_name)

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
            "generated user object for %s (%s) [%s]",
            user.nick,
            user.login,
            user.char_limit,
        )

        # return the created user obj
        return user

    # -- cmd handling -- #
    def channel_msg(self, channel_name, user_line, cmd, user_args):
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

        # print
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
            self.logger.warning(
                "ignoring cmd %s in %s (ratelimited)", cmd, channel.name
            )

            return

        # update tstamp
        channel.tstamp = tstamp

        # exec
        ChanCMD.CMDS[cmd](channel, user, user_args)

    def user_msg(self, user_line, cmd, user_args):
        user_line = chop_userline(user_line)
        user_nick = user_line["nick"]
        user_login = user_line["login"]

        user = self._gen_user(user_nick, user_login)

        self.logger.info(
            "%s%s%s %s %s",
            f"{ac.BMGN}[{ac.BWHI}{user.nick}",
            f"{ac.BRED}/",
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
                self.logger.warning(
                    "ignoring cmd %s in %s (ratelimited)", cmd, user.nick
                )

                return

        user.tstamp = tstamp

        UserCMD.CMDS[cmd](user, user_args)

    # -- irc handling -- #
    def bot_join(self, botname_with_vhost, channel_name):
        channel_name = re.sub(r"^:", "", channel_name)

        self._gen_channel(channel_name)

        for chan in self.channel_obj:
            if chan.name == channel_name:
                channel = chan
                break

        if not channel.char_limit:
            channel.char_limit = 512 - len(
                f"{botname_with_vhost} PRIVMSG {channel.name} :\r\n".encode("utf-8")
            )

            self.logger.debug(
                "char_limit for %s is set to %s", channel.name, channel.char_limit
            )

        self.sock_ops.send_raw(f"WHO {channel_name}")
        self.logger.debug("sent WHO for %s", channel_name)

    def bot_invite(self, user, channel_name):
        self.logger.info("%s has invited us to %s", user, channel_name)
        self.sock_ops.send_join(channel_name)

    def bot_kick(self, user_line, channel_name, reason):
        user_line = chop_userline(user_line)

        self.logger.warning(
            "%s (%s) has kicked us from %s: %s",
            user_line[0],
            user_line[1],
            channel_name,
            reason,
        )
        self.sock_ops.send_join(channel_name)

    def bot_ban(self, channel_name):
        if channel_name in self.channels:
            self.channels.remove(channel_name)

        for chan in self.channel_obj:
            if chan.name == channel_name:
                self.channel_obj.remove(chan)

        self.logger.info("we are banned from %s, removing from lists", channel_name)

        if len(self.channels) == 0:
            self.logger.info("channels list is empty, quitting")

            self.server.stop()

    def nick(self, user_line, user_new_nick):
        user_line = chop_userline(user_line)
        user_old_nick = user_line["nick"]
        user_login = user_line["login"]

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

                # if user is us
                if user.nick == self.server.botname:
                    self.server.botname = user_new_nick
                    self.logger.info("changed the bot name to %s", user_new_nick)
        except UnboundLocalError:
            pass

    def initial_topic_msg(self, channel_name, msg):
        for chan in self.channel_obj:
            if chan.name == channel_name:
                channel = chan
                break

        try:
            topic_msg = " ".join(msg).lstrip(":")
        # pylint: disable=bare-except
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
        # pylint: disable=bare-except
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
        # pylint: disable=bare-except
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

    # pylint: disable=too-many-arguments
    def who(self, channel_name, user_nick, user_ircname, user_hostname, user_props):
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
