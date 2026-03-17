
import os

import game
import rules
import state

def main(): 

    test_graph = game.graph()
    here = os.path.dirname(__file__)
    map_path = os.path.join(here, "ttr_europe_map_data.csv")
    test_graph.import_graph(map_path)

    # Two-player simplified setup: one human, one AI (AI policy not implemented yet).
    player_human = game.player("Human", "human")
    player_ai = game.player("AI", "human")  # placeholder until search.py is implemented
    players = [player_ai, player_human]

    deck_of_trains = game.deck()
    deck_of_trains.shuffle()

    test_game = state.state(test_graph, players, deck_of_trains)
    # Give each player one destination ticket (currently a placeholder ticket generator).
    for p in test_game.players:
        p.give_route()


    while True:
        if rules.is_terminal(test_game):
            break
        print(f"----------------------------- {test_game.current_round}: {test_game.current_player} -----------------------------")
        
        in_hand = test_game.current_player.cards
        print("\nCARDS IN HAND:")
        print(in_hand, "\n")

        all_possible = rules.legal_actions(test_game)
        print("ALL POSSIBLE:")
        print(all_possible, "\n")

        print("Number of trains left", test_game.current_player.trains)
 
        chosen_action = rules.decide_action(test_game)
        rules.apply_action(test_game, chosen_action)

    print("Game ended (endgame terminal condition reached).")


if __name__ == "__main__":
    main()
