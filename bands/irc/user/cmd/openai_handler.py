from bands.colors import MIRCColors

c = MIRCColors()


class OpenAIHandler:
    def __init__(self, user, user_args):
        self.user = user
        self.user_args = user_args

        self._run()

    def _load(self):
        keys = self.user_args[1:]
        if len(keys) == 0:
            errmsg = f"{c.ERR} must supply at least one key."
            self.user.send_query(errmsg)
            return

        for key in keys:
            if key[0:3] != "sk-":
                errmsg = f"{c.ERR} invalid OpenAI key formatting."
                self.user.send_query(errmsg)
                return

            if self.user.server.ai.keys:
                if len(self.user.server.ai.keys) != 0:
                    for stored_key in self.user.server.ai.keys:
                        if key == stored_key["key"]:
                            errmsg = f"{c.ERR} key already stored."
                            self.user.send_query(errmsg)
                            return
            else:
                self.user.server.ai.keys = []

            self.user.server.ai.keys.append({"key": key})

            msg = f"{c.INFO} stored key."
            self.user.send_query(msg)

        with self.user.server.ai.mutex:
            self.user.server.ai.key_index = -1
            self.user.server.ai.rotate_key()

    def _status(self):
        key_index = self.user.server.ai.key_index

        try:
            key_total = len(self.user.server.ai.keys)
        except TypeError:
            key_total = 0

        msg = f"{c.WHITE}├ {c.LRED}key index  {c.RES}{key_index}\n"
        msg += f"{c.WHITE}└ {c.LRED}total keys {c.RES}{key_total}"

        self.user.send_query(msg)

    def _usage(self):
        msg = f"{c.WHITE}├ {c.LGREEN}load{c.RES}   [list of keys]\n"
        msg += f"{c.WHITE}└ {c.LGREEN}status{c.RES}"

        self.user.send_query(msg)

    def _run(self):
        if self.user != self.user.server.admin:
            return

        if len(self.user_args) == 0:
            self._usage()
            return

        if self.user_args[0] == "load":
            self._load()
            return

        if self.user_args[0] == "status":
            self._status()
            return

        self._usage()
