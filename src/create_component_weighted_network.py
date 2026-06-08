from pathlib import Path
import re

import osmnx as ox
import pandas as pd



project_folder = Path(__file__).resolve().parent.parent
input_folder = project_folder / "data" / "input"
output_folder = project_folder / "data" / "output"

traffic_file = input_folder / "traffic_volume.csv"
parking_file = input_folder / "parking_signs.csv"
truck_file = input_folder / "truck_routes.csv"

graph_file = output_folder / "lower_manhattan_network.graphml"

weighted_graph_file = (
    output_folder / "lower_manhattan_component_weighted_network.graphml"
)

street_score_file = (
    output_folder / "lower_manhattan_component_street_scores.csv"
)

edge_coverage_file = (
    output_folder / "component_weighted_network_coverage.csv"
)

output_folder.mkdir(parents=True, exist_ok=True)



CONGESTION_WEIGHT = 0.40
PARKING_WEIGHT = 0.30
TRUCK_WEIGHT = 0.30

NEUTRAL_CONGESTION_PENALTY = 0.50
NEUTRAL_PARKING_PENALTY = 0.50
NEUTRAL_TRUCK_PENALTY = 0.50

DELIVERY_PRIORITY = 1.0




def normalize_street_name(street_name):
    """Standardize street names for matching across files and road network."""
    if pd.isna(street_name):
        return ""

    name = str(street_name).upper().strip()
    name = re.sub(r"\s+", " ", name)

   
    name = re.sub(r"(\d+)(ST|ND|RD|TH)\b", r"\1", name)

    return name


