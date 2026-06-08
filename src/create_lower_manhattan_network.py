from pathlib import Path
import osmnx as ox

project_folder = Path(__file__).resolve().parent.parent
output_folder = project_folder / "data" / "output"
figures_folder = project_folder / "figures"

output_folder.mkdir(parents=True, exist_ok=True)
figures_folder.mkdir(parents=True, exist_ok=True)

lower_manhattan_point = (40.7075, -74.0040)

print("Downloading a Lower Manhattan driving network...")
print("This area is chosen because it includes streets represented in our NYC datasets.")

street_graph = ox.graph_from_point(
    lower_manhattan_point,
    dist=1700,
    network_type="drive",
    simplify=True
)

print("\nLower Manhattan Street Network Download Complete")
print("-----------------------------------------------")
print(f"Intersections/nodes: {len(street_graph.nodes):,}")
print(f"Street segments/edges: {len(street_graph.edges):,}")

graph_file = output_folder / "lower_manhattan_network.graphml"
ox.save_graphml(street_graph, filepath=str(graph_file))

map_file = figures_folder / "lower_manhattan_network.png"

ox.plot_graph(
    street_graph,
    node_size=0,
    edge_linewidth=0.6,
    show=False,
    close=True,
    save=True,
    filepath=str(map_file),
    dpi=300
)

print("\nFiles created:")
print(f"- {graph_file}")
print(f"- {map_file}")