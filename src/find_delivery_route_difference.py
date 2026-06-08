from pathlib import Path
from itertools import combinations
from time import perf_counter

import networkx as nx
import osmnx as ox
import pandas as pd

project_folder = Path(__file__).resolve().parent.parent
output_folder = project_folder / "data" / "output"
figures_folder = project_folder / "figures"

graph_file = output_folder / "lower_manhattan_weighted_network.graphml"
results_file = output_folder / "delivery_route_comparison_results.csv"
map_file = figures_folder / "baseline_vs_delivery_aware_route.png"

street_graph = ox.load_graphml(filepath=str(graph_file))


for start_node, end_node, key, edge_data in street_graph.edges(
    keys=True, data=True
):
    edge_data["delivery_weight"] = float(edge_data["delivery_weight"])
    edge_data["delivery_score"] = float(edge_data["delivery_score"])

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
    Straight-line distance estimate in meters for A*.
    This remains safe because delivery_weight is always at least
    as large as physical street length.
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


def calculate_route_metrics(route):
    """Calculate physical distance, delivery cost, and observed corridors used."""
    route_edges = ox.routing.route_to_gdf(street_graph, route)

    physical_distance = route_edges["length"].astype(float).sum()
    delivery_cost = route_edges["delivery_weight"].astype(float).sum()

    observed_corridors = sorted(
        {
            source
            for source in route_edges["score_source"]
            if source != "NEUTRAL FALLBACK"
        }
    )

    return physical_distance, delivery_cost, observed_corridors


comparison_records = []
changed_routes = []

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

        astar_start = perf_counter()

        delivery_astar_route = nx.astar_path(
            street_graph,
            origin_node,
            destination_node,
            heuristic=delivery_heuristic,
            weight="delivery_weight"
        )

        astar_runtime = perf_counter() - astar_start

        baseline_distance, baseline_cost, baseline_corridors = (
            calculate_route_metrics(baseline_route)
        )

        delivery_distance, delivery_cost, delivery_corridors = (
            calculate_route_metrics(delivery_dijkstra_route)
        )

        route_changed = baseline_route != delivery_dijkstra_route
        algorithms_agree = delivery_dijkstra_route == delivery_astar_route

        cost_improvement = baseline_cost - delivery_cost
        distance_change = delivery_distance - baseline_distance

        record = {
            "origin": origin_name,
            "destination": destination_name,
            "route_changed": route_changed,
            "dijkstra_and_astar_agree": algorithms_agree,
            "baseline_distance_meters": round(baseline_distance, 2),
            "delivery_route_distance_meters": round(delivery_distance, 2),
            "distance_change_meters": round(distance_change, 2),
            "baseline_delivery_cost": round(baseline_cost, 2),
            "optimized_delivery_cost": round(delivery_cost, 2),
            "delivery_cost_improvement": round(cost_improvement, 2),
            "baseline_observed_corridors": ", ".join(baseline_corridors),
            "optimized_observed_corridors": ", ".join(delivery_corridors),
            "dijkstra_runtime_seconds": dijkstra_runtime,
            "astar_runtime_seconds": astar_runtime,
        }

        comparison_records.append(record)

        if route_changed and cost_improvement > 0:
            changed_routes.append(
                {
                    "record": record,
                    "baseline_route": baseline_route,
                    "delivery_route": delivery_dijkstra_route,
                }
            )

    except nx.NetworkXNoPath:
        print(f"No route found: {origin_name} to {destination_name}")

comparison_results = pd.DataFrame(comparison_records)
comparison_results.to_csv(results_file, index=False)

print("Delivery-Aware Route Search")
print("---------------------------")
print(f"Delivery requests tested: {len(comparison_results):,}")
print(
    "Requests where delivery weighting changed the route: "
    f"{comparison_results['route_changed'].sum():,}"
)
print(
    "Requests where Dijkstra and A* agreed: "
    f"{comparison_results['dijkstra_and_astar_agree'].sum():,}"
)

if changed_routes:
    best_example = max(
        changed_routes,
        key=lambda item: item["record"]["delivery_cost_improvement"]
    )

    best_record = best_example["record"]
    baseline_route = best_example["baseline_route"]
    delivery_route = best_example["delivery_route"]

    print("\nBest Route Difference Example")
    print("-----------------------------")
    print(f"Origin: {best_record['origin']}")
    print(f"Destination: {best_record['destination']}")
    print(
        f"Baseline physical distance: "
        f"{best_record['baseline_distance_meters']:.2f} meters"
    )
    print(
        f"Delivery-aware physical distance: "
        f"{best_record['delivery_route_distance_meters']:.2f} meters"
    )
    print(
        f"Added travel distance: "
        f"{best_record['distance_change_meters']:.2f} meters"
    )
    print(
        f"Baseline delivery cost: "
        f"{best_record['baseline_delivery_cost']:.2f}"
    )
    print(
        f"Optimized delivery cost: "
        f"{best_record['optimized_delivery_cost']:.2f}"
    )
    print(
        f"Delivery-cost improvement: "
        f"{best_record['delivery_cost_improvement']:.2f}"
    )
    print(
        f"Baseline observed corridors: "
        f"{best_record['baseline_observed_corridors'] or 'None'}"
    )
    print(
        f"Optimized observed corridors: "
        f"{best_record['optimized_observed_corridors'] or 'None'}"
    )

    ox.plot_graph_routes(
        street_graph,
        routes=[baseline_route, delivery_route],
        route_colors=["#1f77b4", "#d62728"],
        route_linewidths=[4, 4],
        node_size=0,
        edge_linewidth=0.5,
        show=False,
        close=True,
        save=True,
        filepath=str(map_file),
        dpi=300
    )

    print("\nMap legend:")
    print("Blue route = shortest physical distance baseline")
    print("Red route = delivery-aware optimized route")

    print("\nFiles created:")
    print(f"- {results_file}")
    print(f"- {map_file}")

else:
    print("\nNo route difference was found among the sample delivery requests.")
    print(
        "This does not mean the weighting failed. It means we may need "
        "additional scored corridors or a stronger delivery-priority setting."
    )

    print("\nFile created:")
    print(f"- {results_file}")