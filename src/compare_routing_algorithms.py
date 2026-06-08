from pathlib import Path
from time import perf_counter

import networkx as nx
import osmnx as ox


project_folder = Path(__file__).resolve().parent.parent
output_folder = project_folder / "data" / "output"
figures_folder = project_folder / "figures"

graph_file = output_folder / "times_square_test_network.graphml"


street_graph = ox.load_graphml(filepath=str(graph_file))


origin_point = (40.7544, -73.9862)
destination_point = (40.7621, -73.9830)

origin_node = ox.distance.nearest_nodes(
    street_graph,
    X=origin_point[1],
    Y=origin_point[0]
)

destination_node = ox.distance.nearest_nodes(
    street_graph,
    X=destination_point[1],
    Y=destination_point[0]
)


def straight_line_heuristic(node_1, node_2):
    """
    Estimate the remaining distance between two intersections in meters.
    A* uses this estimate to guide its search toward the destination.
    """
    latitude_1 = street_graph.nodes[node_1]["y"]
    longitude_1 = street_graph.nodes[node_1]["x"]
    latitude_2 = street_graph.nodes[node_2]["y"]
    longitude_2 = street_graph.nodes[node_2]["x"]

    return ox.distance.great_circle(
        latitude_1,
        longitude_1,
        latitude_2,
        longitude_2
    )


def calculate_route_distance(route):
    """Calculate total route distance in meters."""
    route_edges = ox.routing.route_to_gdf(street_graph, route)
    return route_edges["length"].sum()


dijkstra_start = perf_counter()

dijkstra_route = nx.dijkstra_path(
    street_graph,
    origin_node,
    destination_node,
    weight="length"
)

dijkstra_time = perf_counter() - dijkstra_start
dijkstra_distance = calculate_route_distance(dijkstra_route)

astar_start = perf_counter()

astar_route = nx.astar_path(
    street_graph,
    origin_node,
    destination_node,
    heuristic=straight_line_heuristic,
    weight="length"
)

astar_time = perf_counter() - astar_start
astar_distance = calculate_route_distance(astar_route)

print("Dijkstra vs. A* Route Comparison")
print("--------------------------------")
print(f"Origin node: {origin_node}")
print(f"Destination node: {destination_node}")

print("\nDijkstra Results")
print("----------------")
print(f"Intersections visited in returned route: {len(dijkstra_route):,}")
print(f"Total route distance: {dijkstra_distance:.2f} meters")
print(f"Runtime: {dijkstra_time:.8f} seconds")

print("\nA* Results")
print("----------")
print(f"Intersections visited in returned route: {len(astar_route):,}")
print(f"Total route distance: {astar_distance:.2f} meters")
print(f"Runtime: {astar_time:.8f} seconds")

print("\nComparison")
print("----------")
print(f"Same distance found: {dijkstra_distance == astar_distance}")
print(f"Same exact route found: {dijkstra_route == astar_route}")

astar_map_file = figures_folder / "times_square_astar_route.png"

ox.plot_graph_route(
    street_graph,
    astar_route,
    node_size=0,
    edge_linewidth=0.8,
    route_linewidth=4,
    show=False,
    close=True,
    save=True,
    filepath=str(astar_map_file),
    dpi=300
)

print("\nFile created:")
print(f"- {astar_map_file}")