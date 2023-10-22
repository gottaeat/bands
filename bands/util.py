import re
import textwrap
import unicodedata


# pylint: disable=too-few-public-methods
class MIRCColors:
    RES = "\x0f"
    BOLD = "\x02"

    WHITE = "\x0300"
    BLACK = "\x0301"
    BLUE = "\x0302"
    GREEN = "\x0303"
    LRED = "\x0304"
    BROWN = "\x0305"
    PURPLE = "\x0306"
    ORANGE = "\x0307"
    YELLOW = "\x0308"
    LGREEN = "\x0309"
    CYAN = "\x0310"
    LCYAN = "\x0311"
    LBLUE = "\x0312"
    PINK = "\x0313"
    GREY = "\x0314"
    LGREY = "\x0315"

    def __init__(self):
        pass


# pylint: disable=anomalous-backslash-in-string
def strip_color(string):
    ansi_strip = re.compile(r"(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]")
    mirc_strip = re.compile("[\x02\x0F\x16\x1D\x1F]|\x03(\d{,2}(,\d{,2})?)?")

    return mirc_strip.sub("", ansi_strip.sub("", string))


def strip_user(string):
    return re.sub(r"^:|\![^!]*$", "", string)


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
    # pylint: disable=invalid-name
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
        string[
            i
        ] = f"{string[i]}{(width - unilen(string[i])) * ' '}{c.PINK}{chars['v']}{c.RES}"

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


# pylint: disable=bare-except
def decode_data(data):
    try:
        data = strip_color(data.decode(encoding="UTF-8")).split("\r\n")
        for index, item in enumerate(data):
            if item == "":
                del data[index]
                break
            data[index] = f"{item}\r\n"

        return data
    except UnicodeDecodeError:
        try:
            data = strip_color(data.decode(encoding="latin-1")).split("\r\n")
            for index, item in enumerate(data):
                if item == "":
                    del data[index]

                data[index] = f"{item}\r\n"

            return data
        except:
            return None
    except:
        return None
