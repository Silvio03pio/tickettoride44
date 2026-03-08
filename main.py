import classes

def main():
    game_grid = classes.grid()
    game_grid.import_grid("ttr_europe_map_data.csv")

    player1 = classes.player("human")
    player2 = classes.player("AI")
    players = [player1, player2]

    game_instance = classes.game(game_grid, players)

    print("Game created successfully")
    print(f"Nodes: {len(game_grid.get_nodes())}")
    print(f"Paths: {len(game_grid.get_paths())}")
    print(f"Players: {[player.name for player in players]}")
    print(f"N: {game_grid.N}")
    print(f"Longest possible route: {game_grid.longest_possible_route}")

if __name__ == "__main__":
    main()
