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


def _owner_edge_color(owner_name: str | None) -> str | None:
    """
    Color convention for claimed routes.

    IMPORTANT: in this codebase, path.occupation stores the *player name* (e.g. "Human", "AI"),
    not the player type ("human"/"ai").
    """
    if owner_name is None:
        return None
    if str(owner_name) == "AI":
        return "#ef4444"  # red
    if str(owner_name) == "Human":
        return "#3b82f6"  # blue
    # Unknown owner name (future extensions): fall back to a readable neutral.
    return "#a78bfa"  # purple


def _scaled_positions(nodes):
    """
    Convert longitude/latitude to stable on-screen x/y.

    We normalize coordinates so the map fits nicely in the PyVis canvas and does not depend
    on the raw coordinate magnitudes.
    """
    coords = []
    for n in nodes:
        if hasattr(n, "longitude") and hasattr(n, "latitude"):
            try:
                coords.append((n, float(n.longitude), float(n.latitude)))
            except Exception:
                continue

    if not coords:
        return {}

    xs = [x for _, x, _ in coords]
    ys = [y for _, _, y in coords]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    # Avoid division by zero in degenerate cases.
    span_x = max(1e-9, (max_x - min_x))
    span_y = max(1e-9, (max_y - min_y))

    # Target canvas scale in "vis.js coordinate space"
    target_w = 1200.0
    target_h = 700.0

    out = {}
    for n, lon, lat in coords:
        # Normalize to 0..1 then scale, centered around (0,0). Invert latitude so north is up.
        nx = (lon - min_x) / span_x
        ny = (lat - min_y) / span_y
        x = (nx - 0.5) * target_w
        y = -(ny - 0.5) * target_h
        out[n.name] = (x, y)
    return out


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

    # We use fixed node positions from the CSV coordinates (when available) so the board
    # looks like an actual map instead of a "network blob".
    net.toggle_physics(False)
    net.set_options(
        """
        {
          "interaction": {
            "hover": true,
            "tooltipDelay": 80,
            "navigationButtons": true,
            "keyboard": true
          },
          "nodes": {
            "shape": "dot",
            "size": 12,
            "borderWidth": 2,
            "shadow": {
              "enabled": true,
              "color": "rgba(0,0,0,0.45)",
              "size": 8,
              "x": 2,
              "y": 2
            },
            "font": {
              "size": 16,
              "color": "#e5e7eb",
              "strokeWidth": 3,
              "strokeColor": "#0b1220"
            },
            "color": {
              "background": "#0f172a",
              "border": "#94a3b8",
              "highlight": {
                "background": "#1f2937",
                "border": "#fbbf24"
              }
            }
          },
          "edges": {
            "smooth": {
              "type": "dynamic"
            },
            "shadow": {
              "enabled": true,
              "color": "rgba(0,0,0,0.35)",
              "size": 10,
              "x": 1,
              "y": 1
            },
            "font": {
              "size": 18,
              "color": "#f9fafb",
              "strokeWidth": 4,
              "strokeColor": "#0b1220",
              "background": "rgba(17,24,39,0.65)"
            }
          }
        }
        """
    )

    # Add city nodes
    nodes = graph.get_nodes()
    pos = _scaled_positions(nodes)
    for node in nodes:
        x, y = pos.get(node.name, (None, None))

        net.add_node(
            node.name,
            label=node.name,
            title=node.name,
            x=x,
            y=y,
            physics=False,
        )

    # Add path edges
    for path in graph.get_paths():
        start = path.get_start_node().name
        end = path.get_end_node().name
        occupation = path.get_occupation()
        path_colour = path.get_colour()
        distance = path.get_distance()
        path_id = path.get_path_id()


        if occupation == "Human":
            edge_color = "#3b82f6"  # blue for Human
        elif occupation == "AI":
            edge_color = "#ef4444"  # red for AI
        else:
            edge_color = path_display_color(path_colour)


        # Make claimed routes and the selected route pop visually.
        is_selected = selected_path_id is not None and str(path_id) == str(selected_path_id)
        if is_selected:
            width = 8
        elif occupation is not None:
            width = 6
        else:
            width = 3

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
            # Use a per-edge color config so hover/highlight keeps ownership obvious.
            color={
                "color": edge_color,
                "highlight": edge_color,
                "hover": edge_color,
                "inherit": False,
                # Slightly dim unclaimed routes so claimed routes stand out more.
                "opacity": 0.85 if occupation is None else 1.0,
            },
            width=width,
            # Show required trains directly on the edge (always visible).
            label=str(distance),
            title=title,
            # Make the selected route extra visible without changing core game state.
            dashes=True if is_selected else False,
            # Glow-like emphasis: strengthen shadow for claimed routes.
            shadow={
                "enabled": True,
                "color": edge_color if occupation is not None else "rgba(0,0,0,0.35)",
                "size": 18 if occupation is not None else 10,
                "x": 1,
                "y": 1,
            },
        )

    return net