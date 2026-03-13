
import state
import game
import rules
import models_P
import evaluation

def main(): 

    test_graph = game.graph()
    test_graph.import_graph("ttr_europe_map_data.csv")

    player1 = game.player("AI")
    player2 = game.player("Human")
    players = [player1, player2]

    deck_of_trains = game.deck()
    deck_of_trains.shuffle()

    test_game = state.state(test_graph, players, deck_of_trains)



    


if __name__ == "__main__":
    main()
