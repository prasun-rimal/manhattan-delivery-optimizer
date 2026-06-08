from pathlib import Path
import re

import osmnx as ox
import pandas as pd

project_folder = Path(__file__).resolve().parent.parent
output_folder = project_folder / "data" / "output"

graph_file = output_folder / "lower_manhattan_network.graphml"
scores_file = output_folder / "lower_manhattan_corridor_scores.csv"

weighted_graph_file = output_folder / "lower_manhattan_weighted_network.graphml"
summary_file = output_folder / "weighted_network_score_summary.csv"

DELIVERY_PRIORITY = 1.0


def normalize_street_name(street_name):
    """Standardize street names for matching."""
    if pd.isna(street_name):
        return ""

    name = str(street_name).upper().strip()
    name = re.sub(r"\s+", " ", name)
    name = re.sub(r"(\d+)(ST|ND|RD|TH)\b", r"\1", name)

    return name


def get_edge_street_names(edge_name):
    """Return possible standardized names for one map edge."""
    if isinstance(edge_name, list):
        return [normalize_street_name(name) for name in edge_name]

    return [normalize_street_name(edge_name)]


street_graph = ox.load_graphml(filepath=str(graph_file))
corridor_scores = pd.read_csv(scores_file)

observed_score_lookup = dict(
    zip(
        corridor_scores["street_standardized"],
        corridor_scores["delivery_cost_score"]
    )
)

neutral_fallback_score = corridor_scores["delivery_cost_score"].mean()

print("Creating Delivery-Weighted Road Network")
print("---------------------------------------")
print(f"Observed corridor scores: {observed_score_lookup}")
print(f"Neutral fallback score: {neutral_fallback_score:.3f}")
print(f"Delivery priority multiplier: {DELIVERY_PRIORITY:.1f}")

edge_summary_records = []

for start_node, end_node, key, edge_data in street_graph.edges(keys=True, data=True):
    edge_names = get_edge_street_names(edge_data.get("name", ""))

    matched_street = None

    for name in edge_names:
        if name in observed_score_lookup:
            matched_street = name
            break

    if matched_street is not None:
        delivery_score = observed_score_lookup[matched_street]
        score_source = matched_street
        has_observed_score = "Yes"
    else:
        delivery_score = neutral_fallback_score
        score_source = "NEUTRAL FALLBACK"
        has_observed_score = "No"

    physical_length = float(edge_data["length"])

    delivery_weight = physical_length * (
        1 + DELIVERY_PRIORITY * delivery_score
    )

    edge_data["delivery_score"] = float(delivery_score)
    edge_data["delivery_weight"] = float(delivery_weight)
    edge_data["score_source"] = score_source
    edge_data["has_observed_score"] = has_observed_score

    edge_summary_records.append(
        {
            "score_source": score_source,
            "has_observed_score": has_observed_score,
            "street_segments": 1,
            "mapped_length_meters": physical_length
        }
    )

edge_summary = pd.DataFrame(edge_summary_records)

weighted_network_summary = (
    edge_summary.groupby(["score_source", "has_observed_score"])
    .agg(
        street_segments=("street_segments", "sum"),
        mapped_length_meters=("mapped_length_meters", "sum")
    )
    .reset_index()
)

weighted_network_summary["mapped_length_meters"] = (
    weighted_network_summary["mapped_length_meters"].round(2)
)

ox.save_graphml(street_graph, filepath=str(weighted_graph_file))
weighted_network_summary.to_csv(summary_file, index=False)

print("\nWeighted Network Summary")
print("------------------------")
print(weighted_network_summary.to_string(index=False))

print("\nFiles created:")
print(f"- {weighted_graph_file}")
print(f"- {summary_file}")