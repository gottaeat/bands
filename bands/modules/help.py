from bands.util import drawbox
from bands.util import MIRCColors

# pylint: disable=invalid-name
c = MIRCColors()


# pylint: disable=too-few-public-methods
class Help:
    def __init__(self, channel):
        self.channel = channel

    def print(self):
        msg = f"{c.WHITE}├ {c.LRED}usage{c.RES}\n"
        msg += f"{c.WHITE}│ ├ {c.LRED}channel{c.RES}\n"
        msg += f"{c.WHITE}│ │ ├ {c.LGREEN}?advice{c.RES} {{target}}\n"
        msg += f"{c.WHITE}│ │ ├ {c.LGREEN}?bands{c.RES}\n"
        msg += f"{c.WHITE}│ │ ├ {c.LGREEN}?help{c.RES}\n"
        msg += f"{c.WHITE}│ │ ├ {c.LGREEN}?piss{c.RES}   [target]\n"
        msg += f"{c.WHITE}│ │ └ {c.LGREEN}?tarot{c.RES}  {{last}}\n"
        msg += f"{c.WHITE}│ └ {c.LRED}user{c.RES}\n"
        msg += f"{c.WHITE}│   ├ {c.LGREEN}?auth{c.RES}   [secret]\n"
        msg += f"{c.WHITE}│   └ {c.LGREEN}?openai{c.RES} [reload|status]\n"
        msg += f"{c.WHITE}└ {c.LRED}src{c.RES}         https://github.com/gottaeat/bands"

        self.channel.send_query(msg)
