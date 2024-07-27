from threading import Thread

from bands.colors import MIRCColors

c = MIRCColors()


class RCon:
    def __init__(self, user, user_args):
        self.user = user
        self.user_args = user_args

        self.logger = self.user.logger.getChild(self.__class__.__name__)
        self.config = self.user.server.config

        self._run()

    def _usage(self):
        # fmt: off
        msg  = f"{c.WHITE}├ {c.LGREEN}connect{c.RES} [server]\n"
        msg += f"{c.WHITE}├ {c.LGREEN}dc{c.RES}      [list of servers]\n"
        msg += f"{c.WHITE}├ {c.LGREEN}join{c.RES}    [server] [list of channels]\n"
        msg += f"{c.WHITE}├ {c.LGREEN}part{c.RES}    [server] [list of channels]\n"
        msg += f"{c.WHITE}├ {c.LGREEN}raw{c.RES}     [server] [raw irc line]\n"
        msg += f"{c.WHITE}├ {c.LGREEN}rehash{c.RES}\n"
        msg += f"{c.WHITE}└ {c.LGREEN}status{c.RES}"
        # fmt: on
        self.user.send_query(msg)

    def _get_server(self, server_name):
        server_obj = None
        for server in self.config.servers:
            if server.name.lower() == server_name.lower():
                server_obj = server
                break

        if not server_obj:
            return

        server_channels = {}
        for channel in server_obj.channel_obj:
            server_channels[channel.name] = channel

        if len(server_channels) == 0:
            server_channels = None

        server_dict = {
            "name": server_obj.name,
            "obj": server_obj,
            "channels": server_channels,
        }

        return server_dict

    def _dispatcher(self):
        cmd = self.user_args[0]

        # rehash
        if cmd == "rehash":
            self._cmd_rehash()
            return

        # status
        if cmd == "status":
            self._cmd_status()
            return

        # connect + dc
        if cmd in ("connect", "dc"):
            server_names = self.user_args[1:]

            if len(server_names) == 0:
                self.user.send_query(f"{c.ERR} must supply at least one server.")
                return

            for server_name in server_names:
                server_dict = self._get_server(server_name)

                if server_dict is None:
                    self.user.send_query(f"{c.ERR} {server_name} does not exist.")
                    continue

                # connect
                if cmd == "connect":
                    self._cmd_connect(server_dict["obj"])
                    continue

                # dc
                if cmd == "dc":
                    self._cmd_dc(server_dict["obj"])

            return

        # join + part + raw
        if cmd in ("join", "part", "raw"):
            # take input
            if len(self.user_args) == 1:
                self.user.send_query(f"{c.ERR} must supply a server as the first arg.")
                return

            if cmd != "raw" and len(self.user_args) == 2:
                self.user.send_query(f"{c.ERR} must supply at least one channel.")
                return

            server_name = self.user_args[1]

            if cmd == "raw":
                msg = " ".join(self.user_args[2:])

                if len(msg) == 0:
                    self.user.send_query(f"{c.ERR} no message provided.")
                    return
            else:
                channel_names = self.user_args[2:]

                for channel_name in channel_names:
                    if channel_name[0] != "#":
                        self.user.send_query(f"{c.ERR} channels must start with a #.")
                        return

            # act on input
            server_dict = self._get_server(server_name)
            if server_dict is None:
                self.user.send_query(f"{c.ERR} {server_name} does not exist.")
                return

            # raw
            if cmd == "raw":
                self._cmd_raw(server_dict["obj"], msg)
                return

            # join + part
            for channel_name in channel_names:
                if cmd == "join":
                    self._cmd_join(server_dict, channel_name)
                    continue

                if cmd == "part":
                    self._cmd_part(server_dict, channel_name)
            return

        self._usage()

    # - - server cmd - - #
    def _cmd_connect(self, server_obj):
        if server_obj.socket.conn is not None:
            err_msg = f"{c.ERR} already connected to {server_obj.name}."
            self.user.send_query(err_msg)
            return

        self.user.send_query(f"{c.INFO} connecting to {server_obj.name}")
        server_thread = Thread(target=server_obj.run)
        server_thread.start()
        return

    def _cmd_dc(self, server_obj):
        if self.user.server == server_obj:
            err_msg = f"{c.ERR} cannot disconnect from {server_obj.name} "
            err_msg += "because it is the c2 server."
            self.user.send_query(err_msg)
            return

        if server_obj.socket.conn is None:
            warn_msg = f"{c.WARN} {server_obj.name} has no socket, just "
            warn_msg += "removing it from the server list."
            self.user.send_query(warn_msg)

            self.config.servers.remove(server_obj)
        else:
            self.user.send_query(f"{c.INFO} disconnecting from {server_obj.name}")
            server_obj.stop()

    def _cmd_raw(self, server_obj, msg):
        server_obj.sock_ops.send_raw(msg)

    # - - channel cmd - - #
    def _cmd_join(self, server_dict, channel_name):
        try:
            if channel_name in server_dict["channels"].keys():
                err_msg = f"{c.ERR} already in {channel_name} in "
                err_msg += f"{server_dict['obj'].name}."
                self.user.send_query(err_msg)
                return
        except AttributeError:
            pass

        server_dict["obj"].sock_ops.send_join(channel_name)
        self.user.send_query(f"{c.INFO} sent JOIN for {channel_name}.")

    def _cmd_part(self, server_dict, channel_name):
        try:
            if channel_name not in server_dict["channels"].keys():
                err_msg = f"{c.ERR} not in {channel_name} "
                err_msg += f"{server_dict['obj'].name}."
                self.user.send_query(err_msg)
                return
        except AttributeError:
            err_msg = f"{c.ERR} not in any channels in {server_dict['obj'].name}."
            self.user.send_query(err_msg)
            return

        server_dict["obj"].sock_ops.send_part(channel_name, "mom said no")
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

        for server in self.config.servers:
            msg += f"{c.LRED}{server.name}{c.RES}\n"
            msg += f"{c.WHITE}├ {c.LGREEN}admin:{c.RES} "

            if server.admin:
                msg += f"{server.admin.nick} ({server.admin.login})\n"
            else:
                msg += "no auth\n"

            msg += f"{c.WHITE}└ {c.LGREEN}channels:{c.RES}"

            if len(server.channel_obj) == 0:
                msg += " none\n"

            else:
                msg += "\n"
                for chan in server.channel_obj:
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

                    for user in chan.user_list:
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

        if len(self.user_args) == 0:
            self._usage()
            return

        self._dispatcher()
