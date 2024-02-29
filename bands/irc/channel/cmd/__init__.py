from .advice import Advice
from .blackjack import BlackJack
from .doot import Doot
from .finance import Finance
from .help import Help
from .piss import Piss
from .quake import Quake
from .quote import Quote
from .tarot import Tarot

CMDS = {
    ":?advice": Advice,
    ":?bands": Finance,
    ":?bj": BlackJack,
    ":?doot": Doot,
    ":?help": Help,
    ":?piss": Piss,
    ":?quake": Quake,
    ":?quote": Quote,
    ":?tarot": Tarot,
}
