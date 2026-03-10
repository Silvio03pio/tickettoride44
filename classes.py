import pandas as pd
from collections import deque, Counter
import random

COLOURS = ["red", "blue", "green", "yellow", "black", "white", "orange", "pink"]
NBR_OF_CARDS_PER_COLOUR = 12

class node:
    def __init__(self, name, longitude, latitude):
        self.name = name
        self.connected_paths = []
        self.longitude = longitude
        self.latitude = latitude

    def add_path(self, path):
        self.connected_paths.append(path)

    def remove_path(self, path):
        self.connected_paths.remove(path)

    def get_connected_paths(self):
        return self.connected_paths

    def __repr__(self):
        return f"node({self.name})"

class path:
    def __init__(self, distance, colour, path_id):
        self.nodes = []
        self.distance = int(distance)
        self.colour = colour
        self.occupation = None
        self.path_id = path_id

    def get_start_node(self):
        return self.nodes[0]

    def get_end_node(self):
        return self.nodes[1]

    def get_distance(self):
        return self.distance

    def get_colour(self):
        return self.colour

    def get_occupation(self):
        return self.occupation

    def set_occupation(self, player):
        self.occupation = player.name

    def get_path_id(self):
        return self.path_id

    def __repr__(self):
        if len(self.nodes) == 2:
            return f"path({self.nodes[0].name} <-> {self.nodes[1].name}, {self.distance}, {self.colour})"
        return f"path(unconnected, {self.distance}, {self.colour})"

class route_card:
    def __init__(self, destinations, points):
        self.destinations = destinations
        self.points = points

class graph:
    def __init__(self):
        self.nodes = []
        self.paths = []

    def import_graph(self, graph_file):
        df = pd.read_csv(graph_file)

        self.nodes = []
        self.paths = []

        node_lookup = {}

        # ---- Create nodes ----
        node_rows = df[df["record_type"] == "node"]

        for _, row in node_rows.iterrows():
            n = node(
                name=row["name"],
                longitude=float(row["longitude"]),
                latitude=float(row["latitude"])
            )
            self.add_node(n)
            node_lookup[row["name"]] = n

        # ---- Create paths ----
        path_rows = df[df["record_type"] == "path"]

        for _, row in path_rows.iterrows():
            p = path(
                distance=int(row["length"]),
                colour=row["color"],
                path_id=row["path_id"]
            )

            start = node_lookup[row["source"]]
            end = node_lookup[row["target"]]

            p.nodes = [start, end]

            start.add_path(p)
            end.add_path(p)

            self.add_path(p)

    def add_node(self, node):
        if node not in self.nodes:
            self.nodes.append(node)
        return node

    def add_path(self, path):
        self.paths.append(path)
        self.add_node(path.nodes[0])
        self.add_node(path.nodes[1])
        # self.longest_possible_route = utils.find_longest_possible_route(self)
        # self.N = self.longest_possible_route[0]

    def get_nodes(self):
        return self.nodes

    def get_paths(self):
        return self.paths

    def claim_path(self, path, player):
        for p in self.paths:
            if p.get_path_id() == path.get_path_id():
                p.set_occupation(player)
                return True 
        return False

class card:
    def __init__(self, colour):
        self.colour = colour

    def get_colour(self):
        return self.colour

    def __repr__(self):
        return f"card({self.colour})"

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

class deck:
    def __init__(self, colours=COLOURS, nbr_of_cards_per_colour=NBR_OF_CARDS_PER_COLOUR): 
        self.cards = self.build_deck(colours, nbr_of_cards_per_colour)

    def build_deck(self, colours, nbr_of_cards_per_colour):
        cards = []
        for colour in colours:
            for i in range(nbr_of_cards_per_colour):
                current_card = card(colour)
                cards.append(current_card)
        return cards

    def shuffle(self):
        self.deck = random.shuffle(self.cards)

    def get_card_count(self): # Number of cards not stored, only counted when needed
        return len(self.cards)

    def get_colour_count(self, colour):
        return sum(card.colour == colour for card in self.cards)

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
