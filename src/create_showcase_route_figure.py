from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import networkx as nx
import osmnx as ox
import pandas as pd


project_folder = Path(__file__).resolve().parent.parent
output_folder = project_folder / "data" / "output"
figures_folder = project_folder / "figures"

graph_file = (
    output_folder / "lower_manhattan_component_weighted_network.graphml"
)

summary_file = (
    output_folder / "financial_district_to_chinatown_showcase_summary.csv"
)

breakdown_file = (
    output_folder / "financial_district_to_chinatown_route_breakdown.csv"
)

map_file = (
    figures_folder / "financial_district_to_chinatown_showcase_route.png"
)



street_graph = ox.load_graphml(filepath=str(graph_file))


for start_node, end_node, key, edge_data in street_graph.edges(
    keys=True, data=True
):
    edge_data["length"] = float(edge_data["length"])
    edge_data["delivery_weight"] = float(edge_data["delivery_weight"])
    edge_data["delivery_score"] = float(edge_data["delivery_score"])
    edge_data["components_observed"] = int(edge_data["components_observed"])


origin_name = "Financial District"
destination_name = "Chinatown"

origin_point = (40.7075, -74.0113)
destination_point = (40.7157, -73.9970)

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

optimized_route = nx.dijkstra_path(
    street_graph,
    origin_node,
    destination_node,
    weight="delivery_weight"
)

astar_route = nx.astar_path(
    street_graph,
    origin_node,
    destination_node,
    weight="delivery_weight",
    heuristic=lambda node_1, node_2: ox.distance.great_circle(
        street_graph.nodes[node_1]["y"],
        street_graph.nodes[node_1]["x"],
        street_graph.nodes[node_2]["y"],
        street_graph.nodes[node_2]["x"]
    )
)


def route_metrics(route, weight_name):
    """Calculate total distance, cost, and data coverage for one route."""
    route_edges = ox.routing.route_to_gdf(
        street_graph,
        route,
        weight=weight_name
    ).copy()

    route_edges["length"] = route_edges["length"].astype(float)
    route_edges["delivery_weight"] = route_edges[
        "delivery_weight"
    ].astype(float)

    total_distance = route_edges["length"].sum()
    total_cost = route_edges["delivery_weight"].sum()

    traffic_distance = route_edges.loc[
        route_edges["has_traffic_data"] == "Yes", "length"
    ].sum()

    parking_distance = route_edges.loc[
        route_edges["has_parking_data"] == "Yes", "length"
    ].sum()

    truck_distance = route_edges.loc[
        route_edges["has_truck_data"] == "Yes", "length"
    ].sum()

    two_component_distance = route_edges.loc[
        route_edges["components_observed"].astype(int) >= 2, "length"
    ].sum()

    return {
        "distance_meters": total_distance,
        "delivery_cost": total_cost,
        "traffic_coverage_percent": traffic_distance / total_distance * 100,
        "parking_coverage_percent": parking_distance / total_distance * 100,
        "truck_coverage_percent": truck_distance / total_distance * 100,
        "two_component_coverage_percent": (
            two_component_distance / total_distance * 100
        )
    }


def route_breakdown(route, route_name, weight_name):
    """Summarize distance and cost by number of observed data components."""
    route_edges = ox.routing.route_to_gdf(
        street_graph,
        route,
        weight=weight_name
    ).copy()

    route_edges["length"] = route_edges["length"].astype(float)
    route_edges["delivery_weight"] = route_edges[
        "delivery_weight"
    ].astype(float)

    route_edges["components_observed"] = route_edges[
        "components_observed"
    ].astype(int)

    breakdown = (
        route_edges.groupby("components_observed")
        .agg(
            road_segments=("length", "count"),
            distance_meters=("length", "sum"),
            delivery_cost=("delivery_weight", "sum")
        )
        .reset_index()
    )

    breakdown["route"] = route_name

    return breakdown[
        [
            "route",
            "components_observed",
            "road_segments",
            "distance_meters",
            "delivery_cost"
        ]
    ]


baseline_metrics = route_metrics(baseline_route, "length")
optimized_metrics = route_metrics(optimized_route, "delivery_weight")

distance_change = (
    optimized_metrics["distance_meters"]
    - baseline_metrics["distance_meters"]
)

cost_improvement = (
    baseline_metrics["delivery_cost"]
    - optimized_metrics["delivery_cost"]
)



