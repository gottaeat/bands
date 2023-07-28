import argparse

from .irc import IRC


# pylint: disable=too-few-public-methods
class CLI:
    def __init__(self):
        pass

    def run(self):
        parser = argparse.ArgumentParser(description="shart the IRC bot.")
        parser.add_argument("--nick", type=str, default="shart")
        parser.add_argument("--net", type=str, required=True)
        parser.add_argument("--port", type=int, required=True)
        parser.add_argument("--channel", type=str, required=True)
        parser.add_argument("--tls", action="store_true")
        parser.add_argument("--noverify", action="store_true")
        args = parser.parse_args()

        if args.noverify and not args.tls:
            raise ValueError("noverify requested without tls.")

        irc = IRC()

        irc.net = args.net
        irc.port = args.port
        irc.channel = f"#{args.channel}"
        irc.botname = args.nick

        irc.tls = args.tls
        irc.noverify = args.noverify

        irc.connect()


def run():
    # pylint: disable=invalid-name
    c = CLI()
    c.run()
