
class state:
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