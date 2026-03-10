import classes
import utils

def P_longest_path(game): #change name!!!
    """
    Estimates the probability that the AI wins the Longest Path bonus.
        N_consec_AI    = the longest simple path through the AI's claimed edges.
        N_consec_Opp   = the longest simple path through the opponent's claimed edges.
    """

    player1 = game.players[0]  # human
    player2 = game.players[1]  # AI

    n_consecutive_ai  = _longest_chain_for_player(game.graph, player2)
    n_consecutive_opp = _longest_chain_for_player(game.graph, player1)

    denominator = n_consecutive_ai + n_consecutive_opp
    if denominator == 0:
        return 0.0

    prob = (n_consecutive_ai / denominator)
    return max(0.0, min(1.0, prob))


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