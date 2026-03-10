# This file computes C_c(s), the card-based contribution term of the evaluation function.
# It estimates how valuable the current hand is with respect to currently claimable board actions.
# For each free path, it combines immediate route reward, colour draw probability, and cards in hand.

import P_colour

def points_for_path_length(length):
    """
    Returns the standard Ticket to Ride score for a claimed path length.
    """
    score_table = {
        1: 1,
        2: 2,
        3: 4,
        4: 7,
        5: 10,
        6: 15
    }
    return score_table.get(length, 0)


def count_colour_in_player_hand(player, colour):
    """
    Counts how many cards of a given colour are in the player's hand.

    Supported formats:
    - player.cards contains card objects with get_colour()
    - player.cards contains strings such as "blue", "red", etc.
    """
    count = 0

    for card in player.cards:
        if hasattr(card, "get_colour"):
            if card.get_colour() == colour:
                count += 1
        elif isinstance(card, str):
            if card == colour:
                count += 1

    return count


def available_actions(graph):
    """
    Returns all currently unclaimed paths.
    These are the available claim actions on the board.
    """
    actions = []

    for path in graph.get_paths():
        if path.get_occupation() is None:
            actions.append(path)

    return actions


def delta_C_a(path):
    """
    Returns the immediate score gain of claiming a path.
    """
    return points_for_path_length(path.get_distance())


def C_c(game, player):
    """
    Computes the C_c(s) term for the given player.

    Interpretation used:
    - available actions = all unclaimed paths
    - delta_C_a = score gained by claiming path a
    - % of action = probability of drawing the path colour from the deck
    - no. of trains in hand = number of cards of that colour currently in player's hand

    Formula implemented:
        C_c(s) = sum over available paths a of
                 delta_C_a * P_colour(colour_of_a) * cards_in_hand(colour_of_a)
    """
    total = 0.0

    for path in available_actions(game.graph):
        colour = path.get_colour()

        # Skip paths with undefined colours if ever present in the dataset
        if colour is None:
            continue

        # Probability of drawing this colour from the remaining deck
        # p_colour = game.deck.P_colour(colour) # old
        p_colour = P_colour.P_colour(game.deck, colour) # new

        # Number of cards of this colour currently in player's hand
        cards_in_hand = count_colour_in_player_hand(player, colour)

        # Immediate route reward if this path is claimed
        delta = delta_C_a(path)

        total += delta * p_colour * cards_in_hand

    return total

# right now in the main this is comment
def C_c_breakdown(game, player):
    """
    Returns a detailed breakdown of the C_c(s) contribution for debugging.
    """
    breakdown = []
    total = 0.0

    for path in available_actions(game.graph):
        colour = path.get_colour()

        if colour is None:
            continue

        # p_colour = game.deck.P_colour(colour) # old
        p_colour = P_colour.P_colour(game.deck, colour) # new
        cards_in_hand = count_colour_in_player_hand(player, colour)
        delta = delta_C_a(path)

        contribution = delta * p_colour * cards_in_hand
        total += contribution

        breakdown.append({
            "path_id": path.get_path_id(),
            "start": path.get_start_node().name,
            "end": path.get_end_node().name,
            "colour": colour,
            "distance": path.get_distance(),
            "delta_C_a": delta,
            "P_colour": p_colour,
            "cards_in_hand": cards_in_hand,
            "contribution": contribution
        })

    return {
        "total_C_c": total,
        "details": breakdown
    }