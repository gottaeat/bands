import copy
import random

from bands.colors import MIRCColors

c = MIRCColors()


# pylint: disable=too-few-public-methods
class Card:
    def __init__(self):
        self.face = None
        self.val = None
        self.suit = None


# pylint: disable=too-few-public-methods
class Shoe:
    _CARDS = [
        {"face": "A", "val": None},
        {"face": "2", "val": 2},
        {"face": "3", "val": 3},
        {"face": "4", "val": 4},
        {"face": "5", "val": 5},
        {"face": "6", "val": 6},
        {"face": "7", "val": 7},
        {"face": "8", "val": 8},
        {"face": "9", "val": 9},
        {"face": "10", "val": 10},
        {"face": "J", "val": 10},
        {"face": "Q", "val": 10},
        {"face": "K", "val": 10},
    ]

    _SUITS = [
        f"{c.WHITE}♠{c.RES}",
        f"{c.LRED}♥{c.RES}",
        f"{c.LRED}♦{c.RES}",
        f"{c.WHITE}♣{c.RES}",
    ]

    def __init__(self):
        self.cards = []

        self._cut()

    def _gen_deck(self):
        for suit in self._SUITS:
            for card in self._CARDS:
                pc = Card()
                pc.face = card["face"]
                pc.val = card["val"]
                pc.suit = suit

                self.cards.append(pc)

    def _cut(self):
        for _ in range(0, 2):
            self._gen_deck()

        random.shuffle(self.cards)


# pylint: disable=too-few-public-methods
class Game:
    def __init__(self):
        self.shoe = None

        self.bet = None

        self.dealer_hand = []
        self.player_hand = []

        self.dealer_val = 0
        self.player_val = 0


