from .ai import AIQuery
from .blackjack import BlackJack
from .help import Help
from .point import Point
from .quote import Quote
from .tarot import Tarot

# fmt: off
CMDS = {
    "ai":    {"class": AIQuery,   "usage": "[query]",            "openai": True},
    "bj":    {"class": BlackJack, "usage": "{prefix}bj help",    "openai": False},
    "help":  {"class": Help,      "usage": None,                 "openai": False},
    "point": {"class": Point,     "usage": "{prefix}point help", "openai": False},
    "quote": {"class": Quote,     "usage": "{prefix}quote help", "openai": False},
    "tarot": {"class": Tarot,     "usage": "[question]",         "openai": True},
}
# fmt: on
