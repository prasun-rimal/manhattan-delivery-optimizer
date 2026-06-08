"""
Core routing functions for the Manhattan Last-Mile Delivery Optimizer.

This module loads the prepared delivery-weighted road network and calculates:
1. A shortest-distance baseline route using Dijkstra's algorithm.
2. A delivery-aware route using Dijkstra's algorithm.
3. A delivery-aware route using A* for verification.

It also converts the route node paths into latitude/longitude coordinate
lists so a future web map can draw the routes.
"""

from pathlib import Path
import sys

import networkx as nx
import osmnx as ox

CURRENT_FOLDER = Path(__file__).resolve().parent
if str(CURRENT_FOLDER) not in sys.path:
    sys.path.append(str(CURRENT_FOLDER))

from locations import get_coordinates, get_location_names



PROJECT_FOLDER = Path(__file__).resolve().parent.parent.parent
GRAPH_FILE = (
    PROJECT_FOLDER
    / "data"
    / "output"
    / "lower_manhattan_component_weighted_network.graphml"
)



def load_delivery_graph():
    """
    Load the prepared Lower Manhattan road network.

    Custom values saved in GraphML are converted back to numeric values
    so they can be used in routing calculations.
    """
    if not GRAPH_FILE.exists():
        raise FileNotFoundError(
            "The delivery-weighted road network was not found. "
            "Run create_component_weighted_network.py first."
        )

    graph = ox.load_graphml(filepath=str(GRAPH_FILE))

    for start_node, end_node, key, edge_data in graph.edges(
        keys=True, data=True
    ):
        edge_data["length"] = float(edge_data["length"])
        edge_data["delivery_weight"] = float(edge_data["delivery_weight"])
        edge_data["delivery_score"] = float(edge_data["delivery_score"])
        edge_data["components_observed"] = int(
            edge_data["components_observed"]
        )

    return graph




def straight_line_heuristic(graph, node_1, node_2):
    """
    Estimate remaining physical distance between two nodes in meters.

    This is a valid heuristic for delivery-aware routing because the
    delivery-weighted cost is always at least the physical street length.
    """
    latitude_1 = graph.nodes[node_1]["y"]
    longitude_1 = graph.nodes[node_1]["x"]
    latitude_2 = graph.nodes[node_2]["y"]
    longitude_2 = graph.nodes[node_2]["x"]

    return ox.distance.great_circle(
        latitude_1,
        longitude_1,
        latitude_2,
        longitude_2
    )



def route_to_coordinates(graph, route):
    """
    Convert a route from graph node IDs into latitude/longitude pairs.

    This format can be used by a web map such as Leaflet.js.
    """
    coordinates = []

    for node in route:
        latitude = graph.nodes[node]["y"]
        longitude = graph.nodes[node]["x"]
        coordinates.append([latitude, longitude])

    return coordinates



def calculate_route_metrics(graph, route, routing_weight):
    """Calculate distance, modeled cost, and data coverage for one route."""
    route_edges = ox.routing.route_to_gdf(
        graph,
        route,
        weight=routing_weight
    ).copy()

    route_edges["length"] = route_edges["length"].astype(float)
    route_edges["delivery_weight"] = route_edges[
        "delivery_weight"
    ].astype(float)

    total_distance = route_edges["length"].sum()
    total_delivery_cost = route_edges["delivery_weight"].sum()

    traffic_distance = route_edges.loc[
        route_edges["has_traffic_data"] == "Yes",
        "length"
    ].sum()

    parking_distance = route_edges.loc[
        route_edges["has_parking_data"] == "Yes",
        "length"
    ].sum()

    truck_distance = route_edges.loc[
        route_edges["has_truck_data"] == "Yes",
        "length"
    ].sum()

    two_component_distance = route_edges.loc[
        route_edges["components_observed"].astype(int) >= 2,
        "length"
    ].sum()

    return {
        "distance_meters": round(total_distance, 2),
        "distance_miles": round(total_distance / 1609.34, 2),
        "delivery_cost": round(total_delivery_cost, 2),
        "traffic_coverage_percent": round(
            traffic_distance / total_distance * 100, 2
        ),
        "parking_coverage_percent": round(
            parking_distance / total_distance * 100, 2
        ),
        "truck_coverage_percent": round(
            truck_distance / total_distance * 100, 2
        ),
        "two_component_coverage_percent": round(
            two_component_distance / total_distance * 100, 2
        )
    }




