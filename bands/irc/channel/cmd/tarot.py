import random

from bands.colors import MIRCColors
from bands.irc.util import unilen

c = MIRCColors()


class Tarot:
    _CARD_NAMES = [
        "The Fool",
        "The Magician",
        "The High Priestess",
        "The Empress",
        "The Emperor",
        "The Hierophant",
        "The Lovers",
        "The Chariot",
        "Strength",
        "The Hermit",
        "Wheel of Fortune",
        "Justice",
        "The Hanged Man",
        "Death",
        "Temperance",
        "The Devil",
        "The Tower",
        "The Star",
        "The Moon",
        "The Sun",
        "Judgement",
        "The World",
        "Ace of Wands",
        "Two of Wands",
        "Three of Wands",
        "Four of Wands",
        "Five of Wands",
        "Six of Wands",
        "Seven of Wands",
        "Eight of Wands",
        "Nine of Wands",
        "Ten of Wands",
        "Page of Wands",
        "Knight of Wands",
        "Queen of Wands",
        "King of Wands",
        "Ace of Cups",
        "Two of Cups",
        "Three of Cups",
        "Four of Cups",
        "Five of Cups",
        "Six of Cups",
        "Seven of Cups",
        "Eight of Cups",
        "Nine of Cups",
        "Ten of Cups",
        "Page of Cups",
        "Knight of Cups",
        "Queen of Cups",
        "King of Cups",
        "Ace of Swords",
        "Two of Swords",
        "Three of Swords",
        "Four of Swords",
        "Five of Swords",
        "Six of Swords",
        "Seven of Swords",
        "Eight of Swords",
        "Nine of Swords",
        "Ten of Swords",
        "Page of Swords",
        "Knight of Swords",
        "Queen of Swords",
        "King of Swords",
        "Ace of Pentacles",
        "Two of Pentacles",
        "Three of Pentacles",
        "Four of Pentacles",
        "Five of Pentacles",
        "Six of Pentacles",
        "Seven of Pentacles",
        "Eight of Pentacles",
        "Nine of Pentacles",
        "Ten of Pentacles",
        "Page of Pentacles",
        "Knight of Pentacles",
        "Queen of Pentacles",
        "King of Pentacles",
    ]

    SYSTEM_PROMPT = (
        "You are a tarot reader. The decks you read are laid out in the context "
        "of the Celtic tarot spread. You always perform the tarot reading in "
        "accordance and in relation to the querent's question. Your responses "
        'never include the word "Celtic". Your responses are always limited to '
        "400 characters. Your responses never include lists. You always respond "
        "with a single paragraph. You make references to the querent's question "
        "in your reading."
    )

    def __init__(self, channel, user, user_args):
        self.channel = channel
        self.user = user
        self.user_args = user_args

        self.logger = self.channel.logger.getChild(self.__class__.__name__)

        self._run()

    def _read(self):
        question = " ".join(self.user_args)
        if unilen(question) > 300:
            return self.channel.send_query(
                f"{c.ERR} question wider than 300 characters."
            )

        cards = random.sample(self._CARD_NAMES, 10)
        cards_str = ", ".join(cards)

        # print deck
        separator = f"{c.LBLUE}, {c.LGREEN}"
        self.channel.send_query(
            f"{c.INFO} deck for {c.WHITE}{self.user.nick}{c.RES}: "
            f"{c.LGREEN}{separator.join(cards)}{c.RES}"
        )

        # query ai
        prompt = (
            f'The querent\'s question is "{question}". The pulled cards are: '
            f"{cards_str}. They are ordered from 1 to 10. Cards must be read "
            "in the context of the Celtic tarot spread. Your reponse must not "
            "include the word Celtic. Keep it short and do not include lists, "
            "emojis or markdown formatting. Reading must be done in accordance "
            "and in relation to the question."
        )

        try:
            reading = self.channel.server.config.ai.query(self.SYSTEM_PROMPT, prompt)
        except:
            self.logger.exception("query failed")
            return self.channel.send_query(f"{c.ERR} query failed.")

        if not reading:
            return self.channel.send_query(f"{c.ERR} no response.")

        # print reading
        self.channel.send_query(
            f"{c.INFO} reading for {c.WHITE}{self.user.nick}{c.RES}:\n" f"{reading}"
        )

    def _run(self):
        if not self.user_args:
            return self.channel.send_query(f"{c.ERR} you must ask a question.")

        self._read()