# pylint: disable=too-few-public-methods
class BlackJack:
    def __init__(self, channel, user, user_args):
        self.channel = channel
        self.user = user
        self.user_args = user_args

        self.game = None

        self._run()

    # -- card handling -- #
    def _deal(self, hand):
        pulled_card = self.game.shoe.cards.pop()
        hand.append(pulled_card)
        self._handle_aces(hand)

    # pylint: disable=too-many-branches
    def _handle_aces(self, hand):
        aces = []
        for card in hand:
            if card.face == "A":
                aces.append(card)

        # no aces
        if len(aces) == 0:
            return

        # shallow copy deck, keep card obj refs
        tmp_hand = copy.copy(hand)

        for card in aces:
            tmp_hand.remove(card)

        # count val w/o aces
        aceless_val = 0
        for card in tmp_hand:
            aceless_val += card.val

        # just one ace
        if len(aces) == 1:
            if 11 + aceless_val > 21:
                aces[0].val = 1
            else:
                aces[0].val = 11

        # multiple aces
        if len(aces) > 1:
            if (1 * (len(aces) - 1)) + 11 + aceless_val > 21:
                for ace in aces:
                    ace.val = 1
            else:
                aces[0].val = 11
                for ace in aces[1:]:
                    ace.val = 1

    def _player_hand_op(self):
        # calc val
        self.game.player_val = 0
        for card in self.game.player_hand:
            self.game.player_val += card.val

        # return str
        hand_str = f"{c.INFO} {self.user.nick}: "
        for card in self.game.player_hand:
            hand_str += f"{card.face}{card.suit} "

        hand_str = f"{hand_str.rstrip(' ')} ({self.game.player_val})"

        return hand_str

    def _dealer_hand_op(self, initial=False):
        # calc val
        self.game.dealer_val = 0
        for card in self.game.dealer_hand:
            self.game.dealer_val += card.val

        # return str
        if initial:
            hand_str = f"{c.INFO} dealer: "
            hand_str += f"{self.game.dealer_hand[0].face}"
            hand_str += f"{self.game.dealer_hand[0].suit} "
            hand_str += f"?? ({self.game.dealer_hand[0].val} + ?)"
        else:
            hand_str = f"{c.INFO} dealer's full hand: "
            for card in self.game.dealer_hand:
                hand_str += f"{card.face}{card.suit} "

            hand_str = f"{hand_str.rstrip(' ')} ({self.game.dealer_val})"

        return hand_str
    # -- card handling end -- #

    # -- game handling -- #
    def _initial_deal(self):
        self._deal(self.game.player_hand)
        self._deal(self.game.dealer_hand)
        self._deal(self.game.player_hand)
        self._deal(self.game.dealer_hand)

        # prompt
        self.channel.send_query(self._player_hand_op())
        self.channel.send_query(self._dealer_hand_op(initial=True))

        # check if blackjack, reveal dealer
        if self.game.player_val == 21:
            self.channel.send_query(f"{c.INFO} {self.user.nick} hit blackjack!")
            self._reveal_dealer()
        else:
            msg = f"{c.INFO} hit or stay? ({c.LGREEN}?bj hit {c.RES}| "
            msg += f"{c.LGREEN}?bj stay{c.RES})"
            self.channel.send_query(msg)

    def _reveal_dealer(self):
        self.channel.send_query(self._dealer_hand_op())

        # revealed deck costs less than 17, pull till we're above it
        if self.game.dealer_val < 17:
            msg = f"{c.INFO} dealer's hand costs less than 17, dealing."
            self.channel.send_query(msg)

            while self.game.dealer_val < 17:
                self._deal(self.game.dealer_hand)
                last_card = self.game.dealer_hand[-1]
                self.game.dealer_val += last_card.val

                msg = f"{c.INFO} dealer got {last_card.face}{last_card.suit} "
                msg += f"({last_card.val}), total: {self.game.dealer_val}"
                self.channel.send_query(msg)

        # game end
        self._handle_gameend()

    # pylint: disable=too-many-return-statements
    def _handle_gameend(self):
        # bust status
        dealer_bust = self.game.dealer_val > 21
        player_bust = self.game.player_val > 21

        if player_bust:
            # player + dealer bust
            if dealer_bust:
                msg = f"{c.INFO} both the dealer and {self.user.nick} busted!"
                self.channel.send_query(msg)
                self._handle_draw()
                return

            # player bust
            self._handle_player_loss()
            return

        # dealer bust
        if dealer_bust:
            self.channel.send_query(f"{c.INFO} dealer busted!")
            self._handle_player_win()
            return

        # no busts, handle bjack status
        dealer_bjack = self.game.dealer_val == 21
        player_bjack = self.game.player_val == 21

        if player_bjack:
            # both hit blackjack
            if dealer_bjack:
                msg = f"{c.INFO} the dealer and {self.user.nick} both hit blackjack!"
                self.channel.send_query(msg)
                self._handle_draw()
                return

            # player bjack
            self.channel.send_query(f"{c.INFO} {self.user.nick} hit blackjack!")
            self._handle_player_win()
            return

        # dealer bjack
        if dealer_bjack:
            self.channel.send_query(f"{c.INFO} dealer hit blackjack!")
            self._handle_player_loss()
            return

        # no blackjack, no bust
        # dealer costs more
        if self.game.dealer_val > self.game.player_val:
            self._handle_player_loss()
            return

        # dealer == player
        if self.game.dealer_val == self.game.player_val:
            msg = f"{c.INFO} the dealer and {self.user.nick}'s hands cost the same!"
            self.channel.send_query(msg)
            self._handle_draw()
            return

        # player costs more
        self._handle_player_win()
    # -- game handling end -- #

    # -- gameend states -- #
    # TODO: alter doots depending on result
    def _handle_draw(self):
        self.channel.send_query(f"{c.INFO} it's a draw.")
        self.user.bjack = None

    def _handle_player_win(self):
        self.channel.send_query(f"{c.INFO} {self.user.nick} wins.")
        self.user.bjack = None

    def _handle_player_loss(self):
        self.channel.send_query(f"{c.INFO} {self.user.nick} loses.")
        self.user.bjack = None
    # -- gameend states end -- #

    # -- cmd handling -- #
    def _run(self):
        if len(self.user_args) == 0:
            self._cmd_help()
            return

        if self.user_args[0] == "bet":
            self._cmd_bet()
            return

        if self.user_args[0] == "hit":
            self._cmd_hit()
            return

        if self.user_args[0] == "stay":
            self._cmd_stay()
            return

        if self.user_args[0] == "state":
            self._cmd_state()
            return

        self._cmd_help()

    def _cmd_help(self):
        msg = f"{c.LRED}usage{c.RES}\n"
        msg += f"{c.WHITE}├ {c.LGREEN}bet  {c.RES}[amount]\n"
        msg += f"{c.WHITE}├ {c.LGREEN}hit  {c.RES}\n"
        msg += f"{c.WHITE}├ {c.LGREEN}stay {c.RES}\n"
        msg += f"{c.WHITE}└ {c.LGREEN}state{c.RES}"

        self.channel.send_query(msg)

    def _cmd_bet(self):
        # already has a game running
        if self.user.bjack:
            err_msg = f"{c.ERR} {self.user.nick} already has a game running."
            self.channel.send_query(err_msg)
            return

        # no bet
        try:
            bet_amount = int(self.user_args[1])
        except IndexError:
            self.channel.send_query(f"{c.ERR} must provide a bet amount.")
            return
        except ValueError:
            self.channel.send_query(f"{c.ERR} we work only with and for money.")
            return

        # bet out of range
        if bet_amount < 1 or bet_amount > 1000:
            err_msg = f"{c.ERR} bet amount should be between 1 - 1000."
            self.channel.send_query(err_msg)
            return

        # create game
        self.user.bjack = Game()
        self.game = self.user.bjack
        self.game.bet = bet_amount

        # gen shoe, cut and deal
        self.game.shoe = Shoe()
        self._initial_deal()

    def _cmd_hit(self):
        # no game
        if not self.user.bjack:
            err_msg = f"{c.ERR} {self.user.nick} does not have a game running."
            self.channel.send_query(err_msg)
            return

        self.game = self.user.bjack

        self._deal(self.game.player_hand)
        self.channel.send_query(self._player_hand_op())
        self.channel.send_query(self._dealer_hand_op(initial=True))

        if self.game.player_val == 21 or self.game.player_val > 21:
            self._reveal_dealer()
        else:
            msg = f"{c.INFO} hit or stay? ({c.LGREEN}?bj hit {c.RES}| "
            msg += f"{c.LGREEN}?bj stay{c.RES})"
            self.channel.send_query(msg)

    def _cmd_stay(self):
        # no game
        if not self.user.bjack:
            err_msg = f"{c.ERR} {self.user.nick} does not have a game running."
            self.channel.send_query(err_msg)
            return

        self.game = self.user.bjack
        self._reveal_dealer()

    def _cmd_state(self):
        # no game
        if not self.user.bjack:
            err_msg = f"{c.ERR} {self.user.nick} does not have a game running."
            self.channel.send_query(err_msg)
            return

        self.game = self.user.bjack
        msg = f"{self._player_hand_op()}, bet: {c.WHITE}{self.game.bet}{c.RES}\n"
        msg += self._dealer_hand_op(initial=True)
        self.channel.send_query(msg)
    # -- cmd handling end -- #
