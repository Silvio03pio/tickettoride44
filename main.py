import classes
import utils
import P_R
import P_L
import P_colour

def main():
    game_graph = classes.graph()
    game_graph.import_graph("ttr_europe_map_data.csv")
    player1 = classes.player("human")
    player2 = classes.player("AI")
    players = [player1, player2]

    game = classes.game(game_graph, players)

    print("Game created successfully")
    print(f"Nodes: {len(game.graph.get_nodes())}")
    print(f"Paths: {len(game.graph.get_paths())}")
    print(f"Players: {[player.name for player in players]}")


    # Player test
    print("\n")
    player1.give_route()
    print(player1.route["start"])
    print(player1.route["end"])

    game.graph.claim_path(game.graph.paths[0], player1)
    game.graph.claim_path(game.graph.paths[1], player1)
    game.graph.claim_path(game.graph.paths[2], player1)

    for path in game.graph.paths:
        if path.occupation == "human": print(path)

    Pr = P_R.P_R(game, player1)
    print(f"Speculated odds of achievign route: {Pr}")


    #Test for P_L
    game.graph.claim_path(game.graph.paths[10], player2)
    game.graph.claim_path(game.graph.paths[11], player2)
    game.players = [player1, player2]
    N = utils.find_longest_possible_route(game.graph)[0]
    ai_longest = P_L._longest_chain_for_player(game.graph, player2)
    opp_longest = P_L._longest_chain_for_player(game.graph, player1)
    Pl = P_L.P_longest_path(game)
    print(f"N (gesamt): {N}")
    print(f"AI longest: {ai_longest}")
    print(f"Human longest: {opp_longest}")
    print(f"Probability of winning longest path bonus: {Pl}")

if __name__ == "__main__":
    main()