def calculate_parking_access_score(sign_description):
    """
    Initial curb-access score.
    Higher values represent stronger delivery/loading access.
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


def get_edge_street_names(edge_name):
    """Return standardized possible street names for one map edge."""
    if isinstance(edge_name, list):
        return [
            normalize_street_name(name)
            for name in edge_name
            if normalize_street_name(name) != ""
        ]

    standardized_name = normalize_street_name(edge_name)

    if standardized_name == "":
        return []

    return [standardized_name]


def choose_matched_street(edge_names, score_lookup):
    """
    Return the first edge street name that appears in a data-score dictionary.
    """
    for name in edge_names:
        if name in score_lookup:
            return name

    return None



traffic_data = pd.read_csv(traffic_file)
parking_data = pd.read_csv(parking_file)
truck_data = pd.read_csv(truck_file)

street_graph = ox.load_graphml(filepath=str(graph_file))


traffic_data["street_standardized"] = traffic_data["street"].apply(
    normalize_street_name
)

parking_data["street_standardized"] = parking_data["on_street"].apply(
    normalize_street_name
)

truck_data["street_standardized"] = truck_data["Street"].apply(
    normalize_street_name
)



traffic_scores = (
    traffic_data.groupby("street_standardized")
    .agg(
        average_traffic_volume=("Vol", "mean")
    )
    .reset_index()
)

minimum_volume = traffic_scores["average_traffic_volume"].min()
maximum_volume = traffic_scores["average_traffic_volume"].max()

traffic_scores["congestion_penalty"] = (
    (traffic_scores["average_traffic_volume"] - minimum_volume)
    / (maximum_volume - minimum_volume)
)

traffic_lookup = traffic_scores.set_index(
    "street_standardized"
)["congestion_penalty"].to_dict()

traffic_volume_lookup = traffic_scores.set_index(
    "street_standardized"
)["average_traffic_volume"].to_dict()



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

parking_lookup = parking_scores.set_index(
    "street_standardized"
)["parking_penalty"].to_dict()

parking_access_lookup = parking_scores.set_index(
    "street_standardized"
)["parking_access_score"].to_dict()

parking_records_lookup = parking_scores.set_index(
    "street_standardized"
)["parking_sign_records"].to_dict()


truck_data["has_restriction"] = truck_data["Restrictio"].notna()

truck_scores = (
    truck_data.groupby("street_standardized")
    .agg(
        truck_route_segments=("TruckRoute", "count"),
        restricted_segments=("has_restriction", "sum"),
        truck_restriction_penalty=("has_restriction", "mean")
    )
    .reset_index()
)

truck_lookup = truck_scores.set_index(
    "street_standardized"
)["truck_restriction_penalty"].to_dict()

truck_segments_lookup = truck_scores.set_index(
    "street_standardized"
)["truck_route_segments"].to_dict()

restricted_segments_lookup = truck_scores.set_index(
    "street_standardized"
)["restricted_segments"].to_dict()



edge_records = []

for start_node, end_node, key, edge_data in street_graph.edges(
    keys=True, data=True
):
    edge_names = get_edge_street_names(edge_data.get("name", ""))

    traffic_street = choose_matched_street(edge_names, traffic_lookup)
    parking_street = choose_matched_street(edge_names, parking_lookup)
    truck_street = choose_matched_street(edge_names, truck_lookup)

    
    if traffic_street is not None:
        congestion_penalty = float(traffic_lookup[traffic_street])
        has_traffic_data = "Yes"
    else:
        congestion_penalty = NEUTRAL_CONGESTION_PENALTY
        has_traffic_data = "No"

    
    if parking_street is not None:
        parking_penalty = float(parking_lookup[parking_street])
        has_parking_data = "Yes"
    else:
        parking_penalty = NEUTRAL_PARKING_PENALTY
        has_parking_data = "No"

  
    if truck_street is not None:
        truck_penalty = float(truck_lookup[truck_street])
        has_truck_data = "Yes"
    else:
        truck_penalty = NEUTRAL_TRUCK_PENALTY
        has_truck_data = "No"

    components_observed = sum(
        [
            has_traffic_data == "Yes",
            has_parking_data == "Yes",
            has_truck_data == "Yes"
        ]
    )

    delivery_score = (
        CONGESTION_WEIGHT * congestion_penalty
        + PARKING_WEIGHT * parking_penalty
        + TRUCK_WEIGHT * truck_penalty
    )

    physical_length = float(edge_data["length"])

    delivery_weight = physical_length * (
        1 + DELIVERY_PRIORITY * delivery_score
    )


    edge_data["congestion_penalty"] = float(congestion_penalty)
    edge_data["parking_penalty"] = float(parking_penalty)
    edge_data["truck_penalty"] = float(truck_penalty)
    edge_data["delivery_score"] = float(delivery_score)
    edge_data["delivery_weight"] = float(delivery_weight)

    edge_data["has_traffic_data"] = has_traffic_data
    edge_data["has_parking_data"] = has_parking_data
    edge_data["has_truck_data"] = has_truck_data
    edge_data["components_observed"] = int(components_observed)

    edge_records.append(
        {
            "street_names": ", ".join(edge_names) if edge_names else "UNNAMED",
            "traffic_street_match": traffic_street or "",
            "parking_street_match": parking_street or "",
            "truck_street_match": truck_street or "",
            "has_traffic_data": has_traffic_data,
            "has_parking_data": has_parking_data,
            "has_truck_data": has_truck_data,
            "components_observed": components_observed,
            "congestion_penalty": congestion_penalty,
            "parking_penalty": parking_penalty,
            "truck_penalty": truck_penalty,
            "delivery_score": delivery_score,
            "physical_length_meters": physical_length,
            "delivery_weight": delivery_weight
        }
    )

edge_results = pd.DataFrame(edge_records)


coverage_summary = (
    edge_results.groupby("components_observed")
    .agg(
        mapped_street_segments=("physical_length_meters", "count"),
        mapped_length_meters=("physical_length_meters", "sum")
    )
    .reset_index()
    .sort_values("components_observed")
)

coverage_summary["mapped_length_meters"] = (
    coverage_summary["mapped_length_meters"].round(2)
)

total_edges = len(edge_results)

coverage_summary["percent_of_network_edges"] = (
    coverage_summary["mapped_street_segments"] / total_edges * 100
).round(2)


component_coverage = pd.DataFrame(
    {
        "component": [
            "Traffic observations",
            "Parking/loading signs",
            "Official truck-route data"
        ],
        "matched_edges": [
            (edge_results["has_traffic_data"] == "Yes").sum(),
            (edge_results["has_parking_data"] == "Yes").sum(),
            (edge_results["has_truck_data"] == "Yes").sum()
        ]
    }
)

component_coverage["percent_of_network_edges"] = (
    component_coverage["matched_edges"] / total_edges * 100
).round(2)



street_level_summary = (
    edge_results[edge_results["street_names"] != "UNNAMED"]
    .groupby("street_names")
    .agg(
        mapped_segments=("physical_length_meters", "count"),
        mapped_length_meters=("physical_length_meters", "sum"),
        components_observed=("components_observed", "max"),
        average_delivery_score=("delivery_score", "mean"),
        has_traffic_data=("has_traffic_data", "max"),
        has_parking_data=("has_parking_data", "max"),
        has_truck_data=("has_truck_data", "max")
    )
    .reset_index()
)

street_level_summary["mapped_length_meters"] = (
    street_level_summary["mapped_length_meters"].round(2)
)

street_level_summary["average_delivery_score"] = (
    street_level_summary["average_delivery_score"].round(3)
)

street_level_summary = street_level_summary.sort_values(
    by=["components_observed", "average_delivery_score"],
    ascending=[False, True]
)



ox.save_graphml(street_graph, filepath=str(weighted_graph_file))
street_level_summary.to_csv(street_score_file, index=False)
coverage_summary.to_csv(edge_coverage_file, index=False)



print("Component-Based Delivery-Weighted Network")
print("-----------------------------------------")
print(f"Total road-network edges: {total_edges:,}")

print("\nCoverage by Available Data Component")
print("------------------------------------")
print(component_coverage.to_string(index=False))

print("\nEdges Grouped by Number of Observed Components")
print("----------------------------------------------")
print(coverage_summary.to_string(index=False))

print("\nStreets with the Most Complete Data Coverage")
print("--------------------------------------------")
print(
    street_level_summary.head(15)[
        [
            "street_names",
            "mapped_segments",
            "components_observed",
            "average_delivery_score",
            "has_traffic_data",
            "has_parking_data",
            "has_truck_data"
        ]
    ].to_string(index=False)
)

print("\nFiles created:")
print(f"- {weighted_graph_file}")
print(f"- {street_score_file}")
print(f"- {edge_coverage_file}")