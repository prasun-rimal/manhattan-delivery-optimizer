from pathlib import Path
import re

import osmnx as ox
import pandas as pd

project_folder = Path(__file__).resolve().parent.parent
output_folder = project_folder / "data" / "output"

graph_file = output_folder / "lower_manhattan_network.graphml"
scores_file = output_folder / "lower_manhattan_corridor_scores.csv"


def normalize_street_name(street_name):
    """Standardize street names for matching."""
    if pd.isna(street_name):
        return ""

    name = str(street_name).upper().strip()
    name = re.sub(r"\s+", " ", name)
    name = re.sub(r"(\d+)(ST|ND|RD|TH)\b", r"\1", name)

    return name


def get_edge_street_names(edge_name):
    """
    Return standardized street names for one network edge.
    Some OpenStreetMap edges contain more than one name.
    """
    if isinstance(edge_name, list):
        return [normalize_street_name(name) for name in edge_name]

    return [normalize_street_name(edge_name)]


street_graph = ox.load_graphml(filepath=str(graph_file))
network_edges = ox.graph_to_gdfs(street_graph, nodes=False, edges=True)
corridor_scores = pd.read_csv(scores_file)

scored_streets = set(corridor_scores["street_standardized"])

network_edges = network_edges.reset_index()

network_edges["standardized_names"] = network_edges["name"].apply(
    get_edge_street_names
)

scored_edges = network_edges[
    network_edges["standardized_names"].apply(
        lambda names: any(name in scored_streets for name in names)
    )
].copy()

scored_edges["matched_scored_street"] = scored_edges[
    "standardized_names"
].apply(
    lambda names: next(name for name in names if name in scored_streets)
)

scored_edges = scored_edges.merge(
    corridor_scores[
        ["street_standardized", "delivery_cost_score"]
    ],
    left_on="matched_scored_street",
    right_on="street_standardized",
    how="left"
)

coverage_by_corridor = (
    scored_edges.groupby("matched_scored_street")
    .agg(
        mapped_street_segments=("length", "count"),
        mapped_length_meters=("length", "sum"),
        delivery_cost_score=("delivery_cost_score", "first")
    )
    .reset_index()
)

coverage_by_corridor["mapped_length_meters"] = (
    coverage_by_corridor["mapped_length_meters"].round(2)
)

output_file = output_folder / "scored_corridor_network_coverage.csv"
coverage_by_corridor.to_csv(output_file, index=False)

print("Scored Corridor Coverage in Lower Manhattan Road Network")
print("---------------------------------------------------------")
print(coverage_by_corridor.to_string(index=False))

print("\nTotal Scored Road-Network Edges")
print("--------------------------------")
print(f"Matched scored street segments: {len(scored_edges):,}")
print(f"Total street segments in graph: {len(network_edges):,}")
print(
    f"Percent of graph edges currently scored: "
    f"{(len(scored_edges) / len(network_edges)) * 100:.2f}%"
)

print("\nFile created:")
print(f"- {output_file}")