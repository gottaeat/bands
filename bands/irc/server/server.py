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
        self.channels = []
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

        # channels
        self.channel_obj = []

        # users
        self.users = []

        # admin
        self.admin = None
        self.bad_pw_attempts = 0

    # -- CLI() interactions -- #
    def run(self):
        self.socket.connect()
        self.sock_ops = SocketOps(self)

        cl_init = ClientInit(self)
        cl_init.run()

        if not self.socket.halt:
            self.logger.info("%s joining channels %s", f"{ac.BYEL}-->{ac.BWHI}", ac.RES)

            for channel in self.channels:
                self.sock_ops.send_join(channel)

            fin_loop = FinalLoop(self)
            fin_loop.run()

    def stop(self):
        self.logger.warning("%s stopping %s", f"{ac.BYEL}-->{ac.BWHI}", ac.RES)
        self.socket.halt = True

        if self.socket.connected:
            try:
                self.sock_ops.send_quit("quitting.")
            except:
                self.logger.warning("sending quit failed")

        self.socket.disconnect()

        self.logger.info("removing %s from servers list", self.name)
        # pylint: disable=no-member
        # ^ this is a pylint bug
        self.config.servers.remove(self)
