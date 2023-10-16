import re
import time

from .util import strip_color
from .util import strip_user

from .modules.advice import Advice
from .modules.finance import Finance
from .modules.help import Help
from .modules.piss import Piss
from .modules.tarot import Tarot
from .modules.openai_handler import OpenAIHandler


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
                self.core.send_raw(f"{re.sub(r'PING', 'PONG', data)}\r\n")

            if not self.core.char_limit:
                if (
                    data.split()[1] == "JOIN"
                    and strip_user(data.split()[0]) == self.core.botname
                    and data.split()[2] == self.core.channel
                ):
                    self.core.char_limit = 512 - len(
                        f"{data.split()[0]} PRIVMSG {data.split()[2]} :\r\n".encode(
                            "utf-8"
                        )
                    )

            if data.split()[1] == "PRIVMSG" and data.split()[2] == self.core.channel:
                cmd = data.split()[3]

                user = strip_user(data.split()[0])
                user_args = " ".join(data.split()[4:])

                if cmd == ":?openai":
                    OpenAIHandler(self.core).print(user_args)

                if cmd == ":?bands":
                    Finance(self.core).print()

                if cmd == ":?help":
                    Help(self.core).print()

                if cmd == ":?piss":
                    Piss(self.core).print(user, user_args)

                if cmd == ":?tarot":
                    retval = Tarot(self.core).print(self.tarot_deck, user_args)

                    try:
                        if retval[0].__class__.__name__ == "TarotCard":
                            self.tarot_deck = retval
                    # pylint: disable=bare-except
                    except:
                        pass

                if cmd == ":?advice":
                    Advice().print(self.core, user, user_args)
