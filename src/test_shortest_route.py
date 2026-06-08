from pathlib import Path
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

print("Shortest Route Test")
print("-------------------")
print(f"Origin node: {origin_node}")
print(f"Destination node: {destination_node}")

shortest_route = nx.shortest_path(
    street_graph,
    origin_node,
    destination_node,
    weight="length"
)

route_edges = ox.routing.route_to_gdf(street_graph, shortest_route)
total_distance_meters = route_edges["length"].sum()

print(f"Route intersections visited: {len(shortest_route):,}")
print(f"Total route distance: {total_distance_meters:.2f} meters")
print(f"Total route distance: {total_distance_meters / 1609.34:.2f} miles")

route_map_file = figures_folder / "times_square_shortest_route.png"

ox.plot_graph_route(
    street_graph,
    shortest_route,
    node_size=0,
    edge_linewidth=0.8,
    route_linewidth=4,
    show=False,
    close=True,
    save=True,
    filepath=str(route_map_file),
    dpi=300
)

print("\nFile created:")
print(f"- {route_map_file}")