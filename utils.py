from collections import deque
import classes
import heapq

def find_longest_possible_route(graph):
    """
    Finds the longest shortest path in the graph, measured in number of paths (edges).

    What this means:
    - For every pair of nodes in the graph, we imagine the shortest route between them,
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
    - For every start node, compute shortest path lengths to all other nodes.
    - The helper _bfs_shortest_route_lengths(start_node, graph) now uses
      shortest_route_between_two_nodes(node1, node2, graph) for each target node.

    Time complexity:
    - This version is simpler conceptually, but less efficient than one BFS from each node,
      because it runs a BFS separately for each pair of nodes.
    """

    # Edge case: empty graph
    if not graph.nodes:
        return (0, None, None)

    longest_distance = -1
    longest_start = None
    longest_end = None

    # Run "all target nodes from one start node"
    for start_node in graph.nodes:
        distances = _bfs_shortest_route_lengths(start_node, graph)

        for end_node, distance in distances.items():
            if distance > longest_distance and distance != float("inf"):
                longest_distance = distance
                longest_start = start_node
                longest_end = end_node

    return (longest_distance, longest_start, longest_end)

def shortest_route_between_two_nodes(node1, node2, graph):
    """
    Returns the shortest distance in number of edges between node1 and node2
    using BFS.

    Args:
        node1: start node
        node2: target node
        graph: the graph containing the nodes

    Returns:
        int or float('inf'):
            - shortest number of edges between node1 and node2
            - float('inf') if node2 is unreachable from node1
    """

    if node1 not in graph.nodes or node2 not in graph.nodes:
        return float("inf")

    if node1 == node2:
        return 0

    visited = set()
    queue = deque([(node1, 0)])
    visited.add(node1)

    while queue:
        current_node, distance = queue.popleft()

        for p in current_node.get_connected_paths():
            neighbor = (
                p.get_end_node()
                if p.get_start_node() == current_node
                else p.get_start_node()
            )

            if neighbor not in graph.nodes or neighbor in visited:
                continue

            if neighbor == node2:
                return distance + 1

            visited.add(neighbor)
            queue.append((neighbor, distance + 1))

    return float("inf")

def _bfs_shortest_route_lengths(start_node, graph):
    """
    Returns the shortest number of edges from start_node to every node in graph.

    This keeps the same name/signature as before so other files do not need to change.
    Internally, it now uses shortest_route_between_two_nodes(...) for each target node.

    Returns:
        dict[node, int]:
            keys are nodes,
            values are shortest distances in number of paths
    """
    distances = {}

    for node in graph.nodes:
        distances[node] = shortest_route_between_two_nodes(start_node, node, graph)

    return distances

def build_graph_of_player_from_node(node, player):
    """
    Builds a graph consisting only of paths claimed by the given player,
    starting from the given node.

    Returns:
        classes.graph: a new graph containing only the connected component
        of player-owned paths reachable from the starting node.
    """

    player_graph = classes.graph()
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
            neighbor = (
                p.get_end_node()
                if p.get_start_node() == current
                else p.get_start_node()
            )

            if neighbor not in visited_nodes:
                queue.append(neighbor)

    return player_graph

def geographical_distance(node1, node2):
    return abs(node1.longitude - node2.longitude) + abs(node1.latitude - node2.latitude)

def find_shortest_connection_between_subgraphs(subgraph_a, subgraph_b):
    """
    Find the shortest way to connect two subgraphs using a multi-source BFS.

    Idea:
    - Start BFS from *all* nodes in subgraph A at once.
    - Stop as soon as a node in subgraph B is reached.
    - Use geographical distance to subgraph B only as a heuristic tie-breaker
      when deciding which node at the same depth to expand first.

    Important:
    - Because depth (number of edges) is always the first priority,
      this still returns a true shortest connection in edge count.
    - The heuristic only affects which equally short candidate is explored first.

    Args:
        subgraph_a: subgraph A
        subgraph_b: subgraph B

    Returns:
        dict with:
            {
                "distance": int,              # number of edges in shortest connection
                "path_nodes": [node, ...],    # nodes from A-side to B-side
                "path_edges": [path, ...],    # path objects along that route
                "start_node": node,           # first node on route (in A)
                "end_node": node              # first reached node in B
            }

        Returns None if no connection exists.

        Special case:
        - If the two subgraphs already overlap, returns distance 0.
    """

    a_nodes = set(subgraph_a.nodes)
    b_nodes = set(subgraph_b.nodes)

    if not a_nodes or not b_nodes:
        return None

    # If they already share a node, they are already connected.
    overlap = a_nodes & b_nodes
    if overlap:
        shared = next(iter(overlap))
        return {
            "distance": 0,
            "path_nodes": [shared],
            "path_edges": [],
            "start_node": shared,
            "end_node": shared
        }

    def heuristic_distance_to_b(node):
        """Minimum geographical distance from node to any node in subgraph B."""
        return min(geographical_distance(node, target) for target in b_nodes)

    # Priority queue entries:
    # (depth, heuristic, tie_breaker, current_node)
    #
    # depth is first -> guarantees shortest path in number of edges
    # heuristic is second -> chooses promising node among equal-depth candidates
    frontier = []
    counter = 0

    # Parent maps for reconstructing the path
    parent_node = {}
    parent_edge = {}
    best_depth = {}

    for start in a_nodes:
        best_depth[start] = 0
        parent_node[start] = None
        parent_edge[start] = None
        heapq.heappush(frontier, (0, heuristic_distance_to_b(start), counter, start))
        counter += 1

    while frontier:
        depth, _, _, current = heapq.heappop(frontier)

        # Ignore stale queue entries
        if depth != best_depth[current]:
            continue

        # Success: reached subgraph B
        if current in b_nodes:
            path_nodes = []
            path_edges = []
            node_cursor = current

            while node_cursor is not None:
                path_nodes.append(node_cursor)
                edge_used = parent_edge[node_cursor]
                if edge_used is not None:
                    path_edges.append(edge_used)
                node_cursor = parent_node[node_cursor]

            path_nodes.reverse()
            path_edges.reverse()

            return {
                "distance": len(path_edges),
                "path_nodes": path_nodes,
                "path_edges": path_edges,
                "start_node": path_nodes[0],
                "end_node": path_nodes[-1]
            }

        # Expand neighbors
        for p in current.get_connected_paths():
            neighbor = p.get_end_node() if p.get_start_node() == current else p.get_start_node()
            new_depth = depth + 1

            if neighbor not in best_depth or new_depth < best_depth[neighbor]:
                best_depth[neighbor] = new_depth
                parent_node[neighbor] = current
                parent_edge[neighbor] = p

                heapq.heappush(
                    frontier,
                    (new_depth, heuristic_distance_to_b(neighbor), counter, neighbor)
                )
                counter += 1

    return 
    
def get_node_from_name(graph, name):
    for node in graph.nodes:
        if name == node.name: return node
    return False

def get_path_from_id(graph, id):
    for path in graph.nodes:
        if id == path.name: return path
    return False  
