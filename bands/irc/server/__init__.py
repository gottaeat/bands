from bands.colors import ANSIColors

from .socket_ops import SocketOps
from .client_init import ClientInit
from .final_loop import FinalLoop


ac = ANSIColors()


class Server:
    USER_NICKLIMIT = 30

    PONG_TIMEOUT = 60
    PING_INTERVAL = 120

    def __init__(self, socket):
        # args
        self.socket = socket

        # config
        self.name = None
        self.botname = None
        self.channels_init = []
        self.passwd = None
        self.allow_admin = None
        self.secret = None
        self.scroll_speed = None
        self.config = None

        # logger
        self.logger = None

        # socket_ops
        self.sock_ops = None

        # ircv3
        self.caps = []

        # channels + users
        self.channels = {}
        self.users = {}

        # admin
        self.admin = None
        self.bad_pw_attempts = 0

    def run(self):
        self.socket.connect()
        self.sock_ops = SocketOps(self)

        cl_init = ClientInit(self)
        cl_init.run()

        if not self.socket.halt:
            self.logger.info("%s", f"{ac.BYEL}--> {ac.BWHI}joining channels{ac.RES}")

            for channel in self.channels_init:
                self.sock_ops.send_join(channel)

            fin_loop = FinalLoop(self)
            fin_loop.run()

    def stop(self, going_down=False):
        self.logger.warning("%s", f"{ac.BYEL}--> {ac.BWHI}stopping{ac.RES}")
        self.socket.halt = True

        if self.socket.connected:
            try:
                self.sock_ops.send_quit("mom said no.")
            except:
                self.logger.warning("sending quit failed")

            self.socket.disconnect()

        if not going_down:
            self.logger.info("nuking self")
            del self.config.servers[self.name]  # pylint: disable=no-member
