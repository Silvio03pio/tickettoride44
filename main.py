import classes
import utils
import P_R

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

if __name__ == "__main__":
    main()
