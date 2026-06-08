from pathlib import Path
import re

import osmnx as ox
import pandas as pd


project_folder = Path(__file__).resolve().parent.parent
input_folder = project_folder / "data" / "input"
output_folder = project_folder / "data" / "output"

traffic_file = input_folder / "traffic_volume.csv"
truck_file = input_folder / "truck_routes.csv"
parking_file = input_folder / "parking_signs.csv"
graph_file = output_folder / "lower_manhattan_network.graphml"

output_folder.mkdir(parents=True, exist_ok=True)


def normalize_street_name(street_name):
    """Standardize street names for matching across datasets."""
    if pd.isna(street_name):
        return ""

    name = str(street_name).upper().strip()
    name = re.sub(r"\s+", " ", name)
    name = re.sub(r"(\d+)(ST|ND|RD|TH)\b", r"\1", name)

    return name


def calculate_parking_access_score(sign_description):
    """
    Initial delivery curb-access score.
    Higher values mean better access for a delivery vehicle.
    """
    sign_text = str(sign_description).upper()

    if "TRUCK LOADING" in sign_text or "TRUCKS LOADING" in sign_text:
        return 1.00
    elif "COMMERCIAL VEHICLES ONLY" in sign_text:
        return 0.90
    elif "LOADING ONLY" in sign_text:
        return 0.75
    elif "HOTEL LOADING ZONE" in sign_text:
        return 0.40
    else:
        return 0.20


def extract_network_street_names(edges):
    """Extract standardized street names from the road-network edges."""
    names = []

    for edge_name in edges["name"].dropna():
        if isinstance(edge_name, list):
            names.extend(edge_name)
        else:
            names.append(edge_name)

    return {
        normalize_street_name(name)
        for name in names
        if normalize_street_name(name) != ""
    }



traffic_data = pd.read_csv(traffic_file)
truck_data = pd.read_csv(truck_file)
parking_data = pd.read_csv(parking_file)


street_graph = ox.load_graphml(filepath=str(graph_file))
network_edges = ox.graph_to_gdfs(street_graph, nodes=False, edges=True)
network_streets = extract_network_street_names(network_edges)


traffic_data["street_standardized"] = traffic_data["street"].apply(
    normalize_street_name
)

truck_data["street_standardized"] = truck_data["Street"].apply(
    normalize_street_name
)

parking_data["street_standardized"] = parking_data["on_street"].apply(
    normalize_street_name
)


traffic_scores = (
    traffic_data.groupby("street_standardized")
    .agg(average_traffic_volume=("Vol", "mean"))
    .reset_index()
)

minimum_volume = traffic_scores["average_traffic_volume"].min()
maximum_volume = traffic_scores["average_traffic_volume"].max()

traffic_scores["congestion_penalty"] = (
    (traffic_scores["average_traffic_volume"] - minimum_volume)
    / (maximum_volume - minimum_volume)
)


parking_data["parking_access_score"] = parking_data[
    "sign_description"
].apply(calculate_parking_access_score)

parking_scores = (
    parking_data.groupby("street_standardized")
    .agg(
        parking_sign_records=("sign_description", "count"),
        parking_access_score=("parking_access_score", "mean")
    )
    .reset_index()
)

parking_scores["parking_penalty"] = (
    1 - parking_scores["parking_access_score"]
)


truck_data["has_restriction"] = truck_data["Restrictio"].notna()

truck_scores = (
    truck_data.groupby("street_standardized")
    .agg(
        truck_route_segments=("TruckRoute", "count"),
        restricted_segments=("has_restriction", "sum"),
        truck_restriction_risk=("has_restriction", "mean")
    )
    .reset_index()
)


combined_scores = (
    traffic_scores
    .merge(parking_scores, on="street_standardized", how="inner")
    .merge(truck_scores, on="street_standardized", how="inner")
)

combined_scores = combined_scores[
    combined_scores["street_standardized"].isin(network_streets)
].copy()

combined_scores["delivery_cost_score"] = (
    0.40 * combined_scores["congestion_penalty"]
    + 0.30 * combined_scores["parking_penalty"]
    + 0.30 * combined_scores["truck_restriction_risk"]
)

# Round numeric columns for readable output
columns_to_round = [
    "average_traffic_volume",
    "congestion_penalty",
    "parking_access_score",
    "parking_penalty",
    "truck_restriction_risk",
    "delivery_cost_score"
]

combined_scores[columns_to_round] = combined_scores[
    columns_to_round
].round(3)

combined_scores = combined_scores.sort_values(
    by="delivery_cost_score",
    ascending=True
)

output_file = output_folder / "lower_manhattan_corridor_scores.csv"
combined_scores.to_csv(output_file, index=False)

print("Lower Manhattan Delivery Corridor Scores")
print("----------------------------------------")
print(
    combined_scores[
        [
            "street_standardized",
            "average_traffic_volume",
            "congestion_penalty",
            "parking_sign_records",
            "parking_access_score",
            "truck_route_segments",
            "restricted_segments",
            "truck_restriction_risk",
            "delivery_cost_score"
        ]
    ].to_string(index=False)
)

print("\nInterpretation")
print("--------------")

for _, row in combined_scores.iterrows():
    print(
        f"{row['street_standardized']}: delivery cost score "
        f"{row['delivery_cost_score']:.3f}"
    )

print("\nFile created:")
print(f"- {output_file}")