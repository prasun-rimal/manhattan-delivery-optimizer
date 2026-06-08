from pathlib import Path

import networkx as nx
import osmnx as ox
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

project_folder = Path(__file__).resolve().parent.parent
output_folder = project_folder / "data" / "output"

graph_file = output_folder / "lower_manhattan_weighted_network.graphml"
comparison_file = output_folder / "battery_park_to_seaport_route_breakdown.csv"

street_graph = ox.load_graphml(filepath=str(graph_file))

for start_node, end_node, key, edge_data in street_graph.edges(
    keys=True, data=True
):
    edge_data["delivery_weight"] = float(edge_data["delivery_weight"])
    edge_data["delivery_score"] = float(edge_data["delivery_score"])
    edge_data["length"] = float(edge_data["length"])

origin_point = (40.7033, -74.0170)       # Battery Park
destination_point = (40.7068, -74.0035)  # South Street Seaport

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

baseline_route = nx.dijkstra_path(
    street_graph,
    origin_node,
    destination_node,
    weight="length"
)

delivery_route = nx.dijkstra_path(
    street_graph,
    origin_node,
    destination_node,
    weight="delivery_weight"
)


def summarize_route(route, route_name):
    """Summarize how much of a route uses each score source."""
    route_edges = ox.routing.route_to_gdf(street_graph, route).copy()

    route_edges["length"] = route_edges["length"].astype(float)
    route_edges["delivery_weight"] = route_edges["delivery_weight"].astype(float)

    summary = (
        route_edges.groupby("score_source")
        .agg(
            road_segments=("length", "count"),
            physical_distance_meters=("length", "sum"),
            delivery_cost=("delivery_weight", "sum")
        )
        .reset_index()
    )

    summary["route"] = route_name

    return summary[
        [
            "route",
            "score_source",
            "road_segments",
            "physical_distance_meters",
            "delivery_cost"
        ]
    ]


baseline_summary = summarize_route(
    baseline_route,
    "Shortest-distance baseline"
)

delivery_summary = summarize_route(
    delivery_route,
    "Delivery-aware optimized"
)

route_breakdown = pd.concat(
    [baseline_summary, delivery_summary],
    ignore_index=True
)

route_breakdown["physical_distance_meters"] = (
    route_breakdown["physical_distance_meters"].round(2)
)

route_breakdown["delivery_cost"] = (
    route_breakdown["delivery_cost"].round(2)
)

route_breakdown.to_csv(comparison_file, index=False)

print("Battery Park to South Street Seaport Route Breakdown")
print("----------------------------------------------------")
print(route_breakdown.to_string(index=False))

print("\nFile created:")
print(f"- {comparison_file}")

route_nodes = list(set(baseline_route + delivery_route))

route_longitudes = [
    street_graph.nodes[node]["x"] for node in route_nodes
]

route_latitudes = [
    street_graph.nodes[node]["y"] for node in route_nodes
]

longitude_padding = 0.0012
latitude_padding = 0.0012

west = min(route_longitudes) - longitude_padding
east = max(route_longitudes) + longitude_padding
south = min(route_latitudes) - latitude_padding
north = max(route_latitudes) + latitude_padding

focused_map_file = (
    project_folder / "figures" / "focused_baseline_vs_delivery_route.png"
)

fig, ax = ox.plot_graph_routes(
    street_graph,
    routes=[baseline_route, delivery_route],
    route_colors=["#1f77b4", "#d62728"],
    route_linewidths=[5, 5],
    node_size=0,
    edge_linewidth=0.7,
    bbox=(west, south, east, north),
    show=False,
    close=False
)

ax.set_title(
    "Battery Park to South Street Seaport\n"
    "Shortest-Distance vs. Delivery-Aware Route",
    fontsize=13,
    pad=14
)

legend_items = [
    Line2D(
        [0], [0],
        color="#1f77b4",
        linewidth=4,
        label="Shortest-distance baseline"
    ),
    Line2D(
        [0], [0],
        color="#d62728",
        linewidth=4,
        label="Delivery-aware optimized route"
    )
]

ax.legend(
    handles=legend_items,
    loc="lower left",
    frameon=True,
    fontsize=9
)

fig.savefig(
    focused_map_file,
    dpi=300,
    bbox_inches="tight"
)

plt.close(fig)

print("\nFocused map created:")
print(f"- {focused_map_file}")