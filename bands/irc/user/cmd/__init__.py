from .help import Help
from .ping import Ping

# fmt: off
CMDS = {
    "help": {"class": Help, "usage": None,        "openai": False},
    "ping": {"class": Ping, "usage": "[no args]", "openai": False},
}
# fmt: on
