import argparse
import signal

from threading import Thread

from .ai import AI
from .config import ConfigYAML
from .server import Server


# pylint: disable=too-few-public-methods
class CLI:
    def __init__(self):
        self.config_file = None
        self.servers = []

    def _gen_args(self):
        parser_desc = "bands the IRC bot."
        parser_c_help = "Configuration YAML file."

        parser = argparse.ArgumentParser(description=parser_desc)
        parser.add_argument("-c", type=str, required=True, help=parser_c_help)
        args = parser.parse_args()

        self.config_file = args.c

    # pylint: disable=unused-argument
    def _signal_handler(self, signum, frame):
        signame = signal.Signals(signum).name

        if signame in ("SIGINT", "SIGTERM"):
            print(f"I: CLI() caught {signame}.")
            for server in self.servers:
                server.stop()

    def run(self):
        # signal handling to terminate threads peacefully
        # we don't exit here, the exit is done within Server(), otherwise the
        # recv loops throw I/O errors.
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # init argparse
        self._gen_args()

        # parse yaml and gen ServerConfig()'s
        config = ConfigYAML(self.config_file)
        config.parse_yaml()

        # init ai
        ai = AI()
        ai.keys = config.openai_keys
        ai.rotate_key()

        # pass the same ai instance to all servers
        for server in config.servers:
            server.ai = ai

        # start servers
        threads = []

        for server in config.servers:
            s = Server()

            msg = "Server() details\n"
            msg += "----------------\n"
            msg += f"ai          : {server.ai}\n"
            msg += f"name        : {server.name}\n"
            msg += f"address     : {server.address}\n"
            msg += f"port        : {server.port}\n"
            msg += f"botname     : {server.botname}\n"
            msg += f"channels    : {server.channels}\n"
            msg += f"secret      : {server.secret}\n"
            msg += f"tls         : {server.tls}\n"
            msg += f"verify_tls  : {server.verify_tls}\n"
            msg += f"scroll_speed: {server.scroll_speed}\n"
            print(msg)

            s.ai = server.ai
            s.name = server.name
            s.address = server.address
            s.port = server.port
            s.botname = server.botname
            s.channels = server.channels
            s.secret = server.secret
            s.tls = server.tls
            s.verify_tls = server.verify_tls
            s.scroll_speed = server.scroll_speed

            self.servers.append(s)

            p = Thread(target=s.run)
            threads.append(p)

        for thread in threads:
            thread.start()


def run():
    # pylint: disable=invalid-name
    c = CLI()
    c.run()
