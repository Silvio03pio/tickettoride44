import classes
import utils
from collections import Counter

COLOURS = ["red", "blue", "green", "yellow", "black", "white", "orange", "pink"]
CARDS_PER_COLOUR = 12

class deck:
    def __init__(self):
        # Full deck: 12 cards per colour (96 cards)
        self.total_cards = CARDS_PER_COLOUR * len(COLOURS)
        self.colour_counts = Counter({colour: CARDS_PER_COLOUR for colour in COLOURS})
        self.played_cards = Counter()        # cards that have already been used
        self.hand_cards = Counter()       # cards held by AI players

    def play_card(self, colour, count=1):
        # Move cards from the deck to the played pile
        self.played_cards[colour] += count

    def ai_draw_card(self, colour, count=1):
        # Track a card drawn into an AI player's hand
        self.ai_hand_cards[colour] += count

    def ai_play_card(self, colour, count=1):
        # AI plays a card from hand and moves it to played pile.
        self.ai_hand_cards[colour] -= count
        self.played_cards[colour] += count

    def get_colour_count(self, colour):
        # Remaining cards of a colour still in the drawable deck. 
        # = total of that colour - (played + in AI hands)
        return (
            self.colour_counts[colour]
            - self.played_cards[colour]
            - self.ai_hand_cards[colour]
        )

    def get_total_remaining(self):
        # Total cards still in the drawable deck.
        # = total cards - (all played + all AI hand cards)
        total_played = sum(self.played_cards.values())
        total_ai = sum(self.ai_hand_cards.values())
        return self.total_cards - (total_played + total_ai)

    def P_colour(self, colour):
        # Probability of drawing a specific colour from the remaining deck
        #     P_colour(s) = (#[colour] cards - (#[colour] played cards + #[colour] cards in AI hands)) 
        #     / (#total cards - (#played cards + #cards in AI hands))
        numerator = self.get_colour_count(colour)
        denominator = self.get_total_remaining()

        if denominator == 0:
            return 0.0  # Deck is empty

        return numerator / denominator