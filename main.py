import classes
import utils
import P_R

def main():
    game_grid = classes.grid()
    game_grid.import_grid("ttr_europe_map_data.csv")
    player1 = classes.player("human")
    player2 = classes.player("AI")
    players = [player1, player2]

    game = classes.game(game_grid, players)

    print("Game created successfully")
    print(f"Nodes: {len(game.grid.get_nodes())}")
    print(f"Paths: {len(game.grid.get_paths())}")
    print(f"Players: {[player.name for player in players]}")


    # Player test
    print("\n")
    start_node = game_grid.nodes[10]
    end_node = game_grid.nodes[30]
    print(start_node)
    print(end_node)
    player1.route = [start_node, end_node]

    game.grid.claim_path(game.grid.paths[0], player1)
    game.grid.claim_path(game.grid.paths[1], player1)
    game.grid.claim_path(game.grid.paths[2], player1)

    for path in game.grid.paths:
        if path.occupation == "human": print(path)

    Pr = P_R.P_R(game, player1)
    print(f"Speculated odds of achievign route: {Pr}")

if __name__ == "__main__":
    main()
