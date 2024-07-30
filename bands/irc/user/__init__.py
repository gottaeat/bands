class User:
    def __init__(self, server):
        self.server = server
        self.sock_ops = server.sock_ops

        # props
        self.nick = None
        self.login = None

        self.char_limit = None
        self.logger = None

        self.tarot_deck = None

        self.tstamp = None
        self.bad_pw_attempts = 0

    def send_query(self, msg):
        self.sock_ops.send_query_hook(self.nick, self.char_limit, msg)
