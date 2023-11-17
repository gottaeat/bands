import argparse
import logging
import signal

from threading import Thread

from .ai import AI
from .config import ConfigYAML
from .irc.server import Server
from .log import BandsFormatter
from .log import ShutdownHandler


# pylint: disable=too-few-public-methods,too-many-statements
class CLI:
    def __init__(self):
        self.debug = None
        self.config_file = None

        self.logger = None

        self.servers = []

    def _gen_args(self):
        parser_desc = "bands the IRC bot."
        parser_c_help = "Configuration YAML file."
        parser_d_help = "Enable debugging."

        parser = argparse.ArgumentParser(description=parser_desc)
        parser.add_argument("-c", type=str, required=True, help=parser_c_help)
        parser.add_argument("-d", dest="debug", action="store_true", help=parser_d_help)
        args = parser.parse_args()

        self.config_file = args.c
        self.debug = args.debug

    # pylint: disable=unused-argument
    def _signal_handler(self, signum, frame):
        signame = signal.Signals(signum).name

        if signame in ("SIGINT", "SIGTERM"):
            self.logger.info("caught %s exiting", signame)

            for server in self.servers:
                server.stop()

    def run(self):
        # gen logger for CMD() and ConfigYAML()
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG if self.debug else logging.INFO)

        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG if self.debug else logging.INFO)

        handler.setFormatter(BandsFormatter())

        self.logger.addHandler(handler)
        self.logger.addHandler(ShutdownHandler())

        self.logger.info("started bands")

        # signal handling to terminate threads peacefully
        # we don't exit here, the exit is done within Server(), otherwise the
        # recv loops throw I/O errors.
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # init argparse
        self._gen_args()

        # parse yaml and gen ServerConfig()'s
        config = ConfigYAML(self.config_file)
        config.logger = self.logger
        config.parse_yaml()

        # init ai
        ai = AI(self.debug)

        if config.openai:
            ai.keys = config.openai.keys

        ai.first_run()

        # init servers
        for server in config.servers:
            # pass the same ai instance to all servers
            server.ai = ai
            # pass in ourselves to allow for the Server() objects to be
            # manipulated via the auth'ed user
            server.cli = self

        # start servers
        self.logger.info("generating Server() instances")

        threads = []

        for server in config.servers:
            logger = logging.getLogger(server.name)

            logger.setLevel(logging.DEBUG if self.debug else logging.INFO)

            handler = logging.StreamHandler()
            handler.setLevel(logging.DEBUG if self.debug else logging.INFO)

            handler.setFormatter(BandsFormatter())

            logger.addHandler(handler)
            logger.addHandler(ShutdownHandler())

            s = Server()

            s.logger = logger

            msg = f"address     : {server.address}\n"
            msg += f"port        : {server.port}\n"
            msg += f"botname     : {server.botname}\n"
            msg += f"channels    : {server.channels}\n"
            msg += f"secret      : {server.secret}\n"
            msg += f"passwd      : {server.passwd}\n"
            msg += f"tls         : {server.tls}\n"
            msg += f"verify_tls  : {server.verify_tls}\n"
            msg += f"scroll_speed: {server.scroll_speed}"

            for line in msg.split("\n"):
                logger.info(line)

            s.ai = server.ai
            s.cli = server.cli
            s.name = server.name
            s.address = server.address
            s.port = server.port
            s.botname = server.botname
            s.channels = server.channels
            s.secret = server.secret
            s.passwd = server.passwd
            s.tls = server.tls
            s.verify_tls = server.verify_tls
            s.scroll_speed = server.scroll_speed

            self.servers.append(s)

            p = Thread(target=s.run)
            threads.append(p)

        self.logger.info("starting Server() threads")
        for thread in threads:
            thread.start()


def run():
    # pylint: disable=invalid-name
    c = CLI()
    c.run()
