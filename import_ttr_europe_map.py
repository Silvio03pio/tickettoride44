from __future__ import annotations
import csv
from typing import Callable, Any, Optional

def load_ticket_to_ride_europe(
    csv_path: str,
    grid_cls,
    node_factory: Optional[Callable[..., Any]] = None,
    path_factory: Optional[Callable[..., Any]] = None,
):
    """
    Load Ticket to Ride: Europe map data from a single CSV file and build a grid.

    Parameters
    ----------
    csv_path:
        Path to the CSV created from the map data.
    grid_cls:
        Usually your `grid` class. The function instantiates it as `grid_cls()`.
    node_factory:
        Optional callable used to build node objects. If omitted, city rows are
        stored as plain dicts.
        Signature used:
            node_factory(name=<city>, longitude=<lon>, latitude=<lat>)
    path_factory:
        Optional callable used to build path objects. If omitted, route rows are
        stored as plain dicts.
        Signature used:
            path_factory(
                source=<source>, target=<target>, length=<length>,
                color=<color>, route_type=<route_type>, tunnel=<bool>,
                locomotives=<int>, double_route=<bool>, route_id=<route_id>
            )

    Returns
    -------
    map_obj:
        An instance of `grid_cls` with nodes and paths added.
    """
    map_obj = grid_cls()

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["record_type"] == "city":
                city = row["city"]
                longitude = float(row["longitude"])
                latitude = float(row["latitude"])

                node_obj = (
                    node_factory(name=city, longitude=longitude, latitude=latitude)
                    if node_factory is not None
                    else {
                        "name": city,
                        "longitude": longitude,
                        "latitude": latitude,
                    }
                )
                map_obj.add_node(node_obj)

            elif row["record_type"] == "route":
                route_obj = (
                    path_factory(
                        source=row["source"],
                        target=row["target"],
                        length=int(row["length"]),
                        color=row["color"],
                        route_type=row["route_type"],
                        tunnel=row["tunnel"].lower() == "true",
                        locomotives=int(row["locomotives"]),
                        double_route=row["double_route"].lower() == "true",
                        route_id=row["route_id"],
                    )
                    if path_factory is not None
                    else {
                        "route_id": row["route_id"],
                        "source": row["source"],
                        "target": row["target"],
                        "length": int(row["length"]),
                        "color": row["color"],          # specific color or "gray"
                        "route_type": row["route_type"],# "train", "tunnel", or "ferry"
                        "tunnel": row["tunnel"].lower() == "true",
                        "locomotives": int(row["locomotives"]),
                        "double_route": row["double_route"].lower() == "true",
                    }
                )
                map_obj.add_path(route_obj)

    return map_obj


# Example usage with the user's grid class:
#
class grid:
    def __init__(self):
        self.nodes = []
        self.paths = []
        self.n = None

    def find_highest_number_of_paths_between_nodes(self, paths):
        highest_number = 0
        for path in paths:
            for node in path.nodes:
                if node.get_connected_paths().count() > highest_number:
                    highest_number = node.get_connected_paths().count()
        return highest_number
#
    def add_node(self, node):
        self.nodes.append(node)

    def add_path(self, path):
        self.paths.append(path)

    def get_nodes(self):
        return self.nodes

    def get_paths(self):
        return self.paths
#
europe_map = load_ticket_to_ride_europe("ttr_europe_map_data.csv", grid)