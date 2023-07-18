from .util import drawbox


# pylint: disable=too-few-public-methods
class Piss:
    def __init__(self):
        self.pisser = None
        self.pissee = None

    def printpiss(self):
        lolman = "     ë\n"
        lolman += f"   .-║- <- {self.pisser} \n"
        lolman += "   ╭╰\\\n"
        lolman += "   ┊/ \\\n"
        lolman += "   ┊\n"
        lolman += f" {self.pissee}\n"
        lolman = drawbox(lolman, "single")

        return f"{lolman}{self.pissee} just got pissed on by {self.pisser}."
