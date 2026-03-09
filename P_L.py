import classes
import utils

def P_longest_path(game):
    """
    Estimates the probability that the AI wins the Longest Path bonus.
    Derives players from game.players, following the convention in main.py:
        game.players[0] = human (opponent)
        game.players[1] = AI
    where:
        N              = the diameter of the full board graph
                         constant representing the maximum conceivable chain.
        N_consec_AI    = the longest simple path through the AI's claimed edges.
        N_consec_Opp   = the longest simple path through the opponent's claimed edges.
    The first factor reflects the AI's relative lead over the opponent.
    The second factor scales that by how close the AI is to the theoretical maximum.
    Args:
        game : the classes.game object (provides game.graph and game.players)
    Returns:
        float in [0.0, 1.0]: estimated probability that the AI wins the bonus.
    """

    player1 = game.players[0]  # human
    player2 = game.players[1]  # AI

    N = utils.find_longest_possible_route(game.graph)[0]

    if N == 0:
        return 0.0

    n_consecutive_ai  = _longest_chain_for_player(game.graph, player2)
    n_consecutive_opp = _longest_chain_for_player(game.graph, player1)

    denominator = n_consecutive_ai + n_consecutive_opp
    if denominator == 0:
        return 0.0

    prob = (n_consecutive_ai / denominator) * (n_consecutive_ai / N)
    return max(0.0, min(1.0, prob))


def _longest_chain_for_player(full_graph, player):
    """
    Finds the longest simple path (in number of edges) across all connected
    components of the given player's claimed routes.

    Each connected component is only computed once: once a node has been
    assigned to a component it is skipped in subsequent iterations.

    Args:
        full_graph : the full classes.graph (all cities and all routes)
        player     : the player whose claimed routes we examine

    Returns:
        int: length of the longest simple path among all the player's components.
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
