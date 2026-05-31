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

    # -- privmsg -- #
    def privmsg(self, target_name, user_line, msg):
        # get source
        user_line = chop_userline(user_line)
        user_nick = user_line["nick"]
        user_login = user_line["login"]

        # see if the privmsg target is a channel or the bot itself
        target_obj = self.channels.get(target_name.lower())

        if target_obj:
            # target is a channel, get ChannelUser()
            user_obj = target_obj.users.get(user_nick.lower())

            # msg from a channel but no channeluser exists, die
            if not user_obj:
                target_obj.logger.error(
                    "received message from %s (%s) but user not present in channel",
                    user_nick,
                    user_login,
                )
        else:
            # target is bot, generate/get server User()
            if target_name.lower() == self.server.botname.lower():
                user_obj = self._gen_user(user_nick, user_login)
                target_obj = user_obj
            else:
                # PRIVMSG exists but coming from neither a ChannelUser() nor a
                # User(), die
                self.logger.error(
                    "user %s (%s) somehow sent a PRIVMSG with no proper target",
                    user_nick,
                    user_login,
                )

        # set timestamp and full msg str
        tstamp = int(time.strftime("%s"))
        full_msg = re.sub("^:", "", " ".join(msg))

        # base log format
        log_msg = (
            f"{ac.BMGN}[{ac.BYEL}%s{ac.BRED}¦"
            f"{ac.BWHI}{user_obj.nick} ({user_obj.login}){ac.BMGN}]"
            f"{ac.BCYN} :{full_msg}{ac.RES}"
        )

        # check if we ran an event where event is one of HOOK or CMD
        event_ran = False

        # - - CMD begin - - #
        # set vars for CMD events
        if isinstance(target_obj, Channel):
            # target is channel
            prefix = self.server.config.db.get_prefix(self.server.name, target_obj.name)
            cmds = ChanCMD.CMDS
            disabled_commands = self.server.config.db.get_disabled_commands(
                self.server.name, target_obj.name
            )

            # add msg to chats of user
            if len(user_obj.chats) >= 10:
                user_obj.chats = user_obj.chats[1:]

            user_obj.chats.append(
                {
                    "tstamp": tstamp,
                    "chat": full_msg,
                }
            )
        else:
            # target is a user
            prefix = "?"
            cmds = UserCMD.CMDS
            disabled_commands = self.server.config.db.get_disabled_user_commands(
                self.server.name
            )

        # if privmsg contents starts w/ prefix, handle cmd events
        if msg[0].startswith(f":{prefix}"):
            # split msg to: cmd + args and get the cmd name in lowercase for
            # lookups
            cmd_with_prefix, *user_args = msg
            cmd = cmd_with_prefix.removeprefix(f":{prefix}").lower()

            # get the cmd metadata from CMDS dict for target_obj
            cmd_meta = cmds.get(cmd)

            if cmd_meta:
                # check if CMD is disabled
                if cmd in disabled_commands:
                    target_obj.logger.debug("CMD is disabled: %s", cmd)
                # check CMD's openai dependency
                elif cmd_meta["openai"] and not self.server.config.ai:
                    target_obj.logger.debug("openai cap needed for CMD: %s", cmd)
                # check ratelimiting
                elif target_obj.cmd_tstamp and tstamp - target_obj.cmd_tstamp < 2:
                    target_obj.logger.info("ignoring CMD %s: ratelimited", cmd)
                # all checks are done, we're running the CMD
                else:
                    target_obj.logger.info(log_msg, "CMD    ")

                    # update timestamp and call the code
                    target_obj.cmd_tstamp = tstamp
                    event_ran = True
                    cmd_meta["class"](target_obj, user_obj, user_args)
        # - - CMD end - - #

        # - - HOOK begin - - #
        if isinstance(target_obj, Channel):
            # get list of disabled HOOKs
            disabled_hooks = self.server.config.db.get_disabled_hooks(
                self.server.name, target_obj.name
            )

            # get list of HOOKs available for the channel msg we received
            hooks_to_run = []
            for hook, hook_meta in ChanHOOK.HOOKS.items():
                # see if the regex pattern of a HOOK matches the full message
                matches = re.findall(hook_meta["pattern"], full_msg)

                if not matches:
                    continue

                # check if HOOK is disabled
                if hook in disabled_hooks:
                    target_obj.logger.debug("HOOK is disabled: %s", hook)
                    continue
                # check HOOK's openai dependency
                if hook_meta["openai"] and not self.server.config.ai:
                    target_obj.logger.debug("openai cap needed for HOOK: %s", hook)
                    continue
                # all checks are done, we're running the HOOK
                hooks_to_run.append((hook_meta, matches))

            # if we are going to run HOOKs, check ratelimiting
            if (
                hooks_to_run
                and target_obj.hook_tstamp
                and tstamp - target_obj.hook_tstamp < 2
            ):
                target_obj.logger.info("ignoring HOOKs, ratelimited")
                hooks_to_run = []

            # run every matching HOOK
            for hook_meta, matches in hooks_to_run:
                target_obj.logger.info(log_msg, "HOOK   ")
                event_ran = True
                hook_meta["class"](target_obj, user_obj, matches)

            # update HOOK tstamp after every call is done
            if hooks_to_run:
                target_obj.hook_tstamp = tstamp

        # if no HOOK/CMD, channel msg -> debug, direct msg -> info
        if not event_ran:
            if isinstance(target_obj, Channel):
                target_obj.logger.debug(log_msg, "PRIVMSG")
            else:
                target_obj.logger.info(log_msg, "PRIVMSG")

    # -- channel events -- #
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

        for mode_change in mode_data:
            for mode_user, mode_info in mode_change.items():
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

        user_is_us = user_old_nick.lower() == self.server.botname.lower()

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
                user.char_limit = 512 - len(
                    f"PRIVMSG {user_new_nick} :".encode("utf-8")
                )
                user.logger = self.server.logger.getChild(user_new_nick)

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
        if user_nick.lower() == self.server.botname.lower():
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
        if user_nick.lower() == self.server.botname.lower():
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
        reason = " ".join(reason).lstrip(":")

        channel = self.channels[channel_name.lower()]

        # bot kicked
        if kicked_user.lower() == self.server.botname.lower():
            channel.logger.warning(
                "%s (%s) kicked us: (%s)", user_nick, user_login, reason
            )

            del self.channels[channel_name.lower()]
            return self.sock_ops.send_join(channel_name)

        # user kicked
        user = channel.users[kicked_user.lower()]
        del channel.users[kicked_user.lower()]

        channel.logger.info(
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
