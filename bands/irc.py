import re
import time

from .util import strip_color

from .modules.advice import Advice
from .modules.finance import Finance
from .modules.help import Help
from .modules.piss import Piss
from .modules.tarot import Tarot


# pylint: disable=too-few-public-methods
class IRC:
    def __init__(self, core):
        self.core = core
        self.tarot_deck = None

    # pylint: disable=too-many-branches
    def run(self):
        while True:
            data = self.core.conn.recv(512)
            try:
                data = data.decode(encoding="UTF-8")
            except UnicodeDecodeError:
                try:
                    data = data.decode(encoding="latin-1")
                # pylint: disable=bare-except
                except:
                    continue
            # pylint: disable=broad-exception-caught
            except Exception:
                continue

            data = strip_color(data)

            if len(data) == 0:
                self.core.conn.close()
                raise ValueError("E: received nothing.")

            tstamp = time.strftime("%H:%M:%S")
            print(f"[{tstamp}] {data}", end="")

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
                    retval = Tarot().print(self.core, self.tarot_deck, user_args)

                    try:
                        if retval[0].__class__.__name__ == "TarotCard":
                            self.tarot_deck = retval
                    # pylint: disable=bare-except
                    except:
                        pass

                if cmd == ":?advice":
                    Advice().print(self.core, user, user_args)
