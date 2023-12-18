import datetime
import re
import time

import bands.irc.channel.cmd as ChanCMD
import bands.irc.user.cmd as UserCMD

from bands.colors import ANSIColors

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
        self.users = server.users
        self.channel_obj = server.channel_obj
        self.user_obj = server.user_obj

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

    def _gen_user(self, user_name):
        # self.users
        if user_name not in self.channels:
            self.users.append(user_name)

        # self.user_obj
        user_objs = []
        for user in self.user_obj:
            user_objs.append(user.name)

        if user_name not in user_objs:
            user = User(self.server)
            user.name = user_name
            user.char_limit = 512 - len(f"PRIVMSG {user} :".encode("utf-8"))

            self.user_obj.append(user)

            self.logger.debug(
                "generated user object for %s (%s)", user.name, user.char_limit
            )

    # -- cmd handling -- #
    def channel_msg(self, channel_name, user_nick, cmd, user_args):
        self.logger.info(
            "%s%s%s %s %s",
            f"{ac.BMGN}[{ac.BWHI}{user_nick}",
            f"{ac.BRED}¦",
            f"{ac.BGRN}{channel_name}{ac.BMGN}]",
            f"{ac.BCYN}{cmd}",
            f"{' '.join(user_args)}{ac.RES}",
        )

        # get channel object
        for chan in self.channel_obj:
            if chan.name == channel_name:
                channel = chan
                break

        # get channeluser object
        for channeluser in chan.user_list:
            if channeluser.nick == user_nick:
                user = channeluser
                break

        # set tstamp
        tstamp = int(time.strftime("%s"))

        # if this is channel init
        if not channel.tstamp:
            channel.tstamp = tstamp

            ChanCMD.CMDS[cmd](channel, user, user_args)

            return

        # ratelimit if not authed user
        if user_nick != self.server.admin:
            if tstamp - channel.tstamp < 2:
                self.logger.warning(
                    "ignoring cmd %s in %s (ratelimited)", cmd, channel.name
                )

                return

        # update tstamp
        channel.tstamp = tstamp

        # exec
        ChanCMD.CMDS[cmd](channel, user, user_args)

    def user_msg(self, user_name, cmd, user_args):
        if len(self.user_obj) == 0 or user_name not in self.users:
            self._gen_user(user_name)

        for user_obj in self.user_obj:
            if user_obj.name == user_name:
                user = user_obj
                break

        tstamp = int(time.strftime("%s"))

        if not user.tstamp:
            user.tstamp = tstamp

            UserCMD.CMDS[cmd](user, user_args)

            return

        if user_name != self.server.admin:
            if tstamp - user.tstamp < 2:
                self.logger.warning(
                    "ignoring cmd %s in %s (ratelimited)", cmd, user.name
                )

                return

        user.tstamp = tstamp

        UserCMD.CMDS[cmd](user, user_args)

    # -- irc handling -- #
    def join(self, botname_with_vhost, channel_name):
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

    def invite(self, user, channel_name):
        self.logger.info("%s has invited us to %s", user, channel_name)
        self.sock_ops.send_join(channel_name)

    def kick(self, user, channel_name, reason):
        self.logger.info("%s has kicked us from %s for: %s", user, channel_name, reason)
        self.sock_ops.send_join(channel_name)

    def ban(self, channel_name):
        if channel_name in self.channels:
            self.channels.remove(channel_name)

        for chan in self.channel_obj:
            if chan.name == channel_name:
                self.channel_obj.remove(channel_name)

        self.logger.info("we are banned from %s, removing from lists", channel_name)

        if len(self.channels) == 0:
            self.logger.info("channels list is empty, quitting")

            self.server.stop()

    def nick_change(self, user_name, user_new_name):
        if user_name in self.users:
            self.logger.debug(
                "%s changed their nick to %s, updating the user_obj",
                user_name,
                user_new_name,
            )

            self.users.remove(user_name)
            self.users.append(user_new_name)

            for user_obj in self.user_obj:
                if user_obj.name == user_name:
                    user = user_obj
                    break

            user.name = user_new_name

            if user_name == self.server.admin:
                self.logger.debug(
                    "%s was also set as the admin user, updating",
                    user_name,
                )

                self.server.admin = user_new_name

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

        self.logger.info("topic for %s: %s", channel_name, topic_msg)

    def initial_topic_meta(self, channel_name, userline, tstamp):
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

        channel.topic_user = userline
        channel.topic_tstamp = topic_tstamp

        self.logger.info(
            "topic for %s set by %s at %s", channel_name, userline, topic_tstamp
        )

    def topic(self, channel_name, userline, msg):
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

        topic_user = userline.lstrip(":")

        channel.topic_msg = topic_msg
        channel.topic_user = topic_user
        channel.topic_tstamp = time.strftime("%Y/%m/%d %T")

        self.logger.info(
            "topic for %s updated by %s to: %s", channel_name, topic_user, topic_msg
        )

    def who(self, channel_name, userline, user_props):
        user = ChannelUser()
        user.nick = userline["nick"]
        user.ircname = userline["ircname"]
        user.hostname = userline["hostname"]
        user.ident = userline["ident"]

        user.owner = "~" in user_props
        user.admin = "&" in user_props
        user.op = "@" in user_props
        user.hop = "%" in user_props
        user.voiced = "+" in user_props

        for chan in self.channel_obj:
            if chan.name == channel_name:
                channel = chan
                break

        channel.user_list.append(user)
