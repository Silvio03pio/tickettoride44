import classes
import utils

def P_R(game, player):

    start_node = utils.get_node_from_name(game.graph, player.route["start"])
    end_node = utils.get_node_from_name(game.graph, player.route["end"])
    start_graph = utils.build_graph_of_player_from_node(start_node, player)
    end_graph = utils.build_graph_of_player_from_node(end_node, player)

    shortest_connection = utils.find_shortest_connection_between_subgraphs(start_graph, end_graph)
    shortest_connection_length = shortest_connection["distance"]

    longest_possible = utils.find_longest_possible_route(game.graph)
    longest_possible_length = longest_possible[0]

    # Derived from formula
    speculated_odds_of_achieving = (longest_possible_length - 2*shortest_connection_length) / longest_possible_length

    return speculated_odds_of_achieving







