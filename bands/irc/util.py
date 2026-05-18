import re
import textwrap
import unicodedata

# fmt: off
# pylint: disable=anomalous-backslash-in-string
def strip_color(string):
    ansi_strip = re.compile(r"(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]")
    mirc_strip = re.compile("[\x02\x0F\x16\x1D\x1F]|\x03(\d{,2}(,\d{,2})?)?")

    return mirc_strip.sub("", ansi_strip.sub("", string))
# fmt: on


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

    users_n_modes = []
    for index, user in enumerate(user_nicks):
        mode = modes_split[index][1]
        if mode in ("v", "h", "o", "a", "q"):
            mode_dict = {
                user: {
                    "action": modes_split[index][0] == "+",
                    "mode": modes_split[index][1],
                }
            }
            users_n_modes.append(mode_dict)

    return users_n_modes
