from bands.colors import MIRCColors

# pylint: disable=invalid-name
c = MIRCColors()


# pylint: disable=too-few-public-methods
class RCon:
    def __init__(self, user, user_args):
        self.user = user
        self.user_args = user_args

        self._run()

    def _usage(self):
        msg = f"{c.WHITE}├ {c.LGREEN}dc{c.RES}    [list of servers]\n"
        msg += f"{c.WHITE}├ {c.LGREEN}join{c.RES}  [server] [list of channels]\n"
        msg += f"{c.WHITE}├ {c.LGREEN}part{c.RES}  [server] [list of channels]\n"
        msg += f"{c.WHITE}├ {c.LGREEN}raw{c.RES}   [raw irc line]\n"
        msg += f"{c.WHITE}└ {c.LGREEN}status{c.RES}"
        self.user.send_query(msg)

    # pylint: disable=too-many-return-statements
    def _run(self):
        if self.user != self.user.server.admin:
            return

        if len(self.user_args) == 0:
            self._usage()
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

        if self.user_args[0] == "status":
            self._cmd_status()
            return

        self._usage()

    # -- for _cmd_join() + _cmd_part() -- #
    def _get_objects(self, server_name):
        # server object
        for server in self.user.server.cli.servers:
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
    def _cmd_dc(self):
        server_names = self.user_args[1:]

        if len(server_names) == 0:
            self.user.send_query(f"{c.ERR} must supply at least one server.")
            return

        sv_list = []
        sv_objs = {}
        for server in self.user.server.cli.servers:
            sv_list.append(server.name)
            sv_objs[server.name] = server

        for server in server_names:
            if server not in sv_list:
                self.user.send_query(f"{c.ERR} not connected to {server}.")
                return

            self.user.send_query(f"{c.INFO} disconnecting from {server}")
            sv_objs[server].stop()

    def _cmd_join(self):
        # take args
        server_name = self.user_args[1]
        channel_names = self.user_args[2:]

        if len(server_name) == 0:
            self.user.send_query(f"{c.ERR} must supply a server as the first arg.")
            return

        # we handle only for #channels
        if len(channel_names) == 0:
            self.user.send_query(f"{c.ERR} must supply at least one channel.")
            return

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
            # pylint: disable=consider-iterating-dictionary
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
            # pylint: disable=consider-iterating-dictionary
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

    # pylint: disable=too-many-branches
    def _cmd_status(self):
        msg = f"{c.INFO} active connections are:\n"

        for server in self.user.server.cli.servers:
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

                    if chan.topic_msg:
                        msg += (
                            f"    {c.WHITE}├ {c.YELLOW}topic  {c.RES}{chan.topic_msg}\n"
                        )
                        msg += (
                            f"    {c.WHITE}├ {c.YELLOW}set by {c.RES}{chan.topic_nick} "
                        )
                        msg += f"({chan.topic_login})\n"
                        msg += f"    {c.WHITE}├ {c.YELLOW}date   {c.RES}{chan.topic_tstamp}\n"
                    else:
                        msg += f"    {c.WHITE}├ {c.YELLOW}topic  {c.RES}not set\n"

                    msg += f"    {c.WHITE}└ {c.YELLOW}users: \n"

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
