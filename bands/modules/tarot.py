import os
import json
import random

from bands.util import MIRCColors


# pylint: disable=too-few-public-methods
class TarotCard:
    def __init__(self, title, desc1, desc2):
        self.title = title
        self.desc1 = desc1
        self.desc2 = desc2


class Tarot:
    DESC_FILE = (
        f"{os.path.dirname(os.path.realpath(__file__))}/../files/tarot_desc.json"
    )

    def __init__(self):
        # pylint: disable=invalid-name
        self.c = MIRCColors()

        self.cards = []
        self.deck = []
        self.tarot_data = None
        self.ordermsg = []

        self._parse_json()

    def _parse_json(self):
        with open(self.DESC_FILE, "r", encoding="utf-8") as desc_file:
            self.tarot_data = json.loads(desc_file.read())["tarot"]

    def _gen_cards(self):
        card_types = self.tarot_data["card_types"][0]

        for _, card_type in enumerate(card_types):
            for card in card_types[card_type]:
                self.cards.append(
                    TarotCard(
                        card["title"],
                        card["desc1"],
                        card["desc2"],
                    )
                )

    def _pull(self):
        random.shuffle(self.cards)

        for _ in range(0, 10):
            self.deck.append(self.cards.pop(random.randrange(len(self.cards))))

    def _explain(self):
        finmsg = ""
        for index, val in enumerate(self.tarot_data["card_order"]):
            finmsg += f"{self.c.GREEN}[{self.c.LBLUE}#{index+1:02}{self.c.GREEN}] "
            finmsg += f"{self.c.WHITE}{val['desc']} "
            finmsg += f"{self.c.RES}\n"

        return finmsg

    def _run(self):
        self._gen_cards()
        self._pull()

        finmsg = ""
        for index, card in enumerate(self.deck):
            finmsg += f"{self.c.GREEN}[{self.c.LBLUE}#{index+1:02}{self.c.GREEN}] "
            finmsg += f"{self.c.WHITE}{card.title} "
            finmsg += f"{self.c.LBLUE}{card.desc1} "
            finmsg += f"{self.c.LRED}{card.desc2}"
            finmsg += f"{self.c.RES}\n"

        return finmsg

    def print(self, core, user, user_args):
        if len(user_args) != 0 and user_args != "explain":
            core.send_query(f"{user}, usage: ?tarot {{explain}}")
            return

        if user_args == "explain":
            msg = self._explain()
        else:
            msg = self._run()

        for line in msg.split("\n"):
            core.send_query(line)
