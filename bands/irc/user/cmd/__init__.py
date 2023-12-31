from .auth import Auth
from .help import Help
from .openai_handler import OpenAIHandler
from .rcon import RCon

CMDS = {
    ":?auth": Auth,
    ":?help": Help,
    ":?openai": OpenAIHandler,
    ":?rcon": RCon,
}
