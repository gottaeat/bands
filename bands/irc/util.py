import re
import textwrap
import unicodedata

from bands.colors import MIRCColors


# pylint: disable=anomalous-backslash-in-string
def strip_color(string):
    ansi_strip = re.compile(r"(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]")
    mirc_strip = re.compile("[\x02\x0F\x16\x1D\x1F]|\x03(\d{,2}(,\d{,2})?)?")

    return mirc_strip.sub("", ansi_strip.sub("", string))


def chop_userline(userline):
    chop = userline.lstrip(":").split("!")
    return {"nick": chop[0], "login": chop[1]}


def unilen(string):
    string = strip_color(string)

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
    c = MIRCColors()

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
        string[i] = re.sub(r"^", f"{c.PINK}{chars['v']}{c.RES}", string[i])

    width = 0
    for i, _ in enumerate(string):
        if unilen(string[i]) > width:
            width = unilen(string[i])

    for i, _ in enumerate(string):
        string[i] = (
            f"{string[i]}{(width - unilen(string[i])) * ' '}{c.PINK}{chars['v']}{c.RES}"
        )

    string.insert(
        0, f"{c.PINK}{chars['1']}{chars['h'] * (width - 1)}{chars['2']}{c.RES}"
    )
    string.append(f"{c.PINK}{chars['3']}{chars['h'] * (width - 1)}{chars['4']}{c.RES}")

    fin = ""
    for i, line in enumerate(string):
        fin += line + "\n"

    return fin


def wrap_bytes(text, size):
    # pylint: disable=protected-access
    # not my shit i dont care
    words = textwrap.TextWrapper()._split_chunks(text)
    words.reverse()
    words = [w.encode() for w in words]

    lines = [b""]
    while words:
        word = words.pop(-1)
        if len(word) > size:
            words.append(word[size:])
            word = word[0:size]

        if len(lines[-1]) + len(word) <= size:
            lines[-1] += word
        else:
            lines.append(word)

    return [l.decode() for l in lines]


def streamline_modes(modes, user_nicks):
    operators = ("+", "-")

    fin, last, last_operator = "", "", ""
    for char in modes:
        if char in operators:
            fin += char
            last_operator = char
        else:
            if last not in operators:
                fin += f"{last_operator}{char}"
            else:
                fin += char

        last = char

    modes_split = [fin[i : i + 2] for i in range(0, len(fin), 2)]

    users_n_modes = {}
    for index, val in enumerate(user_nicks):
        users_n_modes[val] = {
            "action": modes_split[index][0] == "+",
            "mode": modes_split[index][1],
        }

    return users_n_modes
