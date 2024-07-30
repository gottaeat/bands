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

        self.users = {}

        self.char_limit = None
        self.logger = None
        self.cmd_tstamp = None
        self.hook_tstamp = None

    def send_query(self, msg):
        self.sock_ops.send_query_hook(self.name, self.char_limit, msg)


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
