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


def count_available_paths_per_colour(graph, colour):
    """
    Counts how many currently unclaimed paths exist for a given colour.
    """
    count = 0

    for path in graph.get_paths():
        if path.get_occupation() is None and path.get_colour() == colour:
            count += 1

    return count


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

    Normalized version:
        each contribution is divided by the number of currently available
        paths of the same colour, to keep the return value smaller and avoid
        overweighting colours that simply appear more often on the board.
    """
    total = 0.0

    for path in available_actions(game.graph):
        colour = path.get_colour()

        if colour is None:
            continue

        p_colour = P_colour.P_colour(game.deck, colour)
        cards_in_hand = count_colour_in_player_hand(player, colour)
        delta = delta_C_a(path)

        n_paths_same_colour = count_available_paths_per_colour(game.graph, colour)

        if n_paths_same_colour > 0:
            contribution = (delta * p_colour * cards_in_hand) / n_paths_same_colour
        else:
            contribution = 0

        total += contribution

    return total


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

        p_colour = P_colour.P_colour(game.deck, colour)
        cards_in_hand = count_colour_in_player_hand(player, colour)
        delta = delta_C_a(path)
        n_paths_same_colour = count_available_paths_per_colour(game.graph, colour)

        if n_paths_same_colour > 0:
            contribution = (delta * p_colour * cards_in_hand) / n_paths_same_colour
        else:
            contribution = 0

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
            "available_paths_same_colour": n_paths_same_colour,
            "contribution": contribution
        })

    return {
        "total_C_c": total,
        "details": breakdown
    }