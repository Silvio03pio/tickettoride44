import classes
import utils
import P_R
import P_L
import P_colour
import U_s
import C_c

def main():
    game_graph = classes.graph()
    game_graph.import_graph("ttr_europe_map_data.csv")
    player1 = classes.player("human")
    player2 = classes.player("AI")
    players = [player1, player2]

    game = classes.game(game_graph, players)
    game.deck = P_colour.deck()

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
    print("\n--- P_LONGEST PATH TEST ---")
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


    # P_colour test
    print("\n--- P_COLOUR TEST ---")
    game.deck.draw_card("blue")    # draw 1 blue
    game.deck.draw_card("blue")    # draw 1 blue
    game.deck.draw_card("blue")    # draw 1 blue
    game.deck.draw_card("blue")    # draw 1 blue  → 4 blue on the hand
    game.deck.draw_card("red")     # draw 1 red
    game.deck.draw_card("red")     # draw 1 red   → 2 red on the hand
    game.deck.play_card("blue", 3) # claims a route with three blue → 1 blue in hand
    
    print(f"\nP(blue) = {game.deck.P_colour('blue'):.4f}")
    print(f"P(red)  = {game.deck.P_colour('red'):.4f}")
    print(f"All colours: {game.deck.all_probabilities()}")

        
    # Utility U(s) test
    breakdown = U_s.utility_breakdown(game, player2, player1)

    print("\n--- TERMINAL UTILITY BREAKDOWN ---")
    print("AI route points:", breakdown["AI"]["route_points"])
    print("AI ticket points:", breakdown["AI"]["ticket_points"])
    print("AI longest bonus:", breakdown["AI"]["longest_bonus"])
    print("AI total:", breakdown["AI"]["total"])

    print("Opponent route points:", breakdown["Opponent"]["route_points"])
    print("Opponent ticket points:", breakdown["Opponent"]["ticket_points"])
    print("Opponent longest bonus:", breakdown["Opponent"]["longest_bonus"])
    print("Opponent total:", breakdown["Opponent"]["total"])

    print("Utility U(s) =", breakdown["utility"])

    
    # C_c(s) test
    # Example hand for the AI player
    player2.cards = [
        classes.card("blue"),
        classes.card("blue"),
        classes.card("red"),
        classes.card("green")
    ]

    cc_value = C_c.C_c(game, player2)
    cc_breakdown = C_c.C_c_breakdown(game, player2)

    print("\n--- C_c(s) TEST ---")
    print("C_c(s) =", cc_value)

  #  print("\nFirst 5 contributions:")
  #  for item in cc_breakdown["details"][:5]:
    #     print(item)


if __name__ == "__main__":
    main()
