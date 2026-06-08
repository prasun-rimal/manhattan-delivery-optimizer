from pathlib import Path
import osmnx as ox

project_folder = Path(__file__).resolve().parent.parent
output_folder = project_folder / "data" / "output"
figures_folder = project_folder / "figures"

output_folder.mkdir(parents=True, exist_ok=True)
figures_folder.mkdir(parents=True, exist_ok=True)

times_square_point = (40.7580, -73.9855)

print("Downloading a small driving network around Times Square...")
print("This may take a little time on the first run.")

street_graph = ox.graph_from_point(
    times_square_point,
    dist=600,
    network_type="drive",
    simplify=True
)

number_of_nodes = len(street_graph.nodes)
number_of_edges = len(street_graph.edges)

print("\nStreet Network Download Complete")
print("--------------------------------")
print(f"Intersections/nodes: {number_of_nodes:,}")
print(f"Street segments/edges: {number_of_edges:,}")

graph_file = output_folder / "times_square_test_network.graphml"
ox.save_graphml(street_graph, filepath=str(graph_file))

map_file = figures_folder / "times_square_test_network.png"

ox.plot_graph(
    street_graph,
    node_size=0,
    edge_linewidth=0.8,
    show=False,
    close=True,
    save=True,
    filepath=str(map_file),
    dpi=300
)

print("\nFiles created:")
print(f"- {graph_file}")
print(f"- {map_file}")