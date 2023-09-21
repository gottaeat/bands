import re
import unicodedata


# pylint: disable=too-few-public-methods
class MIRCColors:
    RES = "\x0f"
    BOLD = "\x02"

    WHITE = "\x030"
    BLACK = "\x031"
    BLUE = "\x032"
    GREEN = "\x033"
    LRED = "\x034"
    BROWN = "\x035"
    PURPLE = "\x036"
    ORANGE = "\x037"
    YELLOW = "\x038"
    LGREEN = "\x039"
    CYAN = "\x0310"
    LCYAN = "\x0311"
    LBLUE = "\x0312"
    PINK = "\x0313"
    GREY = "\x0314"
    LGREY = "\x0315"

    def __init__(self):
        pass


def unilen(string):
    width = 0
    for i in string:
        if unicodedata.category(i)[0] in ("M", "C"):
            continue
        w = unicodedata.east_asian_width(i)
        if w in ("N", "Na", "H", "A"):
            width += 1
        else:
            width += 2
    return width


def drawbox(string, charset):
    if charset == "double":
        chars = {"1": "╔", "2": "╗", "3": "╚", "4": "╝", "h": "═", "v": "║"}
    elif charset == "single":
        chars = {"1": "┌", "2": "┐", "3": "└", "4": "┘", "h": "─", "v": "│"}
    elif charset == "thic":
        chars = {"1": "╔", "2": "╗", "3": "╚", "4": "╝", "h": "─", "v": "│"}
    else:
        chars = {"1": "+", "2": "+", "3": "+", "4": "+", "h": "-", "v": "|"}

    string = string.split("\n")

    if string[-1] == "":
        string = string[:-1]
    if string[0] == "":
        string = string[1:]

    for i, _ in enumerate(string):
        string[i] = re.sub(r"^", chars["v"], string[i])

    width = 0
    for i, _ in enumerate(string):
        if unilen(string[i]) > width:
            width = unilen(string[i])

    for i, _ in enumerate(string):
        string[i] = f"{string[i]}{(width - unilen(string[i])) * ' '}{chars['v']}"

    string.insert(0, f"{chars['1']}{chars['h'] * (width - 1)}{chars['2']}")
    string.append(f"{chars['3']}{chars['h'] * (width - 1)}{chars['4']}")

    fin = ""
    for i, line in enumerate(string):
        fin += line + "\n"

    return fin
