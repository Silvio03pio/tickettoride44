from pyvis.network import Network


def path_display_color(path_colour: str) -> str:
    """
    Converts route colours to map-friendly colours.
    White is changed to light gray so it stays visible on a dark background.
    """
    mapping = {
        "red": "#ef4444",
        "blue": "#3b82f6",
        "green": "#22c55e",
        "yellow": "#eab308",
        "black": "#111827",
        "white": "#d1d5db",
        "orange": "#f97316",
        "pink": "#ec4899",
        "grey": "#9ca3af",
        "gray": "#9ca3af",
    }
    return mapping.get(str(path_colour).lower(), "#9ca3af")


def create_map(graph, selected_path_id=None):
    """
    Builds an interactive Pyvis network for the Ticket to Ride map.

    Visual rules:
    - unclaimed paths use their route colour
    - human claimed paths are highlighted in green
    - AI claimed paths are highlighted in red
    - selected path is thicker
    - path label shows required number of trains
    """
    net = Network(
        height="650px",
        width="100%",
        bgcolor="#111827",
        font_color="white",
        directed=False,
    )

    net.barnes_hut()
    net.toggle_physics(False)

    # Add city nodes
    for node in graph.get_nodes():
        x = None
        y = None

        # Use map coordinates if available
        if hasattr(node, "longitude") and hasattr(node, "latitude"):
            x = float(node.longitude) * 25
            y = -float(node.latitude) * 25

        net.add_node(
            node.name,
            label=node.name,
            title=node.name,
            x=x,
            y=y,
            physics=False,
            shape="dot",
            size=12,
            color="#f8fafc",
        )

    # Add path edges
    for path in graph.get_paths():
        start = path.get_start_node().name
        end = path.get_end_node().name
        occupation = path.get_occupation()
        path_colour = path.get_colour()
        distance = path.get_distance()
        path_id = path.get_path_id()

        if occupation == "human":
            edge_color = "#22c55e"
        elif occupation == "AI":
            edge_color = "#ef4444"
        else:
            edge_color = path_display_color(path_colour)

        width = 3
        if selected_path_id is not None and str(path_id) == str(selected_path_id):
            width = 7
        elif occupation is not None:
            width = 5

        title = (
            f"Path ID: {path_id}<br>"
            f"{start} ↔ {end}<br>"
            f"Colour: {path_colour}<br>"
            f"Length: {distance}<br>"
            f"Owner: {occupation if occupation is not None else 'unclaimed'}"
        )

        net.add_edge(
            start,
            end,
            color=edge_color,
            width=width,
            label=str(distance),
            title=title,
        )

    return net