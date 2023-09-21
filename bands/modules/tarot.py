import os
import json
import random


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
            finmsg += f"[#{index+1:02}] {val['desc']}\n"

        return finmsg

    def _run(self):
        self._gen_cards()
        self._pull()

        finmsg = ""
        for index, card in enumerate(self.deck):
            finmsg += f"[#{index+1:02}] | {card.title} | {card.desc1} | {card.desc2}\n"

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
