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
        msg += f"{c.WHITE}  └ {c.LGREEN}status{c.RES}"
        self.user.send_query(msg)

    def _status(self):
        msg = f"{c.INFO} active connections are:\n"

        for server in self.user.server.cli.servers:
            msg += f"└ {c.LRED}{server.name}{c.RES}\n"

            for chan in server.channel_obj:
                msg += f"  {c.WHITE}└ {c.LGREEN}{chan.name}{c.RES}\n"
                msg += f"    {c.WHITE}├ {c.YELLOW}topic  {c.RES}{chan.topic_msg}\n"
                msg += f"    {c.WHITE}├ {c.YELLOW}set by {c.RES}{chan.topic_user}\n"
                msg += f"    {c.WHITE}└ {c.YELLOW}date   {c.RES}{chan.topic_tstamp}\n"

        self.user.send_query(msg)

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

        self._usage()
