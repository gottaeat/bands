import argparse

from .core import Core
from .irc import IRC


# pylint: disable=too-few-public-methods
class CLI:
    def __init__(self):
        pass

    def run(self):
        parser = argparse.ArgumentParser(description="bands the IRC bot.")
        parser.add_argument("--nick", type=str, default="bands")
        parser.add_argument("--net", type=str, required=True)
        parser.add_argument("--port", type=int, required=True)
        parser.add_argument("--channel", type=str, required=True)
        parser.add_argument("--tls", action="store_true")
        parser.add_argument("--noverify", action="store_true")
        args = parser.parse_args()

        if args.noverify and not args.tls:
            raise ValueError("noverify requested without tls.")

        # init core
        core = Core()

        core.net = args.net
        core.port = args.port
        core.channel = f"#{args.channel}"
        core.botname = args.nick
        core.tls = args.tls
        core.noverify = args.noverify

        core.connect()

        # hand over to IRC
        irc = IRC(core)
        irc.run()


def run():
    # pylint: disable=invalid-name
    c = CLI()
    c.run()
