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
        msg += f"{c.WHITE}├ {c.LGREEN}raw{c.RES}     [raw irc line]\n"
        msg += f"{c.WHITE}├ {c.LGREEN}rehash{c.RES}\n"
        msg += f"{c.WHITE}└ {c.LGREEN}status{c.RES}"
        # fmt: on
        self.user.send_query(msg)

    def _run(self):
        if self.user != self.user.server.admin:
            return

        if len(self.user_args) == 0:
            self._usage()
            return

        if self.user_args[0] == "connect":
            self._cmd_connect()
            return

        if self.user_args[0] == "dc":
            self._cmd_dc()
            return

        if self.user_args[0] == "join":
            self._cmd_join()
            return

        if self.user_args[0] == "part":
            self._cmd_part()
            return

        if self.user_args[0] == "raw":
            self._cmd_raw()
            return

        if self.user_args[0] == "rehash":
            self._cmd_rehash()
            return

        if self.user_args[0] == "status":
            self._cmd_status()
            return

        self._usage()

    # -- for _cmd_join() + _cmd_part() -- #
    def _get_objects(self, server_name):
        # server object
        for server in self.config.servers:
            if server.name == server_name:
                server_obj = server
                break

        try:
            if server_obj:
                # channel name: channel object
                sv_chans = {}
                for chan in server_obj.channel_obj:
                    sv_chans[chan.name] = chan
        except NameError:
            server_obj, sv_chans = False, False

        return server_obj, sv_chans

    # -- cmds -- #
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

    def _cmd_connect(self):
        server_names = self.user_args[1:]

        if len(server_names) == 0:
            self.user.send_query(f"{c.ERR} must supply at least one server.")
            return

        sv_list = []
        sv_objs = {}
        for server in self.config.servers:
            sv_list.append(server.name)
            sv_objs[server.name] = server

        for server in server_names:
            if server not in sv_list:
                self.user.send_query(f"{c.ERR} {server} does not exist.")
                return

            if sv_objs[server].socket.conn is not None:
                self.user.send_query(f"{c.ERR} already connected to {server}.")
                return

            self.user.send_query(f"{c.INFO} connecting to {server}")
            server_thread = Thread(target=sv_objs[server].run)
            server_thread.start()

    def _cmd_dc(self):
        server_names = self.user_args[1:]

        if len(server_names) == 0:
            self.user.send_query(f"{c.ERR} must supply at least one server.")
            return

        sv_list = []
        sv_objs = {}
        for server in self.config.servers:
            sv_list.append(server.name)
            sv_objs[server.name] = server

        for server in server_names:
            if server not in sv_list:
                self.user.send_query(f"{c.ERR} not connected to {server}.")
                return

            if self.user.server == sv_objs[server]:
                err_msg = f"{c.ERR} cannot disconnect from {server} "
                err_msg += "because it is the c2 server."
                self.user.send_query(err_msg)
                return

            if sv_objs[server].socket.conn is None:
                warn_msg = f"{c.WARN} {server} has no socket, just removing it "
                warn_msg += "from the server list."
                self.user.send_query(warn_msg)

                self.config.servers.remove(sv_objs[server])
            else:
                self.user.send_query(f"{c.INFO} disconnecting from {server}")
                sv_objs[server].stop()

    def _cmd_join(self):
        # take args
        if len(self.user_args) == 0:
            self.user.send_query(f"{c.ERR} must supply a server as the first arg.")
            return

        if len(self.user_args) == 1:
            self.user.send_query(f"{c.ERR} must supply at least one channel.")
            return

        server_name = self.user_args[1]
        channel_names = self.user_args[2:]

        # we handle only for #channels
        for channel_name in channel_names:
            if channel_name[0] != "#":
                self.user.send_query(f"{c.ERR} channels must start with a #.")
                return

        # get server object
        server_obj, sv_chans = self._get_objects(server_name)

        # no server object
        if not server_obj:
            self.user.send_query(f"{c.ERR} not connected to {server_name}.")
            return

        # check if channel already exists
        for channel_name in channel_names:
            if channel_name in sv_chans.keys():
                self.user.send_query(
                    f"{c.ERR} already in {channel_name} in {server_obj.name}."
                )
                return

        # join channel(s)
        for channel_name in channel_names:
            server_obj.sock_ops.send_join(channel_name)
            self.user.send_query(f"{c.INFO} sent JOIN for {channel_name}.")

    def _cmd_part(self):
        # take args
        server_name = self.user_args[1]
        channel_names = self.user_args[2:]

        if len(server_name) == 0:
            self.user.send_query(f"{c.ERR} must supply a server as the first arg.")
            return

        if len(channel_names) == 0:
            self.user.send_query(f"{c.ERR} must supply at least one channel.")
            return

        # get server object
        server_obj, sv_chans = self._get_objects(server_name)

        # no server object
        if not server_obj:
            self.user.send_query(f"{c.ERR} not connected to {server_name}.")
            return

        # check if channel already exists
        for channel_name in channel_names:
            if channel_name not in sv_chans.keys():
                self.user.send_query(
                    f"{c.ERR} not in {channel_name} in {server_obj.name}."
                )
                return

        # part from channel(s)
        for channel_name in channel_names:
            server_obj.sock_ops.send_part(channel_name, "mom said no")
            self.user.send_query(f"{c.INFO} parted from {channel_name}")

    def _cmd_raw(self):
        msg = " ".join(self.user_args[1:])

        if len(msg) == 0:
            self.user.send_query(f"{c.ERR} no message provided.")
            return

        self.user.sock_ops.send_raw(msg)

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
