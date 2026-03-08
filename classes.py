import pandas as pd
from collections import deque
import utils

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

class grid:
    def __init__(self):
        self.nodes = []
        self.paths = []

    def import_grid(self, grid_file):
        df = pd.read_csv(grid_file)

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
        self.route = None
        self.trains = 44
    
    def __repr__(self):
        return f"player({self.name})"

class game:
    def __init__(self, grid, players):
        self.grid = grid
        self.players = []
        self.current_player = 0
        self.current_round = 0

# For testing purposes

def main():
    test_grid = grid()
    test_grid.import_grid("ttr_europe_map_data.csv")

    print("Nodes:")
    print(test_grid.get_nodes())

    print("\nPaths:")
    print(test_grid.get_paths()[:10])  # print first 10 paths

    print("\nN:")
    print(test_grid.N)


if __name__ == '__main__':
    main()
