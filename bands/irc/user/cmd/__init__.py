from .auth import Auth
from .help import Help
from .rcon import RCon

CMDS = {
    ":?auth": Auth,
    ":?help": Help,
    ":?rcon": RCon,
}
