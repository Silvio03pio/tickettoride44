from dataclasses import dataclass, field
from typing import List, Optional, Literal
import pandas as pd
from collections import deque, Counter
import random

import classes # Uses graph, player, deck, route_card as defined there

#___________________________________
# Action Representation
#___________________________________

# Define a class Action that lets a player draw or claim a route



#___________________________________
# Player State
#___________________________________

# Define a class PlayerState to track their cards on hand, ticket, and trains left (search and evaluation will use this)




#___________________________________
# Game State
#___________________________________

# Define a class GameState to track the game state (rules, evaluation, and search will use this)


class player:
    def __init__(self, name):
        self.name = name
        self.score = 0
        self.cards = []
        self.route = None # this is a route_card object
        self.trains = 44
        self.P_R = 21 # will be removed and only stored in self.route

    def give_route(self):

        # Apply random functions here sometime
        start = "Brest"
        end = "Petrograd"
        points = 21
        self.route = {
            "start": start,
            "end": end,
            "points": points
        }

    def add_card_to_hand(self, card): 
        self.cards.append(card) 

    def draw_card(self, deck):
        if deck.cards: 
            card = deck.cards.pop(0) # remocves top card from deck
            self.add_card_to_hand(card)
        else: 
            return False # No cards in deck
    
    def place_trains(self, path):
        colour = path.colour
        train_count = path.distance

        matching_cards = [card for card in self.cards if card.colour == colour]

        if len(matching_cards) < train_count:
            return False

        cards_to_remove = matching_cards[:train_count]
        for card in cards_to_remove:
            self.cards.remove(card)

        path.occupation = self.name
        self.trains -= train_count

        return path
    
    def claim_path(self, path):
        path.occupation = self.name

    def __repr__(self):
        return f"player({self.name})"


class game:
    def __init__(self, graph, players, deck, longest_route_points=10):
        self.graph = graph
        self.players = players
        self.current_player = 0
        self.current_round = 0
        self.deck = deck
        self.longest_route_points = longest_route_points

        print("Game created successfully")
        print(f"Nodes: {len(self.graph.get_nodes())}")
        print(f"Paths: {len(self.graph.get_paths())}")
        print(f"Players: {[player.name for player in self.players]}")

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

if __name__ == '__main__':
    main()