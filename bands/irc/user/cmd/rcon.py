import logging

from threading import Thread

import bands.irc.channel.cmd as ChanCMD
import bands.irc.channel.hook as ChanHOOK

from bands.colors import MIRCColors

c = MIRCColors()


class RCon:
    def __init__(self, user, user_args):
        self.user = user
        self.user_args = user_args

        self.logger = self.user.logger.getChild(self.__class__.__name__)
        self.config = self.user.server.config
        self.servers = self.config.servers

        self._run()

    def _usage(self):
        self.user.send_query(
            f"{c.WHITE}┌ {c.LGREEN}debug{c.RES}   [on|off|state]\n"
            f"{c.WHITE}├ {c.LGREEN}rehash{c.RES}\n"
            f"{c.WHITE}└ {c.LGREEN}status{c.RES}\n"
            f"{c.WHITE}┌ {c.LGREEN}cmd{c.RES}     [server] [channel] [enable|disable|list] [cmd]\n"
            f"{c.WHITE}├ {c.LGREEN}hook{c.RES}    [server] [channel] [enable|disable|list] [hook]\n"
            f"{c.WHITE}└ {c.LGREEN}prefix{c.RES}  [server] [channel] [prefix]\n"
            f"{c.WHITE}┌ {c.LGREEN}connect{c.RES} [server]\n"
            f"{c.WHITE}├ {c.LGREEN}dc{c.RES}      [list of servers]\n"
            f"{c.WHITE}└ {c.LGREEN}raw{c.RES}     [server] [raw irc line]\n"
            f"{c.WHITE}┌ {c.LGREEN}join{c.RES}    [server] [list of channels]\n"
            f"{c.WHITE}├ {c.LGREEN}part{c.RES}    [server] [list of channels]\n"
            f"{c.WHITE}└ {c.LGREEN}say{c.RES}     [server] [channel] [query]"
        )

    def _get_server(self, server_name):
        try:
            return self.servers[server_name.lower()]
        except KeyError:
            self.user.send_query(f"{c.ERR} server {server_name} does not exist.")
            return None

    def _check_channel(self, channel_name):
        if channel_name[0] != "#":
            self.user.send_query(f"{c.ERR} {channel_name} does not start with a #.")
            return False

        return True

    def _dispatcher(self):
        cmd, *args = self.user_args

        # commands that take no args: rehash + status
        if cmd in ("rehash", "status"):
            return getattr(self, f"_cmd_{cmd}")()

        # commands that take one arg: debug
        if cmd == "debug":
            if not args or len(args) > 1 or args[0] not in ("on", "off", "state"):
                return self.user.send_query(
                    f"{c.ERR} must specify just {{on|off|state}}."
                )
            return self._cmd_debug(args[0])

        # commands that take multiple args: connect + dc | join+part | raw | say
        if cmd in (
            "connect",
            "dc",
            "join",
            "part",
            "raw",
            "say",
            "cmd",
            "hook",
            "prefix",
        ):
            if not args:
                err_msg = "at least one" if cmd in ("connect", "dc") else "a"
                return self.user.send_query(f"{c.ERR} must supply {err_msg} server.")

            # connect + dc
            if cmd in ("connect", "dc"):
                for server_name in args:
                    if server_obj := self._get_server(server_name):
                        getattr(self, f"_cmd_{cmd}")(server_obj)
                return

            server_name, *rest = args
            if not (server_obj := self._get_server(server_name)):
                return

            # join + part
            if cmd in ("join", "part"):
                if not rest:
                    return self.user.send_query(
                        f"{c.ERR} must supply at least one channel."
                    )

                for channel_name in rest:
                    if self._check_channel(channel_name):
                        getattr(self, f"_cmd_{cmd}")(server_obj, channel_name)
                return

            # raw
            if cmd == "raw":
                query_msg = " ".join(rest)

                if not query_msg:
                    return self.user.send_query(f"{c.ERR} no message provided.")

                return self._cmd_raw(server_obj, query_msg)

            # say + cmd + hook + prefix
            if cmd in ("say", "cmd", "hook", "prefix"):
                if not rest:
                    return self.user.send_query(f"{c.ERR} must supply a channel.")

                channel_name, *msg_parts = rest

                if not msg_parts:
                    return self.user.send_query(
                        f"{c.ERR} you've only provided a channel name"
                    )

                if not self._check_channel(channel_name):
                    return

                # get channel_obj
                try:
                    channel_obj = server_obj.channels[channel_name.lower()]
                except KeyError:
                    return self.user.send_query(
                        f"{c.ERR} not in {channel_name} in {server_obj.name}."
                    )

                # say
                if cmd == "say":
                    query_msg = " ".join(msg_parts)
                    return self._cmd_say(server_obj, channel_obj, query_msg)

                # prefix
                if cmd == "prefix":
                    if len(msg_parts) > 1:
                        return self.user.send_query(
                            f"{c.ERR} must supply just one prefix"
                        )

                    return self._cmd_prefix(server_obj, channel_obj, msg_parts[0])

                # cmd + hook
                if cmd in ("cmd", "hook"):
                    return self._cmd_toggle(server_obj, channel_obj, msg_parts, cmd)
        self._usage()

    # - - bot cmd - - #
    def _cmd_debug(self, arg):
        root_logger = logging.getLogger()

        if arg == "state":
            return self.user.send_query(
                f"{c.INFO} current loglevel is {c.LGREEN}{root_logger.level}{c.RES}."
            )

        level = logging.DEBUG if arg == "on" else logging.INFO
        root_logger.setLevel(level)

        self.user.send_query(f"{c.INFO} set the loglevel to {c.LGREEN}{level}{c.RES}.")

    def _cmd_rehash(self):
        self.user.send_query(f"{c.INFO} reloading configuration YAML.")

        try:
            self.config.load_yaml()
        except:
            self.user.send_query(f"{c.ERR} config reload failed.")
            self.logger.exception("config reload failed")

        self.user.send_query(f"{c.INFO} parsing servers.")

        try:
            self.config.parse_servers()
        except:
            self.user.send_query(f"{c.ERR} server parsing failed.")
            self.logger.exception("server parsing failed")

        self.user.send_query(f"{c.INFO} rehashed the configuration.")

    def _cmd_status(self):
        msg = f"{c.INFO} active connections are:\n"

        for server in self.config.servers.values():
            msg += f"{c.LRED}{server.name}{c.RES}\n"
            msg += f"{c.WHITE}├ {c.LGREEN}admin:{c.RES} "

            if server.admin:
                msg += f"{server.admin.nick} ({server.admin.login})\n"
            else:
                msg += "no auth\n"

            msg += f"{c.WHITE}└ {c.LGREEN}channels:{c.RES}"

            if not server.channels:
                msg += " none\n"

            else:
                msg += "\n"
                for chan in server.channels.values():
                    msg += f"  {c.LRED}→ {c.LGREEN}{chan.name}{c.RES}\n"
                    # fmt: off
                    if chan.topic_msg:
                        msg += f"    {c.WHITE}├ {c.YELLOW}topic  {c.RES}{chan.topic_msg}\n"
                        msg += f"    {c.WHITE}├ {c.YELLOW}set by {c.RES}{chan.topic_nick} ({chan.topic_login})\n"
                        msg += f"    {c.WHITE}├ {c.YELLOW}date   {c.RES}{chan.topic_tstamp}\n"
                    else:
                        msg += f"    {c.WHITE}├ {c.YELLOW}topic  {c.RES}not set\n"

                    msg += f"    {c.WHITE}└ {c.YELLOW}users: \n"
                    # fmt: on

                    for user in chan.users.values():
                        userstr = ""

                        if user.owner:
                            userstr += "~"
                        if user.admin:
                            userstr += "&"
                        if user.op:
                            userstr += "@"
                        if user.hop:
                            userstr += "%"
                        if user.voiced:
                            userstr += "+"

                        userstr += f"{user.nick} ({user.login})"

                        msg += f"      {c.LRED}→{c.RES} {userstr} \n"

        self.user.send_query(msg)

    # - - bot cmd / channel specific - - #
    def _cmd_toggle(self, server_obj, channel_obj, args, toggle_type):
        is_cmd = toggle_type == "cmd"
        item_name = "command" if is_cmd else "hook"
        registry = ChanCMD.CMDS if is_cmd else ChanHOOK.HOOKS

        try:
            action, *item_args = args
        except ValueError:
            return self.user.send_query(
                f"{c.ERR} must specify one of enable, disable or list."
            )

        if action not in ("enable", "disable", "list"):
            return self.user.send_query(
                f"{c.ERR} must specify one of enable, disable or list."
            )

        # cmd|hook $server $channel list
        if action == "list":
            if item_args:
                return self.user.send_query(f"{c.ERR} list takes no {item_name}.")

            method_to_call = (
                self.config.db.get_disabled_commands
                if is_cmd
                else self.config.db.get_disabled_hooks
            )
            disabled = method_to_call(server_obj.name, channel_obj.name)

            if not disabled:
                return self.user.send_query(
                    f"{c.INFO} no {item_name} are disabled in {channel_obj.name}."
                )

            return self.user.send_query(
                f"{c.INFO} disabled {item_name} in {channel_obj.name}@"
                f"{server_obj.name}: "
                f"{c.LGREEN}{', '.join(disabled)}{c.RES}"
            )

        # cmd|hook $server $channel enable|disable $cmd|$hook
        if len(item_args) != 1:
            return self.user.send_query(f"{c.ERR} must supply one {item_name}.")

        item = item_args[0]
        if item not in registry:
            return self.user.send_query(f"{c.ERR} no such channel {item_name}: {item}.")

        if is_cmd and registry[item]["openai"] and not server_obj.config.ai:
            return self.user.send_query(
                f"{c.ERR} channel command {item} requires openai " "configuration."
            )

        method_name = f"{action}_{item_name}"
        getattr(self.config.db, method_name)(server_obj.name, channel_obj.name, item)

        self.user.send_query(
            f"{c.INFO} {action}d {c.LGREEN}{item}{c.RES} in "
            f"{channel_obj.name}@{server_obj.name}."
        )

    def _cmd_prefix(self, server_obj, channel_obj, prefix):
        if len(prefix) != 1:
            return self.user.send_query(f"{c.ERR} prefix must be one character.")

        if prefix.isspace():
            return self.user.send_query(f"{c.ERR} prefix cannot be whitespace.")

        self.config.db.set_prefix(server_obj.name, channel_obj.name, prefix)

        self.user.send_query(
            f"{c.INFO} set {channel_obj.name}@{server_obj.name} prefix to "
            f"{c.LGREEN}{prefix}{c.RES}."
        )

    # - - server cmd - - #
    def _cmd_connect(self, server_obj):
        if server_obj.socket.conn is not None:
            return self.user.send_query(
                f"{c.ERR} already connected to {server_obj.name}."
            )

        self.user.send_query(f"{c.INFO} connecting to {server_obj.name}")
        server_thread = Thread(target=server_obj.run)
        server_thread.start()

    def _cmd_dc(self, server_obj):
        if self.user.server == server_obj:
            return self.user.send_query(
                f"{c.ERR} cannot disconnect from {server_obj.name} "
                "because it is the c2 server."
            )

        if not server_obj.socket.conn:
            del self.config.servers[server_obj.name.lower()]

            return self.user.send_query(
                f"{c.WARN} {server_obj.name} has no socket, just "
                "removing it from the server list."
            )

        self.user.send_query(f"{c.INFO} disconnecting from {server_obj.name}")
        server_obj.stop()

    def _cmd_raw(self, server_obj, query_msg):
        self.user.send_query(
            f"{c.GREEN}[{c.LBLUE}RAW{c.GREEN}]"
            f"[{c.LGREEN}{server_obj.name}{c.GREEN}]{c.RES} {query_msg}"
        )

        server_obj.sock_ops.send_raw(query_msg)

    # - - channel cmd - - #
    def _cmd_join(self, server_obj, channel_name):
        if channel_name.lower() in server_obj.channels.keys():
            return self.user.send_query(
                f"{c.ERR} already in {channel_name} in {server_obj.name}."
            )

        server_obj.sock_ops.send_join(channel_name)
        self.user.send_query(
            f"{c.INFO} sent JOIN for {channel_name} in {server_obj.name}."
        )

    def _cmd_part(self, server_obj, channel_name):
        if not server_obj.channels:
            return self.user.send_query(
                f"{c.ERR} not in any channels {server_obj.name}."
            )

        if channel_name.lower() not in server_obj.channels.keys():
            return self.user.send_query(
                f"{c.ERR} not in {channel_name} {server_obj.name}."
            )

        server_obj.sock_ops.send_part(channel_name, "mom said no.")
        self.user.send_query(f"{c.INFO} parted from {channel_name}")

    def _cmd_say(self, server_obj, channel_obj, query_msg):
        self.user.send_query(
            f"{c.GREEN}[{c.LBLUE}SAY{c.GREEN}]"
            f"[{c.LGREEN}{channel_obj.name}{c.LRED}@"
            f"{c.WHITE}{server_obj.name}{c.GREEN}]{c.RES} {query_msg}"
        )

        channel_obj.send_query(query_msg)

    def _run(self):
        if self.user != self.user.server.admin:
            return

        if not self.user_args:
            return self._usage()

        self._dispatcher()
