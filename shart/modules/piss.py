from shart.util import drawbox


# pylint: disable=too-few-public-methods
class Piss:
    def __init__(self):
        pass

    @staticmethod
    def print(core, pisser, pissee):
        msg = "     ë\n"
        msg += f"   .-║- <- {pisser} \n"
        msg += "   ╭╰\\\n"
        msg += "   ┊/ \\\n"
        msg += "   ┊\n"
        msg += f" {pissee}\n"

        msg = drawbox(msg, "single")
        msg += f"{pissee} just got pissed on by {pisser}"

        for line in msg.split("\n"):
            core.send_query(line)
