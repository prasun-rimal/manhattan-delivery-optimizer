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

showcase_results_file = (
    output_folder / "showcase_route_candidates.csv"
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
    edge_data["congestion_penalty"] = float(edge_data["congestion_penalty"])
    edge_data["parking_penalty"] = float(edge_data["parking_penalty"])
    edge_data["truck_penalty"] = float(edge_data["truck_penalty"])
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


def apply_fallback_weight(fallback_value):
    """Recalculate delivery weights for one traffic fallback assumption."""
    for start_node, end_node, key, edge_data in street_graph.edges(
        keys=True, data=True
    ):
        if edge_data["has_traffic_data"] == "Yes":
            congestion_penalty = edge_data["congestion_penalty"]
        else:
            congestion_penalty = fallback_value

        delivery_score = (
            CONGESTION_WEIGHT * congestion_penalty
            + PARKING_WEIGHT * edge_data["parking_penalty"]
            + TRUCK_WEIGHT * edge_data["truck_penalty"]
        )

        edge_data["showcase_delivery_weight"] = (
            edge_data["length"] * (1 + delivery_score)
        )


def calculate_metrics(route):
    """Calculate distance, modeled cost, and data coverage for one route."""
    route_edges = ox.routing.route_to_gdf(
        street_graph,
        route,
        weight="showcase_delivery_weight"
    ).copy()

    route_edges["length"] = route_edges["length"].astype(float)
    route_edges["showcase_delivery_weight"] = route_edges[
        "showcase_delivery_weight"
    ].astype(float)
    route_edges["components_observed"] = route_edges[
        "components_observed"
    ].astype(int)

    total_distance = route_edges["length"].sum()

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
        route_edges["components_observed"] >= 2,
        "length"
    ].sum()

    return {
        "distance_meters": total_distance,
        "delivery_cost": route_edges["showcase_delivery_weight"].sum(),
        "traffic_coverage_percent": traffic_distance / total_distance * 100,
        "parking_coverage_percent": parking_distance / total_distance * 100,
        "truck_coverage_percent": truck_distance / total_distance * 100,
        "two_component_coverage_percent": (
            two_component_distance / total_distance * 100
        )
    }




records = []

for fallback_value in TRAFFIC_FALLBACK_VALUES:
    apply_fallback_weight(fallback_value)

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
            weight="showcase_delivery_weight"
        )

        baseline_metrics = calculate_metrics(baseline_route)
        optimized_metrics = calculate_metrics(optimized_route)

        records.append(
            {
                "origin": origin_name,
                "destination": destination_name,
                "traffic_fallback_penalty": fallback_value,
                "route_changed": baseline_route != optimized_route,
                "optimized_route_signature": "|".join(
                    str(node) for node in optimized_route
                ),
                "distance_change_meters": round(
                    optimized_metrics["distance_meters"]
                    - baseline_metrics["distance_meters"],
                    2
                ),
                "delivery_cost_improvement": round(
                    baseline_metrics["delivery_cost"]
                    - optimized_metrics["delivery_cost"],
                    2
                ),
                "traffic_coverage_percent": round(
                    optimized_metrics["traffic_coverage_percent"], 2
                ),
                "parking_coverage_percent": round(
                    optimized_metrics["parking_coverage_percent"], 2
                ),
                "truck_coverage_percent": round(
                    optimized_metrics["truck_coverage_percent"], 2
                ),
                "two_component_coverage_percent": round(
                    optimized_metrics["two_component_coverage_percent"], 2
                )
            }
        )

all_results = pd.DataFrame(records)



candidate_summary = (
    all_results.groupby(["origin", "destination"])
    .agg(
        changed_under_all_fallbacks=("route_changed", "all"),
        fallback_settings_changed=("route_changed", "sum"),
        distinct_optimized_routes=("optimized_route_signature", "nunique"),
        minimum_cost_improvement=("delivery_cost_improvement", "min"),
        average_cost_improvement=("delivery_cost_improvement", "mean"),
        maximum_extra_distance=("distance_change_meters", "max"),
        minimum_traffic_coverage=("traffic_coverage_percent", "min"),
        maximum_traffic_coverage=("traffic_coverage_percent", "max"),
        minimum_parking_coverage=("parking_coverage_percent", "min"),
        minimum_truck_coverage=("truck_coverage_percent", "min"),
        minimum_two_component_coverage=(
            "two_component_coverage_percent", "min"
        )
    )
    .reset_index()
)

candidate_summary = candidate_summary.sort_values(
    by=[
        "changed_under_all_fallbacks",
        "distinct_optimized_routes",
        "minimum_two_component_coverage",
        "minimum_cost_improvement"
    ],
    ascending=[False, True, False, False]
)

candidate_summary[
    [
        "minimum_cost_improvement",
        "average_cost_improvement",
        "maximum_extra_distance",
        "minimum_traffic_coverage",
        "maximum_traffic_coverage",
        "minimum_parking_coverage",
        "minimum_truck_coverage",
        "minimum_two_component_coverage"
    ]
] = candidate_summary[
    [
        "minimum_cost_improvement",
        "average_cost_improvement",
        "maximum_extra_distance",
        "minimum_traffic_coverage",
        "maximum_traffic_coverage",
        "minimum_parking_coverage",
        "minimum_truck_coverage",
        "minimum_two_component_coverage"
    ]
].round(2)

candidate_summary.to_csv(showcase_results_file, index=False)

print("Showcase Route Candidate Search")
print("-------------------------------")
print(
    "A strong showcase candidate changes under all traffic fallback "
    "assumptions, improves modeled delivery cost, and uses broad "
    "real-data coverage."
)

print("\nTop 10 Route Candidates")
print("-----------------------")
print(
    candidate_summary.head(10)[
        [
            "origin",
            "destination",
            "changed_under_all_fallbacks",
            "distinct_optimized_routes",
            "minimum_cost_improvement",
            "maximum_extra_distance",
            "minimum_traffic_coverage",
            "maximum_traffic_coverage",
            "minimum_parking_coverage",
            "minimum_truck_coverage",
            "minimum_two_component_coverage"
        ]
    ].to_string(index=False)
)

print("\nFile created:")
print(f"- {showcase_results_file}")