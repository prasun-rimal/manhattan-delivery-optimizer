from pathlib import Path
from itertools import combinations

import networkx as nx
import osmnx as ox
import pandas as pd



project_folder = Path(__file__).resolve().parent.parent
output_folder = project_folder / "data" / "output"

graph_file = (
    output_folder / "lower_manhattan_component_weighted_network.graphml"
)

results_file = (
    output_folder / "traffic_fallback_sensitivity_results.csv"
)


CONGESTION_WEIGHT = 0.40
PARKING_WEIGHT = 0.30
TRUCK_WEIGHT = 0.30


TRAFFIC_FALLBACK_VALUES = [0.25, 0.50, 0.75]


street_graph = ox.load_graphml(filepath=str(graph_file))

for start_node, end_node, key, edge_data in street_graph.edges(
    keys=True, data=True
):
    edge_data["length"] = float(edge_data["length"])
    edge_data["parking_penalty"] = float(edge_data["parking_penalty"])
    edge_data["truck_penalty"] = float(edge_data["truck_penalty"])
    edge_data["congestion_penalty"] = float(edge_data["congestion_penalty"])
    edge_data["components_observed"] = int(edge_data["components_observed"])



sample_locations = {
    "Battery Park": (40.7033, -74.0170),
    "Financial District": (40.7075, -74.0113),
    "South Street Seaport": (40.7068, -74.0035),
    "Civic Center": (40.7135, -74.0055),
    "Chinatown": (40.7157, -73.9970),
    "Lower East Side": (40.7163, -73.9895),
    "East Village South": (40.7220, -73.9865),
}

location_nodes = {}

for location_name, point in sample_locations.items():
    location_nodes[location_name] = ox.distance.nearest_nodes(
        street_graph,
        X=point[1],
        Y=point[0]
    )


def apply_traffic_fallback(graph, fallback_value):
    """
    Recalculate delivery weights using a chosen penalty for streets
    without observed traffic information.
    """
    for start_node, end_node, key, edge_data in graph.edges(
        keys=True, data=True
    ):
        if edge_data["has_traffic_data"] == "Yes":
            congestion_penalty = float(edge_data["congestion_penalty"])
        else:
            congestion_penalty = fallback_value

        parking_penalty = float(edge_data["parking_penalty"])
        truck_penalty = float(edge_data["truck_penalty"])

        delivery_score = (
            CONGESTION_WEIGHT * congestion_penalty
            + PARKING_WEIGHT * parking_penalty
            + TRUCK_WEIGHT * truck_penalty
        )

        physical_length = float(edge_data["length"])
        delivery_weight = physical_length * (1 + delivery_score)

        edge_data["sensitivity_delivery_score"] = delivery_score
        edge_data["sensitivity_delivery_weight"] = delivery_weight


def calculate_route_metrics(graph, route, weight_name):
    """Calculate distance, modeled cost, and observed traffic coverage."""
    route_edges = ox.routing.route_to_gdf(
        graph,
        route,
        weight=weight_name
    ).copy()

    route_edges["length"] = route_edges["length"].astype(float)
    route_edges["sensitivity_delivery_weight"] = route_edges[
        "sensitivity_delivery_weight"
    ].astype(float)

    total_distance = route_edges["length"].sum()

    traffic_distance = route_edges.loc[
        route_edges["has_traffic_data"] == "Yes",
        "length"
    ].sum()

    return {
        "distance_meters": total_distance,
        "delivery_cost": route_edges["sensitivity_delivery_weight"].sum(),
        "traffic_coverage_percent": (
            traffic_distance / total_distance * 100
        )
    }



results = []

for fallback_value in TRAFFIC_FALLBACK_VALUES:
    apply_traffic_fallback(street_graph, fallback_value)

    for origin_name, destination_name in combinations(
        sample_locations.keys(), 2
    ):
        origin_node = location_nodes[origin_name]
        destination_node = location_nodes[destination_name]

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
            weight="sensitivity_delivery_weight"
        )

        baseline_metrics = calculate_route_metrics(
            street_graph,
            baseline_route,
            "length"
        )

        optimized_metrics = calculate_route_metrics(
            street_graph,
            optimized_route,
            "sensitivity_delivery_weight"
        )

        results.append(
            {
                "traffic_fallback_penalty": fallback_value,
                "origin": origin_name,
                "destination": destination_name,
                "route_changed": baseline_route != optimized_route,
                "baseline_distance_meters": round(
                    baseline_metrics["distance_meters"], 2
                ),
                "optimized_distance_meters": round(
                    optimized_metrics["distance_meters"], 2
                ),
                "distance_change_meters": round(
                    optimized_metrics["distance_meters"]
                    - baseline_metrics["distance_meters"],
                    2
                ),
                "baseline_delivery_cost": round(
                    baseline_metrics["delivery_cost"], 2
                ),
                "optimized_delivery_cost": round(
                    optimized_metrics["delivery_cost"], 2
                ),
                "delivery_cost_improvement": round(
                    baseline_metrics["delivery_cost"]
                    - optimized_metrics["delivery_cost"],
                    2
                ),
                "optimized_traffic_coverage_percent": round(
                    optimized_metrics["traffic_coverage_percent"], 2
                )
            }
        )


sensitivity_results = pd.DataFrame(results)
sensitivity_results.to_csv(results_file, index=False)

summary = (
    sensitivity_results.groupby("traffic_fallback_penalty")
    .agg(
        routes_tested=("route_changed", "count"),
        routes_changed=("route_changed", "sum"),
        average_cost_improvement=("delivery_cost_improvement", "mean"),
        maximum_cost_improvement=("delivery_cost_improvement", "max"),
        average_optimized_traffic_coverage=(
            "optimized_traffic_coverage_percent", "mean"
        )
    )
    .reset_index()
)

summary[
    [
        "average_cost_improvement",
        "maximum_cost_improvement",
        "average_optimized_traffic_coverage"
    ]
] = summary[
    [
        "average_cost_improvement",
        "maximum_cost_improvement",
        "average_optimized_traffic_coverage"
    ]
].round(2)

print("Traffic Fallback Sensitivity Analysis")
print("-------------------------------------")
print(summary.to_string(index=False))

print("\nFinancial District to East Village South")
print("----------------------------------------")
focus_route = sensitivity_results[
    (sensitivity_results["origin"] == "Financial District")
    & (sensitivity_results["destination"] == "East Village South")
]

print(focus_route.to_string(index=False))

print("\nFile created:")
print(f"- {results_file}")