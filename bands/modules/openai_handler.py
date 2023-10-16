import os

from bands.util import drawbox
from bands.util import MIRCColors

# pylint: disable=invalid-name
c = MIRCColors()

class OpenAIHandler:
    def __init__(self, core):
        self.core = core

    def _status(self):
        key_index = self.core.ai.key_index

        try:
            key_total = len(self.core.ai.keys)
        except TypeError:
            key_total = "none"

        msg = f"{c.WHITE}OpenAI Status{c.RES}\n"
        msg += f"{c.WHITE}├ {c.LRED}Current key index {c.LBLUE}→{c.RES} {key_index}\n"
        msg += f"{c.WHITE}└ {c.LRED}Total keys parsed {c.LBLUE}→{c.RES} {key_total}"

        self.core.send_query(drawbox(msg, "thic"))

    def _reload(self):
        self.core.ai.run()
        print(self.core.ai.openai.api_key)
        print(os.path.isfile(self.core.ai._OPENAI_KEYS_FILE))

        if not self.core.ai.keys:
            errmsg = f"{c.GREEN}[{c.LRED}E{c.GREEN}] "
            errmsg += f"{c.LRED}no keys found.{c.RES}"
            self.core.send_query(errmsg)
        else:
            notif_msg = f"{c.GREEN}[{c.LBLUE}I{c.GREEN}] "
            notif_msg += f"{c.LGREEN}Success.{c.RES}"
            self.core.send_query(notif_msg)

    def _usage(self):
        errmsg = f"{c.GREEN}[{c.LRED}E{c.GREEN}] "
        errmsg += f"{c.LRED}usage: {{status|reload}}.{c.RES}"
        self.core.send_query(errmsg)

    def print(self, user_args):
        if len(user_args) == 0 or len(user_args.split(" ")) > 1:
            self._usage()
            return

        if user_args == "reload":
            self._reload()
        elif user_args == "status":
            self._status()
        else:
            self._usage()
