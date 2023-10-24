import json
import os
import random
import re

from bands.colors import MIRCColors


# pylint: disable=invalid-name
c = MIRCColors()


# pylint: disable=too-few-public-methods
class TarotCard:
    def __init__(self, title, desc1, desc2):
        self.title = title
        self.desc1 = desc1
        self.desc2 = desc2


# pylint: disable=inconsistent-return-statements
class Tarot:
    DESC_FILE = (
        f"{os.path.dirname(os.path.realpath(__file__))}/../files/tarot_desc.json"
    )

    MISS_CLEO = "You are a Rastafarian speaking tarot reader mimicking American "
    MISS_CLEO += "television character Miss Cleo. The decks you read are laid out "
    MISS_CLEO += "in the context of the Celtic tarot spread. Your responses never "
    MISS_CLEO += 'include the word "Celtic". Your responses are always limited '
    MISS_CLEO += "to 400 characters. Your responses never include lists. You always "
    MISS_CLEO += "respond with a single paragraph."

    def __init__(self, channel):
        self.channel = channel

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

    def _interpret(self, deck):
        # stringify cards
        cards_str = ""
        for index, card in enumerate(deck):
            cards_str += f"{index+1}. {card.title}\n"

        # generate prompt
        prompt = "Read the following Celtic tarot deck where the cards are ordered "
        prompt += f"from 1 to 10:\n{cards_str}Respond as the American television "
        prompt += "character Miss Cleo. Your response must be in Rastafarian. "
        prompt += "The cards must be read in the context of the Celtic tarot "
        prompt += 'spread. Your response must not include the word "Celtic". '
        prompt += "Your response must be limited to 400 characters. Your response "
        prompt += "must be a paragraph and must not include lists. "

        # role defs
        message = [
            {"role": "system", "content": self.MISS_CLEO},
            {"role": "user", "content": prompt},
        ]

        # notify that we're generating the reading
        notif_msg = (
            f"{c.GREEN}[{c.LBLUE}I:{self.channel.server.ai.key_index}{c.GREEN}] "
        )
        notif_msg += f"{c.LGREEN}Generating reading:{c.RES}"
        self.channel.send_query(notif_msg)

        # call openai api
        try:
            response = self.channel.server.ai.openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=message,
                temperature=0.1,
                max_tokens=400,
                frequency_penalty=0.0,
                n=1,
            )
        # pylint: disable=broad-exception-caught
        except Exception as exc:
            err_log = f"create() failed:\n{exc}"

            for line in err_log.split("\n"):
                self.channel.server.logger.warning("%s", line)

            errmsg = f"{c.GREEN}[{c.LRED}E{c.GREEN}] "
            errmsg += f"{c.LRED}create() failed but your deck has been stored, "
            errmsg += f"you can retry using {c.LGREEN}?tarot last{c.LRED}.{c.RES}"

            self.channel.send_query(errmsg)
            return

        try:
            self.channel.send_query(response.choices[0]["message"]["content"])
        # pylint: disable=broad-exception-caught
        except Exception as exc:
            err_log = f"parsing response failed:\n{exc}"

            for line in err_log.split("\n"):
                self.channel.server.logger.warning("%s", line)

            errmsg = f"{c.GREEN}[{c.LRED}E{c.GREEN}] "
            errmsg += f"{c.LRED}Failed parsing response but your deck has been"
            errmsg += f"stored, you can retry using {c.LGREEN}?tarot last"
            errmsg += f"{c.LRED}.{c.RES}"

            self.channel.send_query(errmsg)

            return

    def _run(self):
        self._parse_json()
        self._gen_cards()
        self._pull()

    def print(self, user_args):
        # case 1: rerun the old deck and interpret it
        if len(user_args) != 0:
            if user_args == "last":
                if not self.channel.tarot_deck:
                    errmsg = f"{c.GREEN}[{c.LRED}E{c.GREEN}] "
                    errmsg += f"{c.LRED}no previous deck found.{c.RES}"
                    self.channel.send_query(errmsg)

                    return

                # print the cards in the last deck
                cards_msg = f"{c.GREEN}[{c.LBLUE}I{c.GREEN}] "
                cards_msg += f"{c.LGREEN}Cards in the last deck are{c.LBLUE}: "

                for index, card in enumerate(self.channel.tarot_deck):
                    cards_msg += f"{c.GREEN}[{c.LBLUE}#{index+1:02}{c.GREEN}] "
                    cards_msg += f"{c.WHITE}{card.title}{c.LBLUE}, "

                cards_msg = re.sub(r", $", f"{c.RES}", cards_msg)
                self.channel.send_query(cards_msg)

                # gen and send reading
                self._interpret(self.channel.tarot_deck)
                self.channel.server.ai.rotate_key()

                return

            errmsg = f"{c.GREEN}[{c.LRED}E{c.GREEN}] "
            errmsg += f"{c.LRED}only arg supported is {{last}}.{c.RES}"
            self.channel.send_query(errmsg)

            return

        # case 2: gen a deck and interpret it, and store it
        self._run()

        self.channel.tarot_deck = self.deck

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

        self.channel.send_query(finmsg)

        # gen and send reading
        self._interpret(self.deck)
        self.channel.server.ai.rotate_key()

        return
