import game

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
    """
    Returns a dict {colour: probability} for all standard colours.
    """
    from game import COLOURS  # imported here to avoid circular import at module load
    return {colour: P_colour(deck, colour) for colour in COLOURS}

def P_L(game, player):
    """
    Estimates the probability that the AI wins the Longest Path bonus.
        N_consec_AI    = the longest simple path through the AI's claimed edges.
        N_consec_Opp   = the longest simple path through the opponent's claimed edges.
    """

    # Old: only two players, only works for AI, assumes AI is players[0]
    """ 
    player1 = game.players[0]  # human
    player2 = game.players[1]  # AI

    n_consecutive_ai  = _longest_chain_for_player(game.graph, player2)
    n_consecutive_opp = _longest_chain_for_player(game.graph, player1)

    denominator = n_consecutive_ai + n_consecutive_opp
    """ 
    # New: any number of players, player is the input player not just players[0]
    n_consecutive = _longest_chain_for_player(game.graph, player)

    denominator = 0
    for p in game.players:
        denominator += _longest_chain_for_player(game.graph, p)
        print(f"{p}: denominator = {denominator}")

    if denominator == 0:
        return 0.0

    print(f"n_consecutive = {n_consecutive}")
    prob = (n_consecutive / denominator)
    return max(0.0, min(1.0, prob)) # prob will always be between 0 and 1 anyway?

def _longest_chain_for_player(full_graph, player):
    """
    Finds the longest simple path (in number of edges) across all connected
    components of the given player's claimed routes.
    Each connected component is only computed once: once a node has been
    assigned to a component it is skipped in subsequent iterations.
    """
    visited_nodes = set()
    longest = 0
    for node in full_graph.nodes:
        if node in visited_nodes:
            continue  # already part of a previously computed component

        component = game.build_graph_of_player_from_node(node, player)

        # Mark every node in this component so we don't reprocess it
        visited_nodes.update(component.nodes)

        if not component.paths:
            continue  # node has no claimed edges — nothing to measure

        chain_length = game.find_longest_possible_route(component)[0]
        if chain_length > longest:
            longest = chain_length

    return longest

def P_R(game, player):
    """
    Route-completion related term P_R(s) for the given player.
    """
    start_node = game.get_node_from_name(game.graph, player.route["start"])
    end_node = game.get_node_from_name(game.graph, player.route["end"])
    start_graph = game.build_graph_of_player_from_node(start_node, player)
    end_graph = game.build_graph_of_player_from_node(end_node, player)

    shortest_connection = game.find_shortest_connection_between_subgraphs(start_graph, end_graph)
    shortest_connection_length = shortest_connection["distance"]

    longest_possible = game.find_longest_possible_route(game.graph)
    longest_possible_length = longest_possible[0]

    # To match with word file
    N = longest_possible_length
    N_shortest = shortest_connection_length

    # ormula
    print(f"N = {N}, N_shortest = {N_shortest}")
    P_R = ((N - N_shortest) / N -0.5) * 2
    return P_R

