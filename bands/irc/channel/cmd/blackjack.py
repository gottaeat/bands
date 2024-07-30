import copy
import random

from bands.colors import MIRCColors

c = MIRCColors()


class Card:
    def __init__(self):
        self.face = None
        self.val = None
        self.suit = None


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


class Game:
    def __init__(self):
        self.shoe = None

        self.bet = None

        self.dealer_hand = []
        self.player_hand = []

        self.dealer_val = 0
        self.player_val = 0


class BlackJack:
    def __init__(self, channel, user, user_args):
        self.channel = channel
        self.user = user
        self.user_args = user_args

        self.doot = self.channel.server.config.doot

        self.game = None

        self._run()

    # -- card handling -- #
    def _deal(self, hand):
        pulled_card = self.game.shoe.cards.pop()
        hand.append(pulled_card)
        self._handle_aces(hand)

    def _handle_aces(self, hand):
        aces = []
        for card in hand:
            if card.face == "A":
                aces.append(card)

        # no aces
        if not aces:
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
            aces[0].val = 1 if 11 + aceless_val > 21 else 11

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

        return f"{hand_str.rstrip(' ')} ({self.game.player_val})"

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

    def _handle_gameend(self):
        # bust status
        dealer_bust = self.game.dealer_val > 21
        player_bust = self.game.player_val > 21

        if player_bust:
            # player + dealer bust
            if dealer_bust:
                msg = f"{c.INFO} both the dealer and {self.user.nick} busted!"
                self.channel.send_query(msg)
                return self._handle_payout("draw")

            # player bust
            return self._handle_payout("loss")

        # dealer bust
        if dealer_bust:
            self.channel.send_query(f"{c.INFO} dealer busted!")
            return self._handle_payout("win")

        # no busts, handle bjack status
        dealer_bjack = self.game.dealer_val == 21
        player_bjack = self.game.player_val == 21

        if player_bjack:
            # both hit blackjack
            if dealer_bjack:
                msg = f"{c.INFO} the dealer and {self.user.nick} both hit blackjack!"
                self.channel.send_query(msg)
                return self._handle_payout("draw")

            # player bjack
            self.channel.send_query(f"{c.INFO} {self.user.nick} hit blackjack!")
            return self._handle_payout("win")

        # dealer bjack
        if dealer_bjack:
            self.channel.send_query(f"{c.INFO} dealer hit blackjack!")
            return self._handle_payout("loss")

        # no blackjack, no bust
        # dealer costs more
        if self.game.dealer_val > self.game.player_val:
            return self._handle_payout("loss")

        # dealer == player
        if self.game.dealer_val == self.game.player_val:
            msg = f"{c.INFO} the dealer and {self.user.nick}'s hands cost the same!"
            self.channel.send_query(msg)
            return self._handle_payout("draw")

        # player costs more
        self._handle_payout("win")

    def _handle_payout(self, action):
        if action == "draw":
            doot_amount = self.game.bet
            msg = f"{c.INFO} it's a draw, returning your doots."
        elif action == "win":
            doot_amount = 2 * self.game.bet
            msg = f"{c.INFO} {self.user.nick} wins."
        elif action == "loss":
            doot_amount = 0
            msg = f"{c.INFO} {self.user.nick} loses."

        user_doots = self.doot.alter_doot(
            self.channel.server,
            self.user,
            doot_amount,  # pylint: disable=possibly-used-before-assignment
        )
        msg += f" (balance: {user_doots})"  # pylint: disable=undefined-variable

        self.channel.send_query(msg)
        self.user.bjack = None

    # -- cmd handling -- #
    def _run(self):
        if not self.user_args:
            return self._cmd_help()

        cmd = self.user_args[0]

        if cmd in ("bet", "hit", "stay", "state"):
            return getattr(self, f"_cmd_{cmd}")()

        self._cmd_help()

    def _cmd_help(self):
        msg = f"{c.WHITE}├ {c.LGREEN}bet  {c.RES} [amount]\n"
        msg += f"{c.WHITE}├ {c.LGREEN}hit  {c.RES}\n"
        msg += f"{c.WHITE}├ {c.LGREEN}stay {c.RES}\n"
        msg += f"{c.WHITE}└ {c.LGREEN}state{c.RES}"

        self.channel.send_query(msg)

    def _cmd_bet(self):
        # already has a game running
        if self.user.bjack:
            err_msg = f"{c.ERR} {self.user.nick} already has a game running."
            return self.channel.send_query(err_msg)

        # no bet
        try:
            bet_amount = int(self.user_args[1])
        except IndexError:
            return self.channel.send_query(f"{c.ERR} must provide a bet amount.")
        except ValueError:
            return self.channel.send_query(f"{c.ERR} we work only with and for money.")

        # bet out of range
        if bet_amount < 1 or bet_amount > 100:
            err_msg = f"{c.ERR} bet amount should be between 1 - 100."
            return self.channel.send_query(err_msg)

        # create game
        self.user.bjack = Game()
        self.game = self.user.bjack
        self.game.bet = bet_amount

        # deduct bet
        _ = self.doot.alter_doot(self.channel.server, self.user, -self.game.bet)
        msg = f"{c.INFO} {self.game.bet} doots have been deducted from your account!"
        self.channel.send_query(msg)

        # gen shoe, cut and deal
        self.game.shoe = Shoe()
        self._initial_deal()

    def _cmd_hit(self):
        # no game
        if not self.user.bjack:
            err_msg = f"{c.ERR} {self.user.nick} does not have a game running."
            return self.channel.send_query(err_msg)

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
            return self.channel.send_query(err_msg)

        self.game = self.user.bjack
        self._reveal_dealer()

    def _cmd_state(self):
        # no game
        if not self.user.bjack:
            err_msg = f"{c.ERR} {self.user.nick} does not have a game running."
            return self.channel.send_query(err_msg)

        self.game = self.user.bjack
        msg = f"{self._player_hand_op()}, bet: {c.WHITE}{self.game.bet}{c.RES}\n"
        msg += self._dealer_hand_op(initial=True)
        self.channel.send_query(msg)
