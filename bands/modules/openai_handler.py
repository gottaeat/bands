import os
import json

from bands.util import drawbox
from bands.colors import MIRCColors

# pylint: disable=invalid-name
c = MIRCColors()


# pylint: disable=too-few-public-methods
class OpenAIHandler:
    def __init__(self, user, user_args):
        self.user = user
        self.user_args = user_args

        self._run()

    def _status(self):
        key_index = self.user.server.ai.key_index

        try:
            key_total = len(self.user.server.ai.keys)
        except TypeError:
            key_total = "none"

        msg = f"{c.WHITE}OpenAI Status{c.RES}\n"
        msg += f"{c.WHITE}├ {c.LRED}Current key index {c.LBLUE}→{c.RES} {key_index}\n"
        msg += f"{c.WHITE}└ {c.LRED}Total keys parsed {c.LBLUE}→{c.RES} {key_total}"

        self.user.send_query(drawbox(msg, "thic"))

    def _reload(self, keys_file):
        if not os.path.isfile(keys_file):
            errmsg = f"{c.GREEN}[{c.LRED}E{c.GREEN}] "
            errmsg += f"{c.LRED}{keys_file} is not a file.{c.RES}"
            self.user.send_query(errmsg)

            return

        try:
            with open(keys_file, "r", encoding="utf-8") as file:
                openai_keys = json.loads(file.read())["openai_keys"]
        # pylint: disable=broad-exception-caught
        except Exception as exc:
            errmsg = f"{c.GREEN}[{c.LRED}E{c.GREEN}] "
            errmsg += f"{c.LRED}parsing {keys_file} failed:{c.RES}\n"
            errmsg += f"{exc}"
            self.user.send_query(errmsg)

            return

        if len(openai_keys) == 0:
            errmsg = f"{c.GREEN}[{c.LRED}E{c.GREEN}] "
            errmsg += f"{c.LRED}{keys_file} has no keys.{c.RES}"
            self.user.send_query(errmsg)

            return

        for key in openai_keys:
            try:
                if key["key"][0:3] != "sk-":
                    errmsg = f"{c.GREEN}[{c.LRED}E{c.GREEN}] "
                    errmsg += f"{c.LRED}{key['key']} is not a valid OpenAI key.{c.RES}"
                    self.user.send_query(errmsg)

                    return
            except KeyError:
                # pylint: disable=raise-missing-from
                errmsg = f"{c.GREEN}[{c.LRED}E{c.GREEN}] "
                errmsg += f"{c.LRED}{keys_file} formatting is incorrect.{c.RES}"
                self.user.send_query(errmsg)

                return

        with self.user.server.ai.mutex:
            self.user.server.ai.key_index = -1
            self.user.server.ai.rotate_key()

        if not self.user.server.ai.keys:
            errmsg = f"{c.GREEN}[{c.LRED}E{c.GREEN}] "
            errmsg += f"{c.LRED}no keys found.{c.RES}"
            self.user.send_query(errmsg)

            return

        notif_msg = f"{c.GREEN}[{c.LBLUE}I{c.GREEN}] "
        notif_msg += f"{c.LGREEN}Success.{c.RES}"
        self.user.send_query(notif_msg)

        self._status()

    def _usage(self):
        errmsg = f"{c.GREEN}[{c.LRED}E{c.GREEN}] "
        errmsg += f"{c.LRED}usage: {{status|reload}}.{c.RES}"
        self.user.send_query(errmsg)

    def _run(self):
        if self.user.name != self.user.server.admin:
            errmsg = f"{c.GREEN}[{c.LRED}E{c.GREEN}] "
            errmsg += f"{c.LRED}user {self.user.name} is not authorized to run "
            errmsg += f"this command.{c.RES}"
            self.user.send_query(errmsg)

            return

        if len(self.user_args) == 0:
            self._usage()
            return

        if self.user_args[0] == "reload":
            try:
                keys_file = self.user_args[1]
            except IndexError:
                errmsg = f"{c.GREEN}[{c.LRED}E{c.GREEN}] "
                errmsg += f"{c.LRED}must supply a keys file.{c.RES}"
                self.user.send_query(errmsg)

                return

            self._reload(keys_file)
        elif self.user_args[0] == "status":
            self._status()
        else:
            self._usage()
