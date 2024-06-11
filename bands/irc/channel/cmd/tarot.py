import json
import os
import random
import re

from bands.colors import MIRCColors
from bands.irc.util import unilen

c = MIRCColors()


class TarotCard:
    def __init__(self, title, desc1, desc2):
        self.title = title
        self.desc1 = desc1
        self.desc2 = desc2


class TarotDeck:
    def __init__(self):
        self.cards = []
        self.question = None


class Tarot:
    DESC_FILE = (
        f"{os.path.dirname(os.path.realpath(__file__))}/../../../static/tarot_desc.json"
    )

    # fmt: off
    MISS_CLEO  = "You are a tarot reader mimicking the American television "
    MISS_CLEO += "personality Miss Cleo. You always respond in Jamaican Patois "
    MISS_CLEO += "and never in standard English. The decks you read are laid "
    MISS_CLEO += "out in the context of the Celtic tarot spread. You always "
    MISS_CLEO += "perform the tarot reading in accordance and in relation to "
    MISS_CLEO += "the querent's question. Your responses never include the "
    MISS_CLEO += 'word "Celtic". Your responses are always limited to 400 '
    MISS_CLEO += "characters. Your responses never include lists. You always "
    MISS_CLEO += "respond with a single paragraph. You make references to the "
    MISS_CLEO += "querent's question in your reading."
    # fmt: on

    def __init__(self, channel, user, user_args):
        self.channel = channel
        self.user = user
        self.user_args = user_args

        self.openai_client = self.channel.server.config.openai_client

        self.deck = TarotDeck()
        self.tarot_data = None
        self.cards = []

        self._run()

    # - - tarot logic - - #
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

    def _gen_deck(self):
        self._parse_json()
        self._gen_cards()
        self._pull()

    # - - openai call - - #
    def _interpret(self, deck):
        # stringify cards
        cards_str = ""
        for index, card in enumerate(deck.cards):
            cards_str += f"{index+1}. {card.title}\n"

        # generate prompt
        # fmt: off
        prompt  = f'The querent\'s question is "{deck.question}". Read the '
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
        # fmt: on

        # role defs
        message = [
            {"role": "system", "content": self.MISS_CLEO},
            {"role": "user", "content": prompt},
        ]

        # notify that we're generating the reading
        msg = f"{c.INFO} generating reading for {c.WHITE}{self.user.nick}{c.RES}."
        self.channel.send_query(msg)

        # call openai api
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=message,
                temperature=0.1,
                max_tokens=400,
                frequency_penalty=0.0,
                n=1,
            )
        except Exception as exc:
            err_log = f"create() failed:\n{exc}"

            for line in err_log.split("\n"):
                self.channel.server.logger.warning("%s", line)

            err_msg = f"{c.ERR} create() failed but deck for "
            err_msg += f"{c.WHITE}{self.user.nick}{c.RES} has been stored, you "
            err_msg += f"can retry using {c.LGREEN}?tarot read last{c.RES}."
            self.channel.send_query(err_msg)

            return

        try:
            msg = f"{c.INFO} reading for {c.WHITE}{self.user.nick}{c.RES}:\n"
            msg += response.choices[0].message.content
            self.channel.send_query(msg)
        except Exception as exc:
            err_log = f"parsing response failed:\n{exc}"

            for line in err_log.split("\n"):
                self.channel.server.logger.warning("%s", line)

            err_msg = f"{c.ERR} failed parsing response but deck for "
            err_msg += f"{c.WHITE}{self.user.nick}{c.RES} has been stored, you "
            err_msg += f"can retry using {c.LGREEN}?tarot read last{c.RES}."
            self.channel.send_query(err_msg)

            return

    # - - util - - #
    def _pretty_cards(self):
        msg = f"{c.INFO} cards in the deck of "
        msg += f"{c.WHITE}{self.user.nick}{c.RES} are: "

        for index, card in enumerate(self.user.tarot_deck.cards):
            msg += f"{c.GREEN}[{c.LBLUE}#{index+1:02}{c.GREEN}] "
            msg += f"{c.WHITE}{card.title}{c.LBLUE}, "

        msg = re.sub(r", $", f"{c.RES}\n", msg)
        msg += f"{c.INFO} {c.WHITE}{self.user.nick}{c.RES}'s question was: "
        msg += f"{c.WHITE}{self.user.tarot_deck.question}{c.RES}"
        self.channel.send_query(msg)

    # - - cmd handling - - #
    def _cmd_help(self):
        # fmt: off
        msg  = f"{c.WHITE}├ {c.LGREEN}read{c.RES}\n"
        msg += f"{c.WHITE}│ ├ {c.YELLOW}q{c.RES}     take in a question, generate a deck, and feed them\n"
        msg += f"{c.WHITE}│ │{c.RES}       both to the openai api for a reading\n"
        msg += f"{c.WHITE}│ ├ {c.YELLOW}last{c.RES}  provide a reading for the last stored tarot deck\n"
        msg += f"{c.WHITE}│ │{c.RES}       and question for the user\n"
        msg += f"{c.WHITE}│ └ {c.YELLOW}addq{c.RES}  add a question to the user's deck or replace the\n"
        msg += f"{c.WHITE}│  {c.RES}       existing one\n"
        msg += f"{c.WHITE}└ {c.LGREEN}pull{c.RES}    simply create a deck for the user, print the cards\n"
        msg += "          in it with their descriptions, and the meaning of\n"
        msg += "          the order which they are pulled in."
        # fmt: on

        self.channel.send_query(msg)

    def _cmd_pull(self):
        self._gen_deck()
        self.user.tarot_deck = self.deck

        msg = f"{c.INFO} generated deck for {c.WHITE}{self.user.nick}{c.RES}:\n"
        for index, card in enumerate(self.user.tarot_deck.cards):
            order_title = self.tarot_data["card_order"][index]["title"]
            order_desc = self.tarot_data["card_order"][index]["desc"]

            msg += f"{c.GREEN}[{c.LBLUE}#{index+1:02}{c.GREEN}]"
            msg += f"[{c.LCYAN}{order_title}{c.GREEN}]{c.LBLUE}: "
            msg += f"{c.LGREY}{order_desc} {c.LBLUE}¦ "
            msg += f"{c.WHITE}{card.title} {c.LBLUE}¦ "
            msg += f"{c.LGREEN}{card.desc1} {c.LBLUE}¦ "
            msg += f"{c.LRED}{card.desc2}"
            msg += f"{c.RES}\n"

        self.channel.send_query(msg)

    def _cmd_read(self):
        if self.openai_client is None:
            self.channel.send_query(f"{c.ERR} no api key provided.")
            return

        if len(self.user_args) == 1:
            self.channel.send_query(f"{c.ERR} an argument is required.")
            return

        if self.user_args[1] == "addq" or self.user_args[1] == "last":
            if not self.user.tarot_deck:
                err_msg = f"{c.ERR} no previous deck found for "
                err_msg += f"{c.WHITE}{self.user.nick}{c.RES}."
                self.channel.send_query(err_msg)

                return

        # ?tarot read last
        if self.user_args[1] == "last":
            self._subcmd_read_last()
            return

        if self.user_args[1] == "q" or self.user_args[1] == "addq":
            if len(self.user_args) == 2:
                self.channel.send_query(f"{c.ERR} question is missing.")
                return

            user_Q = " ".join(self.user_args[2:])

            if unilen(user_Q) > 300:
                err_msg = f"{c.ERR} question wider than 300 characters."
                self.channel.send_query(err_msg)
                return

        # ?tarot read q <question>
        if self.user_args[1] == "q":
            self._subcmd_read_q(user_Q)
            return

        # ?tarot read addq <question>
        if self.user_args[1] == "addq":
            self._subcmd_read_addq(user_Q)
            return

    def _subcmd_read_last(self):
        if not self.user.tarot_deck.question:
            err_msg = f"{c.ERR} {c.WHITE}{self.user.nick}{c.RES}'s deck does not "
            err_msg += "have a question attached, run "
            err_msg += f"{c.LGREEN}?tarot read addq [question]{c.RES} to add a "
            err_msg += "question"
            self.channel.send_query(err_msg)

            return

        self._pretty_cards()
        self._interpret(self.user.tarot_deck)

    def _subcmd_read_q(self, user_Q):
        self._gen_deck()
        self.user.tarot_deck = self.deck
        self.user.tarot_deck.question = user_Q

        self._pretty_cards()
        self._interpret(self.user.tarot_deck)

    def _subcmd_read_addq(self, user_Q):
        self.user.tarot_deck.question = user_Q

        msg = f"{c.INFO} {c.WHITE}{self.user.nick}{c.RES}'s question has been saved."
        self.channel.send_query(msg)

    def _run(self):
        if len(self.user_args) == 0:
            self._cmd_help()
            return

        if self.user_args[0] == "pull":
            self._cmd_pull()
            return

        if self.user_args[0] == "read":
            self._cmd_read()
            return

        self._cmd_help()
