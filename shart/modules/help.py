from shart.util import drawbox


# pylint: disable=too-few-public-methods
class Help:
    def __init__(self):
        pass

    @staticmethod
    def print(core):
        msg = "help\n"
        msg += "├ usage: {?help|?islam|?piss [chatter]}\n"
        msg += "└ src  : https://github.com/gottaeat/shart\n"

        msg = drawbox(msg, "thic")

        for line in msg.split("\n"):
            core.send_query(line)
