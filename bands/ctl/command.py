import logging
import shlex

from threading import Thread

import bands.irc.channel.cmd as ChanCMD
import bands.irc.channel.hook as ChanHOOK
import bands.irc.user.cmd as UserCMD

from bands.colors import ANSIColors

ac = ANSIColors()


class CTLCommand:
    def __init__(self, config, logger, request):
        self.config = config
        self.servers = config.servers
        self.logger = logger

        self.request = request
        self.user_args = []

    def _dispatcher(self):
        cmd, *args = self.user_args

        # commands that take no args
        if cmd in ("help", "rehash", "status"):
            if args:
                return f"{cmd} takes no args"

            return getattr(self, f"_cmd_{cmd}")()

        # commands that take one arg
        if cmd in ("debug"):
            if len(args) != 1 or args[0] not in ("on", "off", "state"):
                return "must specify one of {on|off|state}"

            return self._cmd_debug(args[0])

        # commands that take a server
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
            "usercmd",
        ):
            if not args:
                return "must provide a server"

            server_name, *rest = args
            server_obj = self.servers.get(server_name.lower())
            if not server_obj:
                return f"{server_name} is not a valid server"

            # connect + dc
            if cmd in ("connect", "dc"):
                if rest:
                    return "must provide just one server"

                return getattr(self, f"_cmd_{cmd}")(server_obj)

            # usercmd
            if cmd == "usercmd":
                return self._cmd_toggle(server_obj, rest, cmd)

            # raw
            if cmd == "raw":
                query_msg = " ".join(rest)
                if not query_msg:
                    return "must provide a raw IRC line"

                return self._cmd_raw(server_obj, query_msg)

            # join + part
            if cmd in ("join", "part"):
                if len(rest) != 1:
                    return "must provide a server and channel combination"

                channel_name = rest[0]
                if channel_name[0] != "#":
                    return "channel names should start with a #"

                return getattr(self, f"_cmd_{cmd}")(server_obj, channel_name)

            # say + cmd + hook + prefix
            if not rest:
                return "must provide a channel"

            channel_name, *msg_parts = rest
            if channel_name[0] != "#":
                return "channel names should start with a #"

            channel_obj = server_obj.channels.get(channel_name.lower())

            if not channel_obj:
                return f"bot is not in {channel_name} @ {server_obj.name}"

            if not msg_parts:
                return "you have provided just a channel name"

            if cmd == "say":
                return self._cmd_say(channel_obj, " ".join(msg_parts))

            if cmd == "prefix":
                if len(msg_parts) != 1:
                    return "must provide a single prefix"

                return self._cmd_prefix(server_obj, channel_obj, msg_parts[0])

            return self._cmd_toggle(server_obj, msg_parts, cmd, channel_obj)

        return "unknown command"

    # - - bot cmd - - #
    def _cmd_help(self):
        return (
            "┌──────────────────────────────────────────────────────┐\n"
            "│ help                                                 │\n"
            "│ rehash                                               │\n"
            "│ status                                               │\n"
            "│ debug   ┆ {on|off|state}                             │\n"
            "├──────────────────────────────────────────────────────┤\n"
            "│ cmd     ┆ $server  $channel  {enable|disable}  $cmd  │\n"
            "│         ┆ $server  $channel  list                    │\n"
            "│ usercmd ┆ $server            {enable|disable}  $cmd  │\n"
            "│         ┆ $server            list              $cmd  │\n"
            "│ hook    ┆ $server  $channel  {enable|disable}  $hook │\n"
            "│         ┆ $server  $channel  list              $hook │\n"
            "│ prefix  ┆ $server  $channel  $prefix                 │\n"
            "├──────────────────────────────────────────────────────┤\n"
            "│ connect ┆ $server                                    │\n"
            "│ dc      ┆ $server                                    │\n"
            "│ raw     ┆ $server  $rawLine                          │\n"
            "├──────────────────────────────────────────────────────┤\n"
            "│ join    ┆ $server  $channel                          │\n"
            "│ part    ┆ $server  $channel                          │\n"
            "│ say     ┆ $server  $channel  $query                  │\n"
            "└──────────────────────────────────────────────────────┘"
        )

    def _cmd_debug(self, arg):
        root_logger = logging.getLogger()

        if arg == "state":
            return f"current loglevel: {root_logger.level}"

        level = logging.DEBUG if arg == "on" else logging.INFO
        root_logger.setLevel(level)

        return f"loglevel set to: {level}"

    def _cmd_rehash(self):
        self.config.load_yaml()
        self.config.parse_servers()

        return "server configuration rehashed"

    def _cmd_status(self):
        msg = ""

        for server in self.config.servers.values():
            state = "running" if server.running else "stopped"
            socket_state = "connected" if server.socket.connected else "disconnected"
            msg += f"{server.name} ({state}, {socket_state})\n"

            if not server.channels:
                msg += "  channels: none\n"
                continue

            msg += "  channels:\n"
            for chan in server.channels.values():
                msg += f"    {chan.name}\n"

                if chan.topic_msg:
                    msg += f"      topic: {chan.topic_msg}\n"
                    msg += f"      set by: {chan.topic_nick} ({chan.topic_login})\n"
                    msg += f"      date: {chan.topic_tstamp}\n"
                else:
                    msg += "      topic: not set\n"

                msg += "      users:\n"
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
                    msg += f"        {userstr}\n"

        if msg:
            msg = "active connections are:\n" + msg.rstrip("\n")
        else:
            msg = "not connected to any servers"

        return msg

    # - - bot cmd / channel specific - - #
    def _cmd_toggle(self, server_obj, args, toggle_type, channel_obj=None):
        is_usercmd = toggle_type == "usercmd"
        is_cmd = toggle_type == "cmd"

        if is_usercmd:
            item_name = "user command"
            registry = UserCMD.CMDS
        elif is_cmd:
            item_name = "command"
            registry = ChanCMD.CMDS
        else:
            item_name = "hook"
            registry = ChanHOOK.HOOKS

        if not args or args[0] not in ("enable", "disable", "list"):
            return "must specify one of {enable|disable|list}"

        action, *item_args = args

        # {cmd|hook} $server $channel list
        # usercmd $server list
        if action == "list":
            if item_args:
                return "list takes no args"

            if is_usercmd:
                disabled = self.config.db.get_disabled_user_commands(server_obj.name)
                target_name = server_obj.name
            else:
                method_to_call = (
                    self.config.db.get_disabled_commands
                    if is_cmd
                    else self.config.db.get_disabled_hooks
                )
                disabled = method_to_call(server_obj.name, channel_obj.name)
                target_name = f"{channel_obj.name}@{server_obj.name}"

            if not disabled:
                return f"no {item_name}(s) disabled in {target_name}"

            return f"disabled {item_name}(s) in {target_name}: {', '.join(disabled)}"

        # {cmd|hook} $server $channel {enable|disable} $cmd/$hook
        # usercmd $server {enable|disable} $cmd
        if len(item_args) != 1:
            return f"must provide one {item_name}"

        item = item_args[0]
        if item not in registry:
            return f"no such {item_name}"

        if registry[item]["openai"] and not server_obj.config.ai:
            return f"{item_name} {item} requires openai"

        if is_usercmd:
            getattr(self.config.db, f"{action}_user_command")(server_obj.name, item)
            target_name = server_obj.name
        else:
            getattr(self.config.db, f"{action}_{item_name}")(
                server_obj.name, channel_obj.name, item
            )
            target_name = f"{channel_obj.name}@{server_obj.name}"

        return f"{action}d {item} in {target_name}"

    def _cmd_prefix(self, server_obj, channel_obj, prefix):
        if len(prefix) != 1:
            return "prefix must be one character wide"

        if prefix.isspace():
            return "prefix cannot be a whitespace"

        self.config.db.set_prefix(server_obj.name, channel_obj.name, prefix)

        return f"{channel_obj.name}@{server_obj.name} prefix set to {prefix}"

    # - - server cmd - - #
    def _cmd_connect(self, server_obj):
        if server_obj.running or server_obj.socket.conn is not None:
            return f"already connected to {server_obj.name}"

        server_thread = Thread(target=server_obj.run)
        server_thread.start()

        return f"connecting to {server_obj.name}"

    def _cmd_dc(self, server_obj):
        server_name = server_obj.name

        if server_obj.running or server_obj.socket.conn is not None:
            server_obj.stop(reconnect=False)
            response = f"disconnecting from {server_name}"
        else:
            response = f"{server_name} has no socket, removing it from the server list"

        try:
            del self.config.servers[server_name.lower()]
        except KeyError:
            pass

        return response

    def _cmd_raw(self, server_obj, query_msg):
        if not server_obj.socket.conn:
            return f"not connected to {server_obj.name}"

        server_obj.sock_ops.send_raw(query_msg)

        return f"sent raw line to {server_obj.name}: {query_msg}"

    # - - channel cmd - - #
    def _cmd_join(self, server_obj, channel_name):
        if not server_obj.socket.conn:
            return f"not connected to {server_obj.name}"

        if channel_name.lower() in server_obj.channels.keys():
            return f"already in {channel_name} @ {server_obj.name}"

        server_obj.sock_ops.send_join(channel_name)

        return f"sent JOIN for: {channel_name} @ {server_obj.name}"

    def _cmd_part(self, server_obj, channel_name):
        if not server_obj.socket.conn:
            return f"not connected to {server_obj.name}"

        if not server_obj.channels:
            return f"not in any channels @ {server_obj.name}"

        if channel_name.lower() not in server_obj.channels.keys():
            return f"not in {channel_name} {server_obj.name}"

        server_obj.sock_ops.send_part(channel_name, "mom said no.")

        return f"parted from {channel_name} @ {server_obj.name}"

    def _cmd_say(self, channel_obj, query_msg):
        channel_obj.send_query(query_msg)

        return f"sent query to {channel_obj.name}"

    # - - action - - #
    def run(self):
        try:
            self.user_args = shlex.split(self.request)
        except:
            self.logger.warning("parsing %s failed", self.request, exc_info=True)
            return "invalid command"

        if not self.user_args:
            return "must provide a command"

        self.logger.info(
            "%s",
            f"{ac.BMGN}[{ac.BYEL}CTL{ac.BMGN}]{ac.BRED}: {ac.BCYN}{self.request}{ac.RES}",
        )

        return self._dispatcher()
