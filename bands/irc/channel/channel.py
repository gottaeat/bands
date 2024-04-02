import time

from bands.irc.util import wrap_bytes


# pylint: disable=too-few-public-methods,too-many-instance-attributes
class Channel:
    def __init__(self, server):
        self.server = server
        self.sock_ops = server.sock_ops

        # props
        self.name = None
        self.topic_msg = None
        self.topic_nick = None
        self.topic_login = None
        self.topic_tstamp = None

        self.user_list = []

        self.char_limit = None
        self.tstamp = None

    def send_query(self, msg):
        if "\n" in msg:
            for line in msg.split("\n"):
                if line != "":
                    if len(line.encode("utf-8")) > self.char_limit:
                        for item in wrap_bytes(line, self.char_limit):
                            self.sock_ops.send_privmsg(item, self.name)
                            time.sleep(self.server.scroll_speed / 1000)
                    else:
                        self.sock_ops.send_privmsg(line, self.name)
                        time.sleep(self.server.scroll_speed / 1000)
        else:
            if len(msg.encode("utf-8")) > self.char_limit:
                for item in wrap_bytes(msg, self.char_limit):
                    self.sock_ops.send_privmsg(item, self.name)
                    time.sleep(self.server.scroll_speed / 1000)
            else:
                self.sock_ops.send_privmsg(msg, self.name)
                time.sleep(self.server.scroll_speed / 1000)


class ChannelUser:
    def __init__(self):
        self.nick = None
        self.login = None

        # modes
        self.owner = None  # ~
        self.admin = None  # &
        self.op = None  # @
        self.hop = None  # %
        self.voiced = None  # +

        # context
        self.tarot_deck = None
        self.bjack = None
        self.chats = []

        # doots
        self.used_doot_tstamp = None
        self.got_dooted_tstamp = None
