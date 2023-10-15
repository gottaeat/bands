from bands.util import drawbox
from bands.util import MIRCColors

# pylint: disable=invalid-name
c = MIRCColors()


# pylint: disable=too-few-public-methods
class Help:
    def __init__(self):
        pass

    @staticmethod
    def print(core):
        msg = f"{c.WHITE}help{c.RES}\n"
        msg += f"{c.WHITE}├ {c.LRED}usage {c.LBLUE}→{c.RES} {{?help|?bands|?tarot}}\n"
        msg += f"{c.WHITE}│       {c.LBLUE}→{c.RES} {{?piss [target]}}\n"
        msg += f"{c.WHITE}│       {c.LBLUE}→{c.RES} {{?advice {{target}}}}\n"
        msg += f"{c.WHITE}└ {c.LRED}src   {c.LBLUE}→{c.RES} https://github.com/gottaeat/bands"

        core.send_query(drawbox(msg, "thic"))
