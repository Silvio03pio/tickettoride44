import classes 
from classes import COLOURS

def P_colour(deck, colour):
    """
    Probability of drawing a specific colour from the remaining deck.
    Formula:
    P_colour(s) = (#[colour] - (#[colour] played + #[colour] in hands))
    / (#total   - (#played          + #in hands))
    """
    numerator   = deck.get_colour_count(colour)
    denominator = deck.get_card_count() # Remaining

    if denominator == 0:
        return 0.0  # deck is empty

    return numerator / denominator
#Returns {colour: probability} for all 8 colours.
def all_probabilities(deck):
    return {colour: P_colour(deck, colour) for colour in COLOURS}