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
        msg = f"{c.WHITE}  ├ {c.LGREEN}dc{c.RES}     [server name]\n"
        msg += f"{c.WHITE}  ├ {c.LGREEN}raw{c.RES}    [raw irc line]\n"
        msg += f"{c.WHITE}  └ {c.LGREEN}status{c.RES}"
        self.user.send_query(msg)

    def _status(self):
        msg = f"{c.INFO} active connections are:\n"

        for server in self.user.server.cli.servers:
            msg += f"{c.WHITE}└ {c.LRED}{server.name}{c.RES}\n"

            for chan in server.channel_obj:
                msg += f"  {c.WHITE}└ {c.LGREEN}{chan.name}{c.RES}\n"
                msg += f"    {c.WHITE}├ {c.YELLOW}topic  {c.RES}{chan.topic_msg}\n"
                msg += f"    {c.WHITE}├ {c.YELLOW}set by {c.RES}{chan.topic_user}\n"
                msg += f"    {c.WHITE}├ {c.YELLOW}date   {c.RES}{chan.topic_tstamp}\n"
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

    def _raw(self):
        msg = " ".join(self.user_args[1:])

        if len(msg) == 0:
            errmsg = f"{c.ERR} no message provided."
            self.user.send_query(errmsg)
            return

        self.user.sock_ops.send_raw(msg)

    def _dc(self):
        server_names = self.user_args[1:]

        if len(server_names) == 0:
            errmsg = f"{c.ERR} must supply at least one server."
            self.user.send_query(errmsg)
            return

        sv_list = []
        sv_objs = {}
        for server in self.user.server.cli.servers:
            sv_list.append(server.name)
            sv_objs[server.name] = server

        for server in server_names:
            if server not in sv_list:
                errmsg = f"{c.ERR} not connected to {server}."
                self.user.send_query(errmsg)
                return

            msg = f"{c.INFO} disconnecting from {server}"
            self.user.send_query(msg)
            sv_objs[server].stop()

    def _run(self):
        if self.user.name != self.user.server.admin:
            errmsg = f"{c.ERR} not authorized."
            self.user.send_query(errmsg)
            return

        if len(self.user_args) == 0:
            self._usage()
            return

        if self.user_args[0] == "status":
            self._status()
            return

        if self.user_args[0] == "dc":
            self._dc()
            return

        if self.user_args[0] == "raw":
            self._raw()
            return

        self._usage()