summary = pd.DataFrame(
    [
        {
            "origin": origin_name,
            "destination": destination_name,
            "baseline_distance_meters": round(
                baseline_metrics["distance_meters"], 2
            ),
            "optimized_distance_meters": round(
                optimized_metrics["distance_meters"], 2
            ),
            "added_distance_meters": round(distance_change, 2),
            "baseline_delivery_cost": round(
                baseline_metrics["delivery_cost"], 2
            ),
            "optimized_delivery_cost": round(
                optimized_metrics["delivery_cost"], 2
            ),
            "delivery_cost_improvement": round(cost_improvement, 2),
            "optimized_traffic_coverage_percent": round(
                optimized_metrics["traffic_coverage_percent"], 2
            ),
            "optimized_parking_coverage_percent": round(
                optimized_metrics["parking_coverage_percent"], 2
            ),
            "optimized_truck_coverage_percent": round(
                optimized_metrics["truck_coverage_percent"], 2
            ),
            "optimized_two_component_coverage_percent": round(
                optimized_metrics["two_component_coverage_percent"], 2
            ),
            "dijkstra_and_astar_agree": optimized_route == astar_route
        }
    ]
)

summary.to_csv(summary_file, index=False)

breakdown = pd.concat(
    [
        route_breakdown(
            baseline_route,
            "Shortest-distance baseline",
            "length"
        ),
        route_breakdown(
            optimized_route,
            "Delivery-aware optimized",
            "delivery_weight"
        )
    ],
    ignore_index=True
)

breakdown["distance_meters"] = breakdown["distance_meters"].round(2)
breakdown["delivery_cost"] = breakdown["delivery_cost"].round(2)

breakdown.to_csv(breakdown_file, index=False)



route_nodes = list(set(baseline_route + optimized_route))

route_longitudes = [
    street_graph.nodes[node]["x"] for node in route_nodes
]

route_latitudes = [
    street_graph.nodes[node]["y"] for node in route_nodes
]

longitude_padding = 0.0013
latitude_padding = 0.0013

west = min(route_longitudes) - longitude_padding
east = max(route_longitudes) + longitude_padding
south = min(route_latitudes) - latitude_padding
north = max(route_latitudes) + latitude_padding

fig, ax = ox.plot_graph_routes(
    street_graph,
    routes=[baseline_route, optimized_route],
    route_colors=["#2f86c1", "#e63946"],
    route_linewidths=[5, 5],
    node_size=0,
    edge_linewidth=0.7,
    bbox=(west, south, east, north),
    show=False,
    close=False
)

# Add visible title on the dark map background
ax.set_title(
    "Financial District to Chinatown\n"
    "Shortest-Distance vs. Delivery-Aware Route",
    fontsize=15,
    color="white",
    pad=18,
    fontweight="bold"
)

# Mark the approximate start and destination
ax.scatter(
    street_graph.nodes[origin_node]["x"],
    street_graph.nodes[origin_node]["y"],
    s=90,
    color="#2f86c1",
    edgecolors="white",
    linewidths=1.2,
    zorder=5
)

ax.scatter(
    street_graph.nodes[destination_node]["x"],
    street_graph.nodes[destination_node]["y"],
    s=90,
    color="#e63946",
    edgecolors="white",
    linewidths=1.2,
    zorder=5
)

ax.annotate(
    "Start",
    (
        street_graph.nodes[origin_node]["x"],
        street_graph.nodes[origin_node]["y"]
    ),
    xytext=(8, 8),
    textcoords="offset points",
    color="white",
    fontsize=9,
    fontweight="bold"
)

ax.annotate(
    "Destination",
    (
        street_graph.nodes[destination_node]["x"],
        street_graph.nodes[destination_node]["y"]
    ),
    xytext=(-62, 8),
    textcoords="offset points",
    color="white",
    fontsize=9,
    fontweight="bold"
)

legend_items = [
    Line2D(
        [0], [0],
        color="#2f86c1",
        linewidth=4,
        label="Shortest-distance baseline"
    ),
    Line2D(
        [0], [0],
        color="#e63946",
        linewidth=4,
        label="Delivery-aware optimized route"
    )
]

legend = ax.legend(
    handles=legend_items,
    loc="upper left",
    frameon=True,
    fontsize=9
)

legend.get_frame().set_facecolor("white")
legend.get_frame().set_alpha(0.92)

# Add a concise result note below the map
fig.text(
    0.5,
    0.015,
    "Adds 35.01 m of travel while reducing modeled delivery cost by 34.62 units",
    ha="center",
    color="white",
    fontsize=10
)

fig.savefig(
    map_file,
    dpi=300,
    bbox_inches="tight",
    facecolor=fig.get_facecolor()
)

plt.close(fig)



print("Showcase Route: Financial District to Chinatown")
print("-----------------------------------------------")
print(summary.to_string(index=False))

print("\nRoute Breakdown by Number of Observed Components")
print("------------------------------------------------")
print(breakdown.to_string(index=False))

print("\nFiles created:")
print(f"- {summary_file}")
print(f"- {breakdown_file}")
print(f"- {map_file}")