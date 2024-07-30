import logging

from threading import Thread

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
        # fmt: off
        msg  = f"{c.WHITE}├ {c.LGREEN}connect{c.RES} [server]\n"
        msg += f"{c.WHITE}├ {c.LGREEN}dc{c.RES}      [list of servers]\n"
        msg += f"{c.WHITE}├ {c.LGREEN}debug{c.RES}   [on|off|state]\n"
        msg += f"{c.WHITE}├ {c.LGREEN}join{c.RES}    [server] [list of channels]\n"
        msg += f"{c.WHITE}├ {c.LGREEN}part{c.RES}    [server] [list of channels]\n"
        msg += f"{c.WHITE}├ {c.LGREEN}raw{c.RES}     [server] [raw irc line]\n"
        msg += f"{c.WHITE}├ {c.LGREEN}rehash{c.RES}\n"
        msg += f"{c.WHITE}└ {c.LGREEN}status{c.RES}"
        # fmt: on
        self.user.send_query(msg)

    def _dispatcher(self):
        cmd, *args = self.user_args

        if cmd in ("rehash", "status"):
            return getattr(self, f"_cmd_{cmd}")()

        # debug
        if cmd == "debug":
            if not args or len(args) > 1 or args[0] not in ("on", "off", "state"):
                err_msg = f"{c.ERR} must specify just {{on|off|state}}."
                return self.user.send_query(err_msg)

            return self._cmd_debug(args[0])

        # connect + dc
        if cmd in ("connect", "dc"):
            if not args:
                err_msg = f"{c.ERR} must supply at least one server."
                return self.user.send_query(err_msg)

            for server_name in args:
                try:
                    server_obj = self.servers[server_name]
                except KeyError:
                    err_msg = f"{c.ERR} {server_name} does not exist."
                    return self.user.send_query(err_msg)

                return getattr(self, f"_cmd_{cmd}")(server_obj)

        # join + part + raw
        if cmd in ("join", "part", "raw"):
            # take input
            if not args:
                err_msg = f"{c.ERR} must supply a server as the first arg."
                return self.user.send_query(err_msg)

            if cmd != "raw" and len(args) == 1:
                err_msg = f"{c.ERR} must supply at least one channel."
                return self.user.send_query(err_msg)

            server_name, *rest = args

            try:
                server_obj = self.servers[server_name]
            except KeyError:
                return self.user.send_query(f"{c.ERR} {server_name} does not exist.")

            # not connected
            if not server_obj.socket.connected:
                return self.user.send_query(f"{c.ERR} not connected to {server_name}.")

            # raw
            if cmd == "raw":
                raw_msg = " ".join(rest)

                if not raw_msg:
                    return self.user.send_query(f"{c.ERR} no message provided.")

                return self._cmd_raw(server_obj, raw_msg)

            # join + part
            for channel_name in rest:
                if channel_name[0] != "#":
                    err_msg = f"{c.ERR} {channel_name} does not start with a #."
                    return self.user.send_query(err_msg)

                getattr(self, f"_cmd_{cmd}")(server_obj, channel_name)

            return

        self._usage()

    # - - bot cmd - - #
    def _cmd_debug(self, arg):
        root_logger = logging.getLogger()

        if arg == "state":
            msg = f"{c.INFO} current loglevel is {c.LGREEN}{root_logger.level}{c.RES}."
            return self.user.send_query(msg)

        level = logging.DEBUG if arg == "on" else logging.INFO
        root_logger.setLevel(level)

        msg = f"{c.INFO} set the loglevel to {c.LGREEN}{level}{c.RES}."
        self.user.send_query(msg)

    # - - server cmd - - #
    def _cmd_connect(self, server_obj):
        if server_obj.socket.conn is not None:
            err_msg = f"{c.ERR} already connected to {server_obj.name}."
            return self.user.send_query(err_msg)

        self.user.send_query(f"{c.INFO} connecting to {server_obj.name}")
        server_thread = Thread(target=server_obj.run)
        server_thread.start()

    def _cmd_dc(self, server_obj):
        if self.user.server == server_obj:
            err_msg = f"{c.ERR} cannot disconnect from {server_obj.name} "
            err_msg += "because it is the c2 server."
            return self.user.send_query(err_msg)

        if not server_obj.socket.conn:
            warn_msg = f"{c.WARN} {server_obj.name} has no socket, just "
            warn_msg += "removing it from the server list."
            self.user.send_query(warn_msg)

            return self.config.servers.remove(server_obj)

        self.user.send_query(f"{c.INFO} disconnecting from {server_obj.name}")
        server_obj.stop()

    def _cmd_raw(self, server_obj, raw_msg):
        msg = f"{c.INFO} sending {c.WHITE}{raw_msg}{c.RES} to "
        msg += f"{c.LGREEN}{server_obj.name}{c.RES}."
        self.user.send_query(msg)

        server_obj.sock_ops.send_raw(raw_msg)

    # - - channel cmd - - #
    def _cmd_join(self, server_obj, channel_name):
        if channel_name in server_obj.channels.keys():
            err_msg = f"{c.ERR} already in {channel_name} in {server_obj.name}."
            return self.user.send_query(err_msg)

        server_obj.sock_ops.send_join(channel_name)
        self.user.send_query(f"{c.INFO} sent JOIN for {channel_name}.")

    def _cmd_part(self, server_obj, channel_name):
        if not server_obj.channels:
            err_msg = f"{c.ERR} not in any channels {server_obj.name}."
            return self.user.send_query(err_msg)

        if channel_name not in server_obj.channels.keys():
            err_msg = f"{c.ERR} not in {channel_name} {server_obj.name}."
            return self.user.send_query(err_msg)

        server_obj.sock_ops.send_part(channel_name, "mom said no.")
        self.user.send_query(f"{c.INFO} parted from {channel_name}")

    # - - noarg - - #
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

    def _run(self):
        if self.user != self.user.server.admin:
            return

        if not self.user_args:
            return self._usage()

        self._dispatcher()
