from bands.util import drawbox
from bands.util import MIRCColors

# pylint: disable=invalid-name
c = MIRCColors()


# pylint: disable=too-few-public-methods
class Piss:
    def __init__(self):
        pass

    @staticmethod
    def print(core, pisser, pissee):
        if len(str(pissee)) == 0:
            msg = f"{c.ORANGE}{pisser}{c.LBLUE}, "
            msg += f"{c.WHITE}on {c.YELLOW}who{c.WHITE}?{c.RES}"
            core.send_query(msg)
            return

        if len(str(pissee)) >= 30:
            msg = f"{c.ORANGE}{pisser}{c.LBLUE}, {c.YELLOW}pissee "
            msg += f"{c.LRED}is longer than 30 chats.{c.RES}"
            core.send_query(msg)
            return

        msg = f"     {c.WHITE}ë{c.RES} \n"
        msg += f"   {c.WHITE}.-║- {c.LBLUE}<- {c.ORANGE}{pisser}{c.RES} \n"
        msg += f"   {c.ORANGE}╭{c.LRED}╰{c.WHITE}\\{c.RES} \n"
        msg += f"   {c.YELLOW}┊{c.WHITE}/ \\{c.RES} \n"
        msg += f"   {c.YELLOW}┊{c.RES} \n"
        msg += f" {c.YELLOW}{pissee}{c.RES} \n"

        msg = drawbox(msg, "single")
        msg += f"{c.WHITE} → {c.ORANGE}{pissee} "
        msg += f"{c.WHITE}just got {c.YELLOW}pissed on "
        msg += f"{c.WHITE}by {c.ORANGE}{pisser}"
        msg += f"{c.WHITE}.{c.RES}"

        for line in msg.split("\n"):
            core.send_query(line)
