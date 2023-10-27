import json
import os
import random
import re

from bands.colors import MIRCColors
from bands.util import unilen

# pylint: disable=invalid-name
c = MIRCColors()


# pylint: disable=too-few-public-methods
class TarotCard:
    def __init__(self, title, desc1, desc2):
        self.title = title
        self.desc1 = desc1
        self.desc2 = desc2


class TarotDeck:
    def __init__(self):
        self.cards = []
        self.question = None


# pylint: disable=inconsistent-return-statements
class Tarot:
    DESC_FILE = (
        f"{os.path.dirname(os.path.realpath(__file__))}/../files/tarot_desc.json"
    )

    MISS_CLEO = "You are a Rastafarian speaking tarot reader mimicking American "
    MISS_CLEO += "television character Miss Cleo. The decks you read are laid out "
    MISS_CLEO += "in the context of the Celtic tarot spread. You always perform "
    MISS_CLEO += "the tarot reading in accordance and in relation to the querent's "
    MISS_CLEO += 'question. Your responses never include the word "Celtic". '
    MISS_CLEO += "Your responses are always limited to 400 characters. Your "
    MISS_CLEO += "responses never include lists. You always respond with a single "
    MISS_CLEO += 'paragraph. You always end your responses with "Call me now for '
    MISS_CLEO += "your free tarot readin'\"."

    def __init__(self, channel, user, user_args):
        self.channel = channel
        self.user = user
        self.user_args = user_args

        self.deck = TarotDeck()

        self.tarot_data = None

        self.cards = []

        self._run()

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
            self.deck.cards.append(self.cards.pop(random.randrange(len(self.cards))))

    def _interpret(self, deck):
        # stringify cards
        cards_str = ""
        for index, card in enumerate(deck.cards):
            cards_str += f"{index+1}. {card.title}\n"

        # get current key index
        with self.channel.server.ai.mutex:
            key_index = self.channel.server.ai.key_index

        # generate prompt
        prompt = f'The querent\'s question is "{deck.question}". Read the '
        prompt += "following Celtic tarot deck and answer the querent's "
        prompt += f"question, the cards are ordered from 1 to 10:\n{cards_str}"
        prompt += "Respond as the American television character Miss Cleo. "
        prompt += "Your response must be in Rastafarian. The cards must be "
        prompt += "read in the context of the Celtic tarot spread. Your "
        prompt += 'response must not include the word "Celtic". Your '
        prompt += "response must be limited to 400 characters. Your response "
        prompt += "must be a paragraph and must not include lists. The reading "
        prompt += "must be done in accordance and relation to the querent's "
        prompt += "question."

        # role defs
        message = [
            {"role": "system", "content": self.MISS_CLEO},
            {"role": "user", "content": prompt},
        ]

        # notify that we're generating the reading
        notif_msg = f"{c.GREEN}[{c.LBLUE}I:{key_index}{c.GREEN}] "
        notif_msg += f"{c.LGREEN}Generating reading for "
        notif_msg += f"{c.WHITE}{self.user.name}{c.LBLUE}.{c.RES}"

        self.channel.send_query(notif_msg)

        # rotate before call
        with self.channel.server.ai.mutex:
            self.channel.server.ai.rotate_key()

        # call openai api
        # the thread safety issue is only within the scope of the pure python
        # regarding the keys and key rotation logic, so we don't have to acquire
        # the lock here.
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
            notif_msg = f"{c.GREEN}[{c.LBLUE}I{c.GREEN}] "
            notif_msg += f"{c.LGREEN}Reading for "
            notif_msg += f"{c.WHITE}{self.user.name}{c.LBLUE}:{c.RES}\n"
            notif_msg += response.choices[0]["message"]["content"]

            self.channel.send_query(notif_msg)
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

    def _usage(self):
        errmsg = f"{c.GREEN}[{c.LRED}E{c.GREEN}] "
        errmsg += f"{c.LRED}an argument must be provided: "
        errmsg += f"{c.LGREEN}[q <question>|last].{c.RES}"
        self.channel.send_query(errmsg)

    # pylint: disable=too-many-statements
    def _run(self):
        if len(self.user_args) == 0:
            self._usage()
            return

        # case 1: rerun the old deck and interpret it
        if self.user_args[0] == "last":
            if not self.user.tarot_deck:
                errmsg = f"{c.GREEN}[{c.LRED}E{c.GREEN}] "
                errmsg += f"{c.LRED}no previous deck found for "
                errmsg += f"{self.user.name}.{c.RES}"
                self.channel.send_query(errmsg)

                return

            # print the cards in the last deck
            cards_msg = f"{c.GREEN}[{c.LBLUE}I{c.GREEN}] "
            cards_msg += f"{c.LGREEN}Cards in the last deck of "
            cards_msg += f"{c.WHITE}{self.user.name} {c.LGREEN}are{c.LBLUE}: "

            for index, card in enumerate(self.user.tarot_deck.cards):
                cards_msg += f"{c.GREEN}[{c.LBLUE}#{index+1:02}{c.GREEN}] "
                cards_msg += f"{c.WHITE}{card.title}{c.LBLUE}, "

            cards_msg = re.sub(r", $", f"{c.RES}\n", cards_msg)

            cards_msg += f"{c.GREEN}[{c.LBLUE}I{c.GREEN}] "
            cards_msg += f"{c.WHITE}{self.user.name}{c.LGREEN}'s question was"
            cards_msg += f"{c.LBLUE}: {c.WHITE}{self.user.tarot_deck.question}"
            cards_msg += f"{c.RES}"

            self.channel.send_query(cards_msg)

            # gen and send reading
            self._interpret(self.user.tarot_deck)

        # case 2: gen a deck and interpret it, and store it
        elif self.user_args[0] == "q":
            if len(self.user_args) == 1:
                errmsg = f"{c.GREEN}[{c.LRED}E{c.GREEN}] "
                errmsg += f"{c.LRED}question query is missing.{c.RES}"
                self.channel.send_query(errmsg)

                return

            user_Q = " ".join(self.user_args[1:])

            if unilen(user_Q) > 300:
                errmsg = f"{c.GREEN}[{c.LRED}E{c.GREEN}] "
                errmsg += f"{c.LRED}question query is longer than 300 "
                errmsg += f"characters.{c.RES}"
                self.channel.send_query(errmsg)

                return

            # set q
            self.deck.question = user_Q

            # set deck
            self._parse_json()
            self._gen_cards()
            self._pull()

            self.user.tarot_deck = self.deck

            # prompt
            finmsg = f"{c.GREEN}[{c.LBLUE}I{c.GREEN}] "
            finmsg += f"{c.LGREEN}Generating deck for "
            finmsg += f"{c.WHITE}{self.user.name}{c.LBLUE}:{c.RES}\n"

            for index, card in enumerate(self.deck.cards):
                order_title = self.tarot_data["card_order"][index]["title"]
                order_desc = self.tarot_data["card_order"][index]["desc"]

                finmsg += f"{c.GREEN}[{c.LBLUE}#{index+1:02}{c.GREEN}]"
                finmsg += f"[{c.LCYAN}{order_title}{c.GREEN}]{c.LBLUE}: "
                finmsg += f"{c.LGREY}{order_desc} {c.LBLUE}¦ "
                finmsg += f"{c.WHITE}{card.title} {c.LBLUE}¦ "
                finmsg += f"{c.LGREEN}{card.desc1} {c.LBLUE}¦ "
                finmsg += f"{c.LRED}{card.desc2}"
                finmsg += f"{c.RES}\n"

            finmsg += f"{c.GREEN}[{c.LBLUE}I{c.GREEN}] "
            finmsg += f"{c.WHITE}{self.user.name}{c.LGREEN}'s question was"
            finmsg += f"{c.LBLUE}: {c.WHITE}{self.deck.question}"
            finmsg += f"{c.RES}"

            self.channel.send_query(finmsg)

            # gen and send reading
            self._interpret(self.deck)
        else:
            self._usage()
            return
