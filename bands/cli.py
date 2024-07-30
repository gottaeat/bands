import argparse
import logging
import signal

from threading import Thread

from .config import ConfigYAML
from .log import set_root_logger
from . import __version__ as pkg_version


class CLI:
    def __init__(self):
        self.debug = None
        self.config_file = None
        self.config = None
        self.logger = None

    def _gen_args(self):
        # fmt: off
        parser = argparse.ArgumentParser(description=f"bands the irc bot ver. {pkg_version}")
        parser.add_argument("-c", type=str, required=True, help="path to config yaml")
        parser.add_argument("-d", dest="debug", action="store_true", help="enable debug")
        # fmt: on

        args = parser.parse_args()

        self.config_file = args.c
        self.debug = args.debug

    def _signal_handler(self, signum, frame):  # pylint: disable=unused-argument
        signame = signal.Signals(signum).name

        if signame in ("SIGINT", "SIGTERM"):
            self.logger.info("caught %s, initiating graceful shutdown", signame)

            if self.config:
                self.config.halt = True

                for server in self.config.servers.values():
                    if server.socket:
                        server.stop(going_down=True)

    def _set_signal_handling(self):
        # signal handling to terminate threads peacefully
        # we don't exit here, the exit is done within Server(), otherwise the
        # recv loops throw I/O errors.
        self.logger.info("set signal handling")
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def run(self):
        # parse first to get self.debug
        self._gen_args()

        # create root logger and init our own
        set_root_logger(self.debug)
        self.logger = logging.getLogger("bands")

        # action
        self.logger.info("started bands ver %s", pkg_version)
        self._set_signal_handling()

        # parse yaml
        self.config = ConfigYAML(self.config_file, self.logger)
        self.config.run()

        # start servers
        if not self.config.halt:
            self.logger.info("starting Server() threads")
            for server in self.config.servers.values():
                server_thread = Thread(target=server.run)
                server_thread.start()


def run():
    c = CLI()
    c.run()
