import time

from .util import wrap_bytes


# pylint: disable=too-few-public-methods
class Channel:
    def __init__(self, server):
        self.server = server
        self.name = None

        self.char_limit = None

    def send_query(self, msg):
        if "\n" in msg:
            for line in msg.split("\n"):
                if line != "":
                    if len(line.encode("utf-8")) > self.char_limit:
                        for item in wrap_bytes(line, self.char_limit):
                            self.server.send_raw(f"PRIVMSG {self.name} :{item}")
                            time.sleep(self.server.scroll_speed)
                    else:
                        self.server.send_raw(f"PRIVMSG {self.name} :{line}")
        else:
            if len(msg.encode("utf-8")) > self.char_limit:
                for item in wrap_bytes(msg, self.char_limit):
                    self.server.send_raw(f"PRIVMSG {self.name} :{item}")
                    time.sleep(self.server.scroll_speed)
            else:
                self.server.send_raw(f"PRIVMSG {self.name} :{msg}")
