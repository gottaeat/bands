import os
import json
import random

from bands.util import MIRCColors

# pylint: disable=invalid-name
c = MIRCColors()


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
        self.cards = []
        self.deck = []
        self.tarot_data = None

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

    def _run(self):
        self._parse_json()
        self._gen_cards()
        self._pull()

        finmsg = ""

        for index, card in enumerate(self.deck):
            order_title = self.tarot_data["card_order"][index]["title"]
            order_desc = self.tarot_data["card_order"][index]["desc"]

            finmsg += f"{c.GREEN}[{c.LBLUE}#{index+1:02}{c.GREEN}]"
            finmsg += f"[{c.LCYAN}{order_title}{c.GREEN}]{c.LBLUE}: "
            finmsg += f"{c.LGREY}{order_desc} {c.LBLUE}¦ "
            finmsg += f"{c.WHITE}{card.title} {c.LBLUE}¦ "
            finmsg += f"{c.LGREEN}{card.desc1} {c.LBLUE}¦ "
            finmsg += f"{c.LRED}{card.desc2}"
            finmsg += f"{c.RES}\n"

        return finmsg

    def print(self, core):
        core.send_query_split(self._run())
