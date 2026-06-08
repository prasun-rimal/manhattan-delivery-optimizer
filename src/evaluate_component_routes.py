from pathlib import Path
from itertools import combinations
from time import perf_counter

import networkx as nx
import osmnx as ox
import pandas as pd


project_folder = Path(__file__).resolve().parent.parent
output_folder = project_folder / "data" / "output"

graph_file = (
    output_folder / "lower_manhattan_component_weighted_network.graphml"
)

results_file = (
    output_folder / "component_route_comparison_results.csv"
)

best_breakdown_file = (
    output_folder / "best_component_route_breakdown.csv"
)



street_graph = ox.load_graphml(filepath=str(graph_file))

# GraphML reloads custom values as text, so convert them back to numbers.
for start_node, end_node, key, edge_data in street_graph.edges(
    keys=True, data=True
):
    edge_data["length"] = float(edge_data["length"])
    edge_data["delivery_weight"] = float(edge_data["delivery_weight"])
    edge_data["delivery_score"] = float(edge_data["delivery_score"])
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


def delivery_heuristic(node_1, node_2):
    """
    Straight-line distance estimate for A*.
    Delivery-weighted distance is always at least physical distance,
    so this remains a valid lower-bound estimate.
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


def get_route_edges(route, weight_name):
    """
    Convert a route node list into its selected street segments.
    The weight name ensures that parallel-road choices match
    the routing objective used.
    """
    return ox.routing.route_to_gdf(
        street_graph,
        route,
        weight=weight_name
    ).copy()


def calculate_route_metrics(route, weight_name):
    """Calculate distance, modeled cost, and real-data coverage."""
    route_edges = get_route_edges(route, weight_name)

    route_edges["length"] = route_edges["length"].astype(float)
    route_edges["delivery_weight"] = route_edges["delivery_weight"].astype(float)

    total_distance = route_edges["length"].sum()
    total_delivery_cost = route_edges["delivery_weight"].sum()

    traffic_distance = route_edges.loc[
        route_edges["has_traffic_data"] == "Yes", "length"
    ].sum()

    parking_distance = route_edges.loc[
        route_edges["has_parking_data"] == "Yes", "length"
    ].sum()

    truck_distance = route_edges.loc[
        route_edges["has_truck_data"] == "Yes", "length"
    ].sum()

    at_least_one_component_distance = route_edges.loc[
        route_edges["components_observed"].astype(int) >= 1, "length"
    ].sum()

    at_least_two_components_distance = route_edges.loc[
        route_edges["components_observed"].astype(int) >= 2, "length"
    ].sum()

    return {
        "distance_meters": total_distance,
        "delivery_cost": total_delivery_cost,
        "traffic_coverage_percent": (
            traffic_distance / total_distance * 100
        ),
        "parking_coverage_percent": (
            parking_distance / total_distance * 100
        ),
        "truck_coverage_percent": (
            truck_distance / total_distance * 100
        ),
        "one_or_more_components_percent": (
            at_least_one_component_distance / total_distance * 100
        ),
        "two_or_more_components_percent": (
            at_least_two_components_distance / total_distance * 100
        ),
    }


def create_route_breakdown(route, route_name, weight_name):
    """Summarize route distance and delivery cost by data coverage level."""
    route_edges = get_route_edges(route, weight_name)

    route_edges["length"] = route_edges["length"].astype(float)
    route_edges["delivery_weight"] = route_edges["delivery_weight"].astype(float)
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




comparison_records = []
changed_route_examples = []

for origin_name, destination_name in combinations(sample_locations.keys(), 2):
    origin_node = location_nodes[origin_name]
    destination_node = location_nodes[destination_name]

    try:
       
        baseline_route = nx.dijkstra_path(
            street_graph,
            origin_node,
            destination_node,
            weight="length"
        )

      
        dijkstra_start = perf_counter()

        delivery_dijkstra_route = nx.dijkstra_path(
            street_graph,
            origin_node,
            destination_node,
            weight="delivery_weight"
        )

        dijkstra_runtime = perf_counter() - dijkstra_start

        # Delivery-aware route using A*
        astar_start = perf_counter()

        delivery_astar_route = nx.astar_path(
            street_graph,
            origin_node,
            destination_node,
            heuristic=delivery_heuristic,
            weight="delivery_weight"
        )

        astar_runtime = perf_counter() - astar_start

        baseline_metrics = calculate_route_metrics(
            baseline_route,
            "length"
        )

        optimized_metrics = calculate_route_metrics(
            delivery_dijkstra_route,
            "delivery_weight"
        )

        route_changed = baseline_route != delivery_dijkstra_route
        algorithms_agree = delivery_dijkstra_route == delivery_astar_route

        cost_improvement = (
            baseline_metrics["delivery_cost"]
            - optimized_metrics["delivery_cost"]
        )

        distance_change = (
            optimized_metrics["distance_meters"]
            - baseline_metrics["distance_meters"]
        )

        record = {
            "origin": origin_name,
            "destination": destination_name,
            "route_changed": route_changed,
            "dijkstra_and_astar_agree": algorithms_agree,
            "baseline_distance_meters": round(
                baseline_metrics["distance_meters"], 2
            ),
            "optimized_distance_meters": round(
                optimized_metrics["distance_meters"], 2
            ),
            "distance_change_meters": round(distance_change, 2),
            "baseline_delivery_cost": round(
                baseline_metrics["delivery_cost"], 2
            ),
            "optimized_delivery_cost": round(
                optimized_metrics["delivery_cost"], 2
            ),
            "delivery_cost_improvement": round(cost_improvement, 2),
            "baseline_real_data_coverage_percent": round(
                baseline_metrics["one_or_more_components_percent"], 2
            ),
            "optimized_real_data_coverage_percent": round(
                optimized_metrics["one_or_more_components_percent"], 2
            ),
            "baseline_two_plus_components_percent": round(
                baseline_metrics["two_or_more_components_percent"], 2
            ),
            "optimized_two_plus_components_percent": round(
                optimized_metrics["two_or_more_components_percent"], 2
            ),
            "optimized_traffic_coverage_percent": round(
                optimized_metrics["traffic_coverage_percent"], 2
            ),
            "optimized_parking_coverage_percent": round(
                optimized_metrics["parking_coverage_percent"], 2
            ),
            "optimized_truck_coverage_percent": round(
                optimized_metrics["truck_coverage_percent"], 2
            ),
            "dijkstra_runtime_seconds": dijkstra_runtime,
            "astar_runtime_seconds": astar_runtime,
        }

        comparison_records.append(record)

        if route_changed and cost_improvement > 0:
            changed_route_examples.append(
                {
                    "record": record,
                    "baseline_route": baseline_route,
                    "optimized_route": delivery_dijkstra_route
                }
            )

    except nx.NetworkXNoPath:
        print(f"No route found: {origin_name} to {destination_name}")



comparison_results = pd.DataFrame(comparison_records)
comparison_results.to_csv(results_file, index=False)

print("Expanded Component-Based Route Evaluation")
print("-----------------------------------------")
print(f"Delivery requests tested: {len(comparison_results):,}")
print(
    "Requests where delivery weighting changed the route: "
    f"{comparison_results['route_changed'].sum():,}"
)
print(
    "Requests where Dijkstra and A* agreed: "
    f"{comparison_results['dijkstra_and_astar_agree'].sum():,}"
)

if changed_route_examples:
    best_example = max(
        changed_route_examples,
        key=lambda example: example["record"]["delivery_cost_improvement"]
    )

    best_record = best_example["record"]
    baseline_route = best_example["baseline_route"]
    optimized_route = best_example["optimized_route"]

    print("\nBest Route Difference Example")
    print("-----------------------------")

    for key, value in best_record.items():
        print(f"{key}: {value}")

    baseline_breakdown = create_route_breakdown(
        baseline_route,
        "Shortest-distance baseline",
        "length"
    )

    optimized_breakdown = create_route_breakdown(
        optimized_route,
        "Delivery-aware optimized",
        "delivery_weight"
    )

    route_breakdown = pd.concat(
        [baseline_breakdown, optimized_breakdown],
        ignore_index=True
    )

    route_breakdown["distance_meters"] = (
        route_breakdown["distance_meters"].round(2)
    )

    route_breakdown["delivery_cost"] = (
        route_breakdown["delivery_cost"].round(2)
    )

    route_breakdown.to_csv(best_breakdown_file, index=False)

    print("\nBest Route Data-Coverage Breakdown")
    print("----------------------------------")
    print(route_breakdown.to_string(index=False))

    print("\nFiles created:")
    print(f"- {results_file}")
    print(f"- {best_breakdown_file}")

else:
    print("\nNo changed route lowered modeled delivery cost.")
    print(f"\nFile created:\n- {results_file}")