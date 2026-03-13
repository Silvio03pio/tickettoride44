from collections import deque


def E_s(game, player):
    """
    Non-terminal evaluation function E(s) for a given player.

    Uses:
      - claimed_route_points from this module
      - P_L, P_R, C_c from models_P (imported lazily to avoid circular imports)
    """
    # Import here to avoid circular import at module load time
    import models_P

    # Sum of opponents' claimed route points
    Delta_C_T = 0
    for p in game.players:
        if p.name != player.name:
            Delta_C_T += claimed_route_points(game.graph, p)

    evaluation = (
        Delta_C_T
        + models_P.P_L(game, player) * game.longest_route_points
        + models_P.P_R(game, player) * player.route["points"]
        + models_P.C_c(game, player)
    )

    return evaluation


def points_for_path_length(length):
    """
    Returns the number of points awarded for claiming a route
    of a given length in Ticket to Ride Europe.
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


def claimed_route_points(graph, player):
    """
    Sums the points from all paths claimed by the given player.
    """
    total = 0
    for p in graph.get_paths():
        if p.get_occupation() == player.name:
            total += points_for_path_length(p.get_distance())
    return total


def get_node_by_name(graph, node_name):
    """
    Returns the node object with the given name from the graph.
    Returns None if not found.
    """
    for n in graph.get_nodes():
        if n.name == node_name:
            return n
    return None


def player_has_connection(graph, player, start_name, end_name):
    """
    Checks whether the player has a continuous claimed connection
    between start_name and end_name using only the player's paths.

    Uses BFS on the subgraph formed by the player's claimed routes.
    """
    start_node = get_node_by_name(graph, start_name)
    end_node = get_node_by_name(graph, end_name)

    if start_node is None or end_node is None:
        return False

    if start_node == end_node:
        return True

    visited = set()
    queue = deque([start_node])
    visited.add(start_node)

    while queue:
        current = queue.popleft()

        if current == end_node:
            return True

        for p in current.get_connected_paths():
            if p.get_occupation() != player.name:
                continue

            # Find the neighbor at the other end of the path
            if p.get_start_node() == current:
                neighbor = p.get_end_node()
            else:
                neighbor = p.get_start_node()

            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)

    return False


def destination_ticket_points(graph, player):
    """
    Returns the destination ticket score for the given player.

    If the destination is completed: +points
    If not completed: -points
    """
    if player.route is None:
        return 0

    start_name = player.route["start"]
    end_name = player.route["end"]
    points = player.route["points"]

    if player_has_connection(graph, player, start_name, end_name):
        return points
    return -points


def longest_path_bonus(graph, player, opponent, bonus_points=10):
    """
    Returns the longest path bonus for the given player.

    Assumption:
    - If player has strictly longer route chain: gets bonus_points
    - If opponent has strictly longer route chain: gets 0
    - If tied: both get bonus_points

    This follows the usual Ticket to Ride tie logic.
    If your assignment wants a different tie rule, change this function.
    """
    player_longest = P_L._longest_chain_for_player(graph, player)
    opponent_longest = P_L._longest_chain_for_player(graph, opponent)

    if player_longest > opponent_longest:
        return bonus_points
    elif player_longest < opponent_longest:
        return 0
    else:
        return bonus_points


def final_score(graph, player, opponent, longest_bonus=10):
    """
    Computes the final score of one player in a terminal state.

    Final score =
        points from claimed routes
        + destination ticket points
        + longest path bonus
    """
    route_score = claimed_route_points(graph, player)
    ticket_score = destination_ticket_points(graph, player)
    longest_score = longest_path_bonus(graph, player, opponent, longest_bonus)

    return route_score + ticket_score + longest_score


def utility(game, ai_player, opponent_player, longest_bonus=10):
    """
    Returns the terminal utility of the state from the AI perspective.

    U(s) = FinalScore(AI) - FinalScore(Opponent)
    """
    ai_score = final_score(game.graph, ai_player, opponent_player, longest_bonus)
    opp_score = final_score(game.graph, opponent_player, ai_player, longest_bonus)

    return ai_score - opp_score


def utility_breakdown(game, ai_player, opponent_player, longest_bonus=10):
    """
    Returns a detailed breakdown of all score components.
    Useful for debugging and testing.
    """
    ai_route = claimed_route_points(game.graph, ai_player)
    ai_ticket = destination_ticket_points(game.graph, ai_player)
    ai_longest = longest_path_bonus(game.graph, ai_player, opponent_player, longest_bonus)
    ai_total = ai_route + ai_ticket + ai_longest

    opp_route = claimed_route_points(game.graph, opponent_player)
    opp_ticket = destination_ticket_points(game.graph, opponent_player)
    opp_longest = longest_path_bonus(game.graph, opponent_player, ai_player, longest_bonus)
    opp_total = opp_route + opp_ticket + opp_longest

    return {
        "AI": {
            "route_points": ai_route,
            "ticket_points": ai_ticket,
            "longest_bonus": ai_longest,
            "total": ai_total
        },
        "Opponent": {
            "route_points": opp_route,
            "ticket_points": opp_ticket,
            "longest_bonus": opp_longest,
            "total": opp_total
        },
        "utility": ai_total - opp_total
    }