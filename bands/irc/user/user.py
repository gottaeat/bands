import time

from bands.irc.util import wrap_bytes


# pylint: disable=too-few-public-methods,too-many-instance-attributes
class User:
    def __init__(self, server):
        self.server = server
        self.sock_ops = server.sock_ops

        self.nick = None
        self.login = None

        self.char_limit = None
        self.tarot_deck = None

        self.tstamp = None
        self.bad_pw_attempts = 0

    def send_query(self, msg):
        if "\n" in msg:
            for line in msg.split("\n"):
                if line != "":
                    if len(line.encode("utf-8")) > self.char_limit:
                        for item in wrap_bytes(line, self.char_limit):
                            self.sock_ops.send_privmsg(item, self.nick)
                            time.sleep(self.server.scroll_speed / 1000)
                    else:
                        self.sock_ops.send_privmsg(line, self.nick)
                        time.sleep(self.server.scroll_speed / 1000)
        else:
            if len(msg.encode("utf-8")) > self.char_limit:
                for item in wrap_bytes(msg, self.char_limit):
                    self.sock_ops.send_privmsg(item, self.nick)
                    time.sleep(self.server.scroll_speed / 1000)
            else:
                self.sock_ops.send_privmsg(msg, self.nick)
                time.sleep(self.server.scroll_speed / 1000)
