
import state
import game
import rules
import models_P
import evaluation

def main(): 

    test_graph = game.graph()
    test_graph.import_graph("ttr_europe_map_data.csv")

    player1 = game.player("Saskia", "human")
    player2 = game.player("Silvio", "human")
    player3 = game.player("Edda", "human")
    player4 = game.player("Hakon", "human")
    # player5 = game.player("AI", "monte_carlo")
    players = [player1, player2, player3, player4]

    deck_of_trains = game.deck()
    deck_of_trains.shuffle()

    test_game = state.state(test_graph, players, deck_of_trains)


    while True:
        if test_game.current_player.end_game: break
        print(f"----------------------------- {test_game.current_round}: {test_game.current_player} -----------------------------")
        
        in_hand = test_game.current_player.cards
        print("\nCARDS IN HAND:")
        print(in_hand, "\n")

        all_possible = rules.get_all_possible_actions(test_game)
        print("ALL POSSIBLE:")
        print(all_possible, "\n")

        print("Number of trains left", test_game.current_player.trains)
 
        action = rules.decide_action(test_game)
        rules.apply_action(test_game, action)
    print("endgame")



    


if __name__ == "__main__":
    main()
