from dataclasses import dataclass
import random
from typing import List


RANKS = [str(n) for n in range(2, 11)] + ["J", "Q", "K", "A"]
SUITS = ["clubs", "diamonds", "hearts", "spades"]
RANK_VALUE = {r: (10 if r == "10" else (11 if r == "J" else (12 if r == "Q" else (13 if r == "K" else (14 if r == "A" else int(r)))))) for r in RANKS}


@dataclass
class Card:
    suit: str
    rank: str

    @property
    def value(self) -> int:
        return RANK_VALUE[self.rank]

    def to_dict(self):
        return {"suit": self.suit, "rank": self.rank}

    @classmethod
    def from_dict(cls, d):
        return cls(d["suit"], d["rank"])


class Deck:
    """Standard deck adjusted for Scoundrel rules.

    Removes Jokers and all red face cards (J,Q,K of hearts/diamonds) and red Aces.
    Remaining cards:
      - Clubs & Spades: all ranks (26 Monsters)
      - Diamonds: 2-10 (9 Weapons)
      - Hearts: 2-10 (9 Health potions)
    """

    def __init__(self, cards: List[Card] | None = None):
        if cards is not None:
            self.cards = cards[:]
        else:
            self.cards = self._build_standard_scoundrel_deck()

    def _build_standard_scoundrel_deck(self) -> List[Card]:
        cards = []
        for suit in SUITS:
            for rank in RANKS:
                # Skip Jokers (not represented) and remove red face cards and red aces
                if suit in ("hearts", "diamonds") and (rank in ("J", "Q", "K") or rank == "A"):
                    continue
                cards.append(Card(suit, rank))
        return cards

    def shuffle(self):
        random.shuffle(self.cards)

    def draw(self):
        if not self.cards:
            return None
        return self.cards.pop(0)  # draw from top (index 0)

    def draw_from_top(self, n: int):
        drawn = []
        for _ in range(n):
            c = self.draw()
            if c is None:
                break
            drawn.append(c)
        return drawn

    def add_to_bottom(self, cards: List[Card]):
        self.cards.extend(cards)

    def to_list(self):
        return [c.to_dict() for c in self.cards]

    @classmethod
    def from_list(cls, arr):
        return cls([Card.from_dict(d) for d in arr])

    def __len__(self):
        return len(self.cards)