from collections import deque
import classes

def find_longest_possible_route(grid):
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
        if not grid.nodes:
            return (0, None, None)

        longest_distance = -1
        longest_start = None
        longest_end = None

        # Run BFS from every node
        for start_node in grid.nodes:
            distances = _bfs_shortest_path_lengths(start_node, grid)

            # Find the farthest reachable node from this start node
            for end_node, distance in distances.items():
                if distance > longest_distance:
                    longest_distance = distance
                    longest_start = start_node
                    longest_end = end_node

        return (longest_distance, longest_start, longest_end)

def _bfs_shortest_path_lengths(start_node, grid):
        """
        Runs BFS from a given start node and returns the shortest number of edges
        from start_node to every end node for nodes in the grid. The grid is used to check if the node is in the grid.

        Returns:
            dict[node, int]:
                keys are nodes,
                values are shortest distances in number of paths
        """
        distances = {node: float('inf') for node in grid.nodes}
        if start_node in grid.nodes:
            distances[start_node] = 0
        queue = deque([start_node])

        while queue:
            current_node = queue.popleft()
            current_distance = distances[current_node]

            # Explore all neighboring nodes
            for p in current_node.get_connected_paths():
                neighbor = p.get_end_node() if p.get_start_node() == current_node else p.get_start_node()
                if neighbor in grid.nodes and distances[neighbor] > current_distance + 1:
                    distances[neighbor] = current_distance + 1
                    queue.append(neighbor)
        return distances

def build_graph_of_player_from_node(node, player):
    """
    Builds a graph consisting only of paths claimed by the given player,
    starting from the given node.

    Returns:
        classes.grid: a new graph containing only the connected component
        of player-owned paths reachable from the starting node.
    """

    player_graph = classes.grid()
    player_graph.add_node(node)

    visited_nodes = set()
    visited_paths = set()

    queue = deque([node])

    while queue:
        current = queue.popleft()

        if current in visited_nodes:
            continue

        visited_nodes.add(current)
        player_graph.add_node(current)

        for p in current.get_connected_paths():

            # Only follow paths owned by the player
            if p.get_occupation() != player.name:
                continue

            if p not in visited_paths:
                visited_paths.add(p)
                player_graph.add_path(p)

            # Find the neighbor node
            neighbor = p.get_end_node() if p.get_start_node() == current else p.get_start_node()

            if neighbor not in visited_nodes:
                queue.append(neighbor)

    # If the player had no claimed paths connected to the start node
    if len(player_graph.paths) == 0:
        return classes.grid()

    return player_graph

def distance_between_nodes(node1, node2):
    return abs(node1.longitude - node2.longitude) + abs(node1.latitude - node2.latitude)