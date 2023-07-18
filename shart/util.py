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
    a = string.split("\n")
    if a[-1] == "":
        a = a[:-1]
    if a[0] == "":
        a = a[1:]
    for i in range(0, len(a)):
        a[i] = re.sub(r"^", chars["v"], a[i])
    width = 0
    for i in range(0, len(a)):
        if unilen(a[i]) > width:
            width = unilen(a[i])
    for i in range(0, len(a)):
        a[i] = f"{a[i]}{(width - unilen(a[i])) * ' '}{chars['v']}"
    a.insert(0, f"{chars['1']}{chars['h'] * (width - 1)}{chars['2']}")
    a.append(f"{chars['3']}{chars['h'] * (width - 1)}{chars['4']}")
    fin = ""
    finlen = len(a)
    for i in range(0, finlen):
        fin += a[i] + "\n"
    return fin
