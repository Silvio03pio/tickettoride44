import classes
import utils

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

        component = utils.build_graph_of_player_from_node(node, player)

        # Mark every node in this component so we don't reprocess it
        visited_nodes.update(component.nodes)

        if not component.paths:
            continue  # node has no claimed edges — nothing to measure

        chain_length = utils.find_longest_possible_route(component)[0] 
        if chain_length > longest:
            longest = chain_length

    return longest