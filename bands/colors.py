# pylint: disable=too-few-public-methods
class MIRCColors:
    RES = "\x0f"

    BOLD = "\x02"
    ULINE = "\x1f"
    BLINK = "\x06"  # weechat no likey

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

    INFO = f"{GREEN}[{LBLUE}I{GREEN}]{RES}"
    WARN = f"{GREEN}[{GREEN}W{GREEN}]{RES}"
    ERR = f"{GREEN}[{LRED}E{GREEN}]{RES}"

    def __init__(self):
        pass


# pylint: disable=too-few-public-methods
class ANSIColors:
    RES = "\033[0;39m"

    LBLK = "\033[0;30m"
    LRED = "\033[0;31m"
    LGRN = "\033[0;32m"
    LYEL = "\033[0;33m"
    LBLU = "\033[0;34m"
    LMGN = "\033[0;35m"
    LCYN = "\033[0;36m"
    LWHI = "\033[0;37m"

    BBLK = "\033[1;30m"
    BRED = "\033[1;31m"
    BGRN = "\033[1;32m"
    BYEL = "\033[1;33m"
    BBLU = "\033[1;34m"
    BMGN = "\033[1;35m"
    BCYN = "\033[1;36m"
    BWHI = "\033[1;37m"

    def __init__(self):
        pass