def calculate_routes(origin_name, destination_name):
    """
    Calculate baseline and delivery-aware routes between two named locations.

    Returns route paths, coordinate lists, and comparison metrics for use
    by a future web app.
    """
    if origin_name == destination_name:
        raise ValueError("Origin and destination must be different locations.")

    graph = load_delivery_graph()

    origin_coordinates = get_coordinates(origin_name)
    destination_coordinates = get_coordinates(destination_name)

    origin_node = ox.distance.nearest_nodes(
        graph,
        X=origin_coordinates[1],
        Y=origin_coordinates[0]
    )

    destination_node = ox.distance.nearest_nodes(
        graph,
        X=destination_coordinates[1],
        Y=destination_coordinates[0]
    )

    baseline_route = nx.dijkstra_path(
        graph,
        origin_node,
        destination_node,
        weight="length"
    )

    optimized_route = nx.dijkstra_path(
        graph,
        origin_node,
        destination_node,
        weight="delivery_weight"
    )

    astar_route = nx.astar_path(
        graph,
        origin_node,
        destination_node,
        weight="delivery_weight",
        heuristic=lambda node_1, node_2: straight_line_heuristic(
            graph,
            node_1,
            node_2
        )
    )

    baseline_metrics = calculate_route_metrics(
        graph,
        baseline_route,
        "length"
    )

    optimized_metrics = calculate_route_metrics(
        graph,
        optimized_route,
        "delivery_weight"
    )

    comparison = {
        "origin": origin_name,
        "destination": destination_name,
        "baseline_distance_meters": baseline_metrics["distance_meters"],
        "baseline_distance_miles": baseline_metrics["distance_miles"],
        "optimized_distance_meters": optimized_metrics["distance_meters"],
        "optimized_distance_miles": optimized_metrics["distance_miles"],
        "added_distance_meters": round(
            optimized_metrics["distance_meters"]
            - baseline_metrics["distance_meters"],
            2
        ),
        "baseline_delivery_cost": baseline_metrics["delivery_cost"],
        "optimized_delivery_cost": optimized_metrics["delivery_cost"],
        "delivery_cost_improvement": round(
            baseline_metrics["delivery_cost"]
            - optimized_metrics["delivery_cost"],
            2
        ),
        "optimized_traffic_coverage_percent": (
            optimized_metrics["traffic_coverage_percent"]
        ),
        "optimized_parking_coverage_percent": (
            optimized_metrics["parking_coverage_percent"]
        ),
        "optimized_truck_coverage_percent": (
            optimized_metrics["truck_coverage_percent"]
        ),
        "optimized_two_component_coverage_percent": (
            optimized_metrics["two_component_coverage_percent"]
        ),
        "route_changed": baseline_route != optimized_route,
        "dijkstra_and_astar_agree": optimized_route == astar_route
    }

    return {
        "baseline_route": baseline_route,
        "optimized_route": optimized_route,
        "astar_route": astar_route,
        "baseline_coordinates": route_to_coordinates(graph, baseline_route),
        "optimized_coordinates": route_to_coordinates(graph, optimized_route),
        "comparison": comparison
    }



if __name__ == "__main__":
    print("Available Delivery Locations")
    print("----------------------------")

    for location_name in get_location_names():
        print(f"- {location_name}")

    print("\nTesting Showcase Route")
    print("----------------------")

    result = calculate_routes(
        "Financial District",
        "Chinatown"
    )

    for metric_name, value in result["comparison"].items():
        print(f"{metric_name}: {value}")

    print("\nRoute Coordinate Check")
    print("----------------------")
    print(
        "Baseline coordinate points:",
        len(result["baseline_coordinates"])
    )
    print(
        "Optimized coordinate points:",
        len(result["optimized_coordinates"])
    )
    print(
        "First optimized coordinate:",
        result["optimized_coordinates"][0]
    )
    print(
        "Last optimized coordinate:",
        result["optimized_coordinates"][-1]
    )