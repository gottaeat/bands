import datetime
import re
import time

import bands.irc.channel.cmd as ChanCMD
import bands.irc.channel.hook as ChanHOOK
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
        self.channels = server.channels
        self.users = server.users

    # -- object generators -- #
    def _gen_user(self, user_nick, user_login):
        try:
            return self.users[user_nick.lower()]
        except KeyError:
            user = User(self.server)
            user.nick = user_nick
            user.login = user_login
            user.char_limit = 512 - len(f"PRIVMSG {user_nick} :".encode("utf-8"))
            user.logger = self.server.logger.getChild(user_nick)

            self.users[user_nick.lower()] = user
            user.logger.debug("generated")

            return user

    # -- channel events -- #
    def _channel_hook_prompt(self, channel_obj, user_obj, full_msg):
        prompt_msg = f"{ac.BMGN}[{ac.BYEL}HOOK{ac.BRED}¦"
        prompt_msg += f"{ac.BWHI}{user_obj.nick} ({user_obj.login}){ac.BMGN}]"
        prompt_msg += f"{ac.BCYN} :{full_msg}{ac.RES}"
        channel_obj.logger.info("%s", prompt_msg)

    def _channel_hook(self, channel_obj, user_obj, full_msg, tstamp):
        # hook matches
        urls = re.findall(r"https?://[^\s]+", full_msg)

        # url dispatcher
        if urls:
            self._channel_hook_prompt(channel_obj, user_obj, full_msg)

            if channel_obj.hook_tstamp and tstamp - channel_obj.hook_tstamp < 2:
                return channel_obj.logger.debug("ignoring url: ratelimited")

            channel_obj.hook_tstamp = tstamp
            ChanHOOK.HOOKS["url_dispatcher"](channel_obj, user_obj, urls)

    def _channel_cmd(self, channel_obj, user_obj, msg, tstamp):
        if msg[0] in ChanCMD.CMDS:
            cmd, *user_args = msg

            prompt_msg = f"{ac.BMGN}[{ac.BYEL}CMD {ac.BRED}¦"
            prompt_msg += f"{ac.BWHI}{user_obj.nick} ({user_obj.login}){ac.BMGN}]"
            prompt_msg += f"{ac.BCYN} {cmd} {' '.join(user_args)}{ac.RES}"
            channel_obj.logger.info("%s", prompt_msg)

            if channel_obj.cmd_tstamp:
                try:
                    rt_exempt = self.users[user_obj.nick.lower()] == self.server.admin
                except KeyError:
                    rt_exempt = False

                if not rt_exempt and tstamp - channel_obj.cmd_tstamp < 2:
                    return channel_obj.logger.debug("ignoring cmd %s: ratelimited", cmd)

            channel_obj.cmd_tstamp = tstamp
            ChanCMD.CMDS[cmd](channel_obj, user_obj, user_args)

    def channel_msg(self, channel_name, user_line, msg):
        channel = self.channels[channel_name.lower()]

        user_line = chop_userline(user_line)
        user_nick = user_line["nick"]

        try:
            user = channel.users[user_nick.lower()]
        except KeyError:
            channel.logger.warning(
                "received message from %s (%s) but user not present in channel",
                user_nick,
                user_line["login"],
            )

        # get timestamp
        tstamp = int(time.strftime("%s"))

        # full msg as str
        full_msg = re.sub("^:", "", " ".join(msg))

        # add msg to chats of user
        if len(user.chats) >= 10:
            user.chats = user.chats[1:]

        user.chats.append(
            {
                "tstamp": tstamp,
                "chat": full_msg,
            }
        )

        # ChanCMD
        self._channel_cmd(channel, user, msg, tstamp)

        # ChanHOOK
        self._channel_hook(channel, user, full_msg, tstamp)

    def bot_invite(self, user_line, channel_name):
        user_line = chop_userline(user_line)

        self.logger.info(
            "%s (%s) invited us to %s",
            user_line["nick"],
            user_line["login"],
            channel_name,
        )

    def bot_ban(self, channel_name):
        self.logger.warning("we are banned from %s", channel_name)

    def bot_invite_only(self, channel_name):
        self.logger.warning("%s requires an invite", channel_name)

    def initial_topic_msg(self, channel_name, msg):
        channel = self.channels[channel_name.lower()]
        channel.topic_msg = " ".join(msg).lstrip(":")

        channel.logger.info("topic: %s", channel.topic_msg)

    def initial_topic_meta(self, channel_name, user_line, tstamp):
        user_line = chop_userline(user_line)
        channel = self.channels[channel_name.lower()]

        topic_tstamp = datetime.datetime.fromtimestamp(int(tstamp)).strftime(
            "%Y/%m/%d %T"
        )

        channel.topic_nick = user_line["nick"]
        channel.topic_login = user_line["login"]
        channel.topic_tstamp = topic_tstamp

        channel.logger.info(
            "topic set by %s (%s) at %s",
            channel.topic_nick,
            channel.topic_login,
            channel.topic_tstamp,
        )

    def topic(self, channel_name, user_line, msg):
        user_line = chop_userline(user_line)
        channel = self.channels[channel_name.lower()]

        channel.topic_msg = " ".join(msg).lstrip(":")
        channel.topic_nick = user_line["nick"]
        channel.topic_login = user_line["login"]
        channel.topic_tstamp = time.strftime("%Y/%m/%d %T")

        channel.logger.info(
            "topic updated by %s (%s) to: %s",
            channel.topic_nick,
            channel.topic_login,
            channel.topic_msg,
        )

    def who(self, channel_name, user_nick, user_ircname, user_hostname, user_props):
        # get channel obj
        channel = self.channels[channel_name.lower()]

        # gen user
        user = ChannelUser()
        user.nick = user_nick
        user.login = f"{user_ircname}@{user_hostname}"

        user.owner = "~" in user_props
        user.admin = "&" in user_props
        user.op = "@" in user_props
        user.hop = "%" in user_props
        user.voiced = "+" in user_props

        # add
        channel.users[user_nick.lower()] = user
        channel.logger.debug("parsed WHO: %s (%s)", user_nick, user.login)

    # -- user events -- #
    def user_msg(self, user_line, cmd, user_args):
        user_line = chop_userline(user_line)
        user_nick = user_line["nick"]
        user_login = user_line["login"]

        user = self._gen_user(user_nick, user_login)

        prompt_msg = f"{ac.BMGN}[{ac.BWHI}{user.nick} ({user.login}){ac.BMGN}]"
        prompt_msg += f"{ac.BCYN} {cmd} {' '.join(user_args)}{ac.RES}"
        user.logger.info(prompt_msg)

        tstamp = int(time.strftime("%s"))

        if not user.tstamp:
            user.tstamp = tstamp
            return UserCMD.CMDS[cmd](user, user_args)

        if user != self.server.admin and tstamp - user.tstamp < 2:
            return user.logger.debug("ignoring cmd %s: ratelimited", cmd)

        user.tstamp = tstamp
        UserCMD.CMDS[cmd](user, user_args)

    def mode(self, user_line, channel_name, modes, user_nicks):
        channel = self.channels[channel_name.lower()]

        try:
            user_line = chop_userline(user_line)
            user_nick = user_line["nick"]
            user_login = user_line["login"]
        except IndexError:
            user_nick = "server"
            user_login = self.server.socket.address

        mode_data = streamline_modes(modes, user_nicks)

        if not mode_data:
            return

        for mode_user, mode_info in mode_data.items():
            user_obj = channel.users[mode_user.lower()]
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

            channel.logger.info(
                "mode %s%s %s (%s) by %s (%s)",
                "+" if mode_info["action"] else "-",
                mode_info["mode"],
                user_obj.nick,
                user_obj.login,
                user_nick,
                user_login,
            )

    def nick(self, user_line, user_new_nick):
        user_line = chop_userline(user_line)
        user_old_nick = user_line["nick"]
        user_login = user_line["login"]

        user_is_us = user_old_nick == self.server.botname

        # 0. bot
        if user_is_us:
            self.server.botname = user_new_nick
            self.logger.warning("bot name changed: %s", user_new_nick)

        # 1. channeluser objs
        for channel_obj in self.channels.values():
            try:
                channeluser = channel_obj.users[user_old_nick.lower()]
                channeluser.nick = user_new_nick

                channel_obj.users[user_new_nick.lower()] = channel_obj.users.pop(
                    user_old_nick.lower()
                )
            except KeyError:
                pass

        # 2. user obj
        if not user_is_us:
            try:
                user = self.users[user_old_nick.lower()]
                user.nick = user_new_nick
                user.logger = self.server.logger.getChild(user_new_nick)

                if user == self.server.admin:
                    self.logger.warning(
                        "admin nick change: %s (%s) => %s",
                        user_old_nick,
                        user_login,
                        user_new_nick,
                    )

                self.users[user_new_nick.lower()] = self.users.pop(
                    user_old_nick.lower()
                )
            except KeyError:
                pass

        # prompt
        self.logger.info(
            "nick change: %s (%s) => %s", user_old_nick, user_login, user_new_nick
        )

    def chghost(self, user_line, user_new_ircname, user_new_hostname):
        user_line = chop_userline(user_line)
        user_nick = user_line["nick"]

        user_old_login = user_line["login"]
        user_new_login = f"{user_new_ircname}@{user_new_hostname}"

        # 1. channeluser obj
        for channel_obj in self.channels.values():
            try:
                channel_obj.users[user_nick.lower()].login = user_new_login
            except KeyError:
                pass

        # 2. user obj
        try:
            user = self.users[user_nick.lower()]
            user.login = user_new_login

            if user == self.server.admin:
                self.logger.warning(
                    "admin host change: %s (%s) => %s",
                    user_nick,
                    user_old_login,
                    user_new_login,
                )
        except KeyError:
            pass

        # prompt
        self.logger.info(
            "host change: %s (%s) => %s", user_nick, user_old_login, user_new_login
        )

    def join(self, user_line, channel_name):
        # some ircd's send channel name w/ a :
        channel_name = re.sub(r"^:", "", channel_name)

        user_line_chop = chop_userline(user_line)
        user_nick = user_line_chop["nick"]
        user_login = user_line_chop["login"]

        # bot join
        if user_nick == self.server.botname:
            channel = Channel(self.server)
            channel.name = channel_name
            channel.logger = self.server.logger.getChild(channel.name)

            self.channels[channel_name.lower()] = channel

            channel.char_limit = 512 - len(
                f"{user_line} PRIVMSG {channel.name} :\r\n".encode("utf-8")
            )

            channel.logger.debug("char_limit set to %s", channel.char_limit)

            channel.logger.info("joined channel")

            self.sock_ops.send_raw(f"WHO {channel.name}")
            return channel.logger.debug("sent WHO")

        # user join
        channel = self.channels[channel_name.lower()]

        user = ChannelUser()
        user.nick = user_nick
        user.login = user_login

        channel.users[user_nick.lower()] = user

        # prompt
        channel.logger.info("%s (%s) joined", user_nick, user_login)

    def part(self, user_line, channel_name, msg):
        user_line = chop_userline(user_line)
        user_nick = user_line["nick"]

        channel = self.channels[channel_name.lower()]

        # bot part
        if user_nick == self.server.botname:
            channel.logger.info("parted")
            del self.channels[channel_name.lower()]
            return

        # user part
        reason = " ".join(msg).lstrip(":")

        user = channel.users[user_nick.lower()]
        channel.logger.info("%s (%s) left: %s", user_nick, user.login, reason)

        del channel.users[user_nick.lower()]

    def kick(self, user_line, channel_name, kicked_user, reason):
        user_line = chop_userline(user_line)
        user_nick = user_line["nick"]
        user_login = user_line["login"]

        channel = self.channels[channel_name.lower()]

        # bot kicked
        if kicked_user == self.server.botname:
            channel.logger.warning(
                "%s (%s) kicked us: (%s)", user_nick, user_login, reason
            )

            del self.channels[channel_name.lower()]
            return self.sock_ops.send_join(channel_name)

        # user kicked
        user = channel.users[user_nick.lower()]
        del channel.users[user_nick.lower()]

        channel.logger.debug(
            "%s (%s) kicked %s (%s): %s",
            user_nick,
            user_login,
            user.nick,
            user.login,
            reason,
        )

    def quit(self, user_line, msg):
        user_line = chop_userline(user_line)
        user_nick = user_line["nick"]
        user_login = user_line["login"]

        reason = " ".join(msg).lstrip(":")

        for channel_obj in self.channels.values():
            try:
                del channel_obj.users[user_nick.lower()]
            except KeyError:
                pass

        try:
            del self.users[user_nick.lower()]
        except KeyError:
            pass

        self.logger.info("%s (%s) quit: %s", user_nick, user_login, reason)
