import argparse
import signal

from threading import Thread

from .colors import ANSIColors
from .config import ConfigYAML
from .log import set_logger

ac = ANSIColors()


class CLI:
    def __init__(self):
        self.debug = None
        self.config_file = None
        self.config = None
        self.logger = None

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

            for server in self.config.servers:
                server.stop()

    def _set_signal_handling(self):
        # signal handling to terminate threads peacefully
        # we don't exit here, the exit is done within Server(), otherwise the
        # recv loops throw I/O errors.
        self.logger.info("set signal handling")
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _gen_prompt(self, server):
        # fmt: off
        msg = f"{ac.BWHI}{server.name}{ac.RES}\n"
        msg += f"{ac.BWHI}├ {ac.BRED}socket{ac.RES}\n"
        msg += f"{ac.BWHI}│ ├ {ac.BGRN}address      {ac.RES}{server.socket.address}{ac.RES}\n"
        msg += f"{ac.BWHI}│ ├ {ac.BGRN}port         {ac.RES}{server.socket.port}{ac.RES}\n"
        msg += f"{ac.BWHI}│ ├ {ac.BGRN}tls          {ac.RES}{server.socket.tls}{ac.RES}\n"
        msg += f"{ac.BWHI}│ └ {ac.BGRN}verify_tls   {ac.RES}{server.socket.verify_tls}{ac.RES}\n"
        msg += f"{ac.BWHI}└ {ac.BRED}server{ac.RES}\n"
        msg += f"{ac.BWHI}  ├ {ac.BGRN}botname      {ac.RES}{server.botname}{ac.RES}\n"
        msg += f"{ac.BWHI}  ├ {ac.BGRN}channels     {ac.RES}{server.channels}{ac.RES}\n"
        msg += f"{ac.BWHI}  ├ {ac.BGRN}allow_admin  {ac.RES}{server.allow_admin}{ac.RES}\n"
        msg += f"{ac.BWHI}  ├ {ac.BGRN}secret       {ac.RES}{server.secret}{ac.RES}\n"
        msg += f"{ac.BWHI}  ├ {ac.BGRN}passwd       {ac.RES}{server.passwd}{ac.RES}\n"
        msg += f"{ac.BWHI}  └ {ac.BGRN}scroll_speed {ac.RES}{server.scroll_speed}{ac.RES}"
        # fmt: on

        for line in msg.split("\n"):
            server.logger.info(line)

    def run(self):
        self.logger = set_logger("bands", self.debug)
        self.logger.info("started")

        self._set_signal_handling()
        self._gen_args()

        # parse yaml
        self.config = ConfigYAML(self.config_file, self.logger)
        self.config.run()

        # start servers
        self.logger.info("starting Server() threads")
        for server in self.config.servers:
            self._gen_prompt(server)

            server_thread = Thread(target=server.run)
            server_thread.start()


def run():
    c = CLI()
    c.run()
