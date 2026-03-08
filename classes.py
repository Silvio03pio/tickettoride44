import pandas as pd
from collections import deque

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
    def __init__(self, distance, colour):
        self.nodes = []
        self.distance = int(distance)
        self.colour = colour
        self.occupation = None

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

    def __repr__(self):
        if len(self.nodes) == 2:
            return f"path({self.nodes[0].name} <-> {self.nodes[1].name}, {self.distance}, {self.colour})"
        return f"path(unconnected, {self.distance}, {self.colour})"

class grid:
    def __init__(self):
        self.nodes = []
        self.paths = []
        self.longest_possible_route = None  # set after importing the grid
        self.N = None

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
                colour=row["color"]
            )

            start = node_lookup[row["source"]]
            end = node_lookup[row["target"]]

            p.nodes = [start, end]

            start.add_path(p)
            end.add_path(p)

            self.add_path(p)
        self.longest_possible_route = self.find_longest_possible_route()
        self.N = self.longest_possible_route[0]

    
    def find_longest_possible_route(self):
        """
        Finds the longest shortest path in the graph, measured in number of paths (edges).

        What this means:
        - For every pair of nodes in the grid, we imagine the shortest route between them,
          where each traversed path counts as 1 step.
        - Among all of those shortest routes, we find the one that is longest.
        - This is the graph's "diameter" in terms of edge count.

        Returns:
            tuple:
                (
                    longest_distance,   # int: number of paths in the longest shortest route
                    start_node,         # node: one endpoint
                    end_node            # node: the other endpoint
                )

        Algorithm used:
        - Breadth-First Search (BFS) from every node.
        - BFS is correct here because the graph is unweighted with respect to this problem:
          every path counts as 1 step regardless of train length or color.
        - For each start node, BFS computes the shortest number of edges to all reachable nodes.
        - We keep the maximum such shortest-path distance over all starts.

        Time complexity:
        - BFS from one node: O(V + E)
        - Repeated for all nodes: O(V * (V + E))
          where:
            V = number of nodes
            E = number of paths
        """

        # Edge case: empty grid
        if not self.nodes:
            return (0, None, None)

        longest_distance = -1
        longest_start = None
        longest_end = None

        # Run BFS from every node
        for start_node in self.nodes:
            distances = self._bfs_shortest_path_lengths(start_node)

            # Find the farthest reachable node from this start node
            for end_node, distance in distances.items():
                if distance > longest_distance:
                    longest_distance = distance
                    longest_start = start_node
                    longest_end = end_node

        return (longest_distance, longest_start, longest_end)

    def _bfs_shortest_path_lengths(self, start_node):
        """
        Runs BFS from a given start node and returns the shortest number of edges
        from start_node to every reachable node.

        Returns:
            dict[node, int]:
                keys are nodes,
                values are shortest distances in number of paths
        """
        distances = {start_node: 0}
        queue = deque([start_node])

        while queue:
            current_node = queue.popleft()
            current_distance = distances[current_node]

            # Explore all neighboring nodes
            for p in current_node.get_connected_paths():
                if p.get_start_node() == current_node:
                    neighbor = p.get_end_node()
                else:
                    neighbor = p.get_start_node()

                if neighbor not in distances:
                    distances[neighbor] = current_distance + 1
                    queue.append(neighbor)

        return distances

    def add_node(self, node):
        self.nodes.append(node)

    def add_path(self, path):
        self.paths.append(path)

    def get_nodes(self):
        return self.nodes

    def get_paths(self):
        return self.paths

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
