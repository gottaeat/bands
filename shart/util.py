import re
import unicodedata


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
