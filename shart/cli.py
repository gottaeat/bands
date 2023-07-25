import argparse
import socket

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
        args = parser.parse_args()

        irc = IRC()

        irc.addr = (socket.gethostbyname(args.net), args.port)
        irc.channel = f"#{args.channel}"
        irc.botname = args.nick

        irc.connect()


def run():
    # pylint: disable=invalid-name
    c = CLI()
    c.run()
