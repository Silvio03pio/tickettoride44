
# 1. Implement place_trains(player, path, deck) or better claim_route(state, player_idx, path_id)
# 2. Implement draw_card(state, player_idx)
# 3. Implement legal_actions(state, player_idx)
# 4. Deprecate or thin out: player.place_trains, player.draw_card, player.claim_path so they become light wrappers (or remove once all call sites are updated)




# For testing purposes

def main():
    test_graph = graph()
    test_graph.import_graph("ttr_europe_map_data.csv")

    print("Nodes:")
    print(test_graph.get_nodes())

    print("\nPaths:")
    print(test_graph.get_paths()[:10])  # print first 10 paths

    print("\nN:")
    print(test_graph.N)