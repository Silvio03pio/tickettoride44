import classes
import utils
import P_R
import P_L
import P_colour
import U_s
import C_c

def main(): 

    # Graph - Map
    game_graph = classes.graph()
    game_graph.import_graph("ttr_europe_map_data.csv")

    # Players
    player1 = classes.player("human")
    player2 = classes.player("AI")
    players = [player1, player2]

    # Deck of train cards
    deck = classes.deck()

    # Create game
    game = classes.game(game_graph, players, deck)


    # ---------------------------------- TEST ----------------------------------


    #Test for P_L
    print("\n--- P_LONGEST PATH TEST ---")
    player2.claim_path(game.graph.paths[10])
    player2.claim_path(game.graph.paths[11])
    ai_longest = P_L._longest_chain_for_player(game.graph, player2)
    opp_longest = P_L._longest_chain_for_player(game.graph, player1)
    Pl = P_L.P_L(game, player2)
    print(f"AI longest: {ai_longest}")
    print(f"Human longest: {opp_longest}")
    print(f"Probability of winning longest path bonus: {Pl}")

    # P_colour 
    print("\n--- P_COLOUR TEST ---")
    prop = P_colour.P_colour(game.deck, "blue")
    print(f"Propability of blue: {prop}")
    game.deck.shuffle()
    for i in range(10): # draw 10 cards from deck
        player1.draw_card(game.deck)
    print(f"Player 1 cards: {player1.cards}")
    prop = P_colour.P_colour(game.deck, "blue")
    print(f"probability of blue now: {prop}")
    
    """
    game.draw_card("blue")    # draw 1 blue
    game.deck.ai_draw_card("blue")    # draw 1 blue
    game.deck.ai_draw_card("blue")    # draw 1 blue
    game.deck.ai_draw_card("blue")    # draw 1 blue  → 4 blue in AI hand
    game.deck.ai_draw_card("red")     # draw 1 red
    game.deck.ai_draw_card("red")     # draw 1 red   → 2 red in AI hand
    game.deck.ai_play_card("blue", 3) # claims a route with three blue → 1 blue in hand
    
    print(f"\nP(blue) = {P_colour.P_colour(game.deck, 'blue'):.4f}")
    print(f"P(red)  = {P_colour.P_colour(game.deck, 'red'):.4f}")
    print(f"All colours: {P_colour.all_probabilities(game.deck)}")
    """
        
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
    # print("C_c breakdown", cc_breakdown)

  #  print("\nFirst 5 contributions:")
  #  for item in cc_breakdown["details"][:5]:
    #     print(item)


if __name__ == "__main__":
    main()
