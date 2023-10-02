import re

from .modules.finance import Finance
from .modules.help import Help
from .modules.piss import Piss
from .modules.tarot import Tarot
from .modules.advice import Advice


# pylint: disable=too-few-public-methods
class IRC:
    def __init__(self, core):
        self.core = core

    def run(self):
        # pylint: disable=anomalous-backslash-in-string
        mirc_strip = re.compile("[\x02\x0F\x16\x1D\x1F]|\x03(\d{,2}(,\d{,2})?)?")

        while True:
            data = mirc_strip.sub(
                "", self.core.conn.recv(2048).decode(encoding="UTF-8")
            )
            if len(data) == 0:
                self.core.conn.close()
                raise ValueError("E: received nothing.")

            print(data, end="")

            if data.split()[0] == "PING":
                self.core.send_pong()

            if data.split()[1] == "PRIVMSG" and data.split()[2] == self.core.channel:
                cmd = data.split()[3]

                user = re.sub(r"^:|\![^!]*$", "", data.split()[0])
                user_args = " ".join(data.split()[4:])

                if cmd == ":?bands":
                    Finance().print(self.core)

                if cmd == ":?help":
                    Help().print(self.core)

                if cmd == ":?piss":
                    Piss().print(self.core, user, user_args)

                if cmd == ":?tarot":
                    Tarot().print(self.core, user, user_args)

                if cmd == ":?advice":
                    Advice().print(self.core, user, user_args)
