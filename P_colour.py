import classes
import utils
from collections import Counter

COLOURS = ["red", "blue", "green", "yellow", "black", "white", "orange", "pink"]
CARDS_PER_COLOUR = 12

class deck:
    def __init__(self):
        """
        Full deck: 12 cards per colour (96 cards)
        Three piles are tracked:
            colour_counts  : the fixed total per colour (never changes)
            played_cards   : cards discarded after a route is claimed
            hand_cards     : cards currently held by both players combined
        The drawable deck = colour_counts - played_cards - hand_cards
        """
        self.total_cards = CARDS_PER_COLOUR * len(COLOURS)
        self.colour_counts = Counter({colour: CARDS_PER_COLOUR for colour in COLOURS})
        self.played_cards = Counter()        # discarded after claiming a route
        self.hand_cards = Counter()       # held by both players combined

    
    
    def draw_card(self, colour, count=1):
        """A player draws a card — it leaves the drawable deck, enters a hand."""
        self.hand_cards[colour] += count

    def play_card(self, colour, count=1):
        """A player claims a route — cards leave a hand and go to the discard pile."""
        self.hand_cards[colour]   -= count
        self.played_cards[colour] += count

    def get_colour_count(self, colour):
        """Cards of this colour still in the drawable deck."""
        return (
            self.colour_counts[colour]
            - self.played_cards[colour]
            - self.hand_cards[colour]
        )

    def get_total_remaining(self):
        """Total cards still in the drawable deck."""
        return (
            self.total_cards
            - sum(self.played_cards.values())
            - sum(self.hand_cards.values())
        )

    def P_colour(self, colour):
        """
        Probability of drawing a specific colour from the remaining deck.

        Formula:
            P_colour(s) = (#[colour] - (#[colour] played + #[colour] in hands))
                        / (#total   - (#played          + #in hands))

        Args:
            colour : one of the 8 colour strings

        Returns:
            float in [0.0, 1.0]
        """
        numerator   = self.get_colour_count(colour)
        denominator = self.get_total_remaining()

        if denominator == 0:
            return 0.0  # deck is empty

        return numerator / denominator

    def all_probabilities(self):
        """
        Returns a dict of {colour: P_colour(colour)} for all 8 colours.
        Useful for the CHANCE node in the Expectimax tree.
        """
        return {colour: self.P_colour(colour) for colour in COLOURS}