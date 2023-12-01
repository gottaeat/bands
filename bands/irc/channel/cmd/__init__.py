from .advice import Advice
from .finance import Finance
from .help import Help
from .piss import Piss
from .tarot import Tarot

CMDS = {
    ":?advice": Advice,
    ":?bands": Finance,
    ":?help": Help,
    ":?piss": Piss,
    ":?tarot": Tarot,
}
