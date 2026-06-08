from pathlib import Path
import re

import osmnx as ox
import pandas as pd


project_folder = Path(__file__).resolve().parent.parent
input_folder = project_folder / "data" / "input"
output_folder = project_folder / "data" / "output"

graph_file = output_folder / "lower_manhattan_network.graphml"
traffic_file = input_folder / "traffic_volume.csv"
truck_file = input_folder / "truck_routes.csv"
parking_file = input_folder / "parking_signs.csv"


def normalize_street_name(street_name):
    """
    Standardize street names so names such as
    'East 14th Street' and 'EAST 14 STREET'
    can be compared more reliably.
    """
    if pd.isna(street_name):
        return ""

    name = str(street_name).upper().strip()
    name = re.sub(r"\s+", " ", name)

   
    name = re.sub(r"(\d+)(ST|ND|RD|TH)\b", r"\1", name)

    return name


def extract_network_street_names(edges):
    """
    Extract individual street names from the OSMnx edge table.
    Some network edges may contain multiple road names.
    """
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


street_graph = ox.load_graphml(filepath=str(graph_file))
network_edges = ox.graph_to_gdfs(street_graph, nodes=False, edges=True)

traffic_data = pd.read_csv(traffic_file)
truck_data = pd.read_csv(truck_file)
parking_data = pd.read_csv(parking_file)

traffic_streets = {
    normalize_street_name(name)
    for name in traffic_data["street"].dropna()
}

truck_streets = {
    normalize_street_name(name)
    for name in truck_data["Street"].dropna()
}

parking_streets = {
    normalize_street_name(name)
    for name in parking_data["on_street"].dropna()
}

network_streets = extract_network_street_names(network_edges)

all_three_data_streets = (
    traffic_streets
    .intersection(truck_streets)
    .intersection(parking_streets)
)

matched_all_three_streets = all_three_data_streets.intersection(network_streets)

traffic_network_matches = traffic_streets.intersection(network_streets)
truck_network_matches = truck_streets.intersection(network_streets)
parking_network_matches = parking_streets.intersection(network_streets)

print("Lower Manhattan Network Street Matching Check")
print("---------------------------------------------")
print(f"Named streets in road network: {len(network_streets):,}")
print(f"Traffic streets matched to network: {len(traffic_network_matches):,}")
print(f"Truck-route streets matched to network: {len(truck_network_matches):,}")
print(f"Parking streets matched to network: {len(parking_network_matches):,}")

print("\nStreets Present in All Three NYC Datasets")
print("-----------------------------------------")
for street in sorted(all_three_data_streets):
    print(street)

print("\nAll-Three Dataset Streets Found in This Road Network")
print("---------------------------------------------------")
if matched_all_three_streets:
    for street in sorted(matched_all_three_streets):
        print(street)
else:
    print("No exact standardized matches found.")

print("\nObserved Traffic Streets Found in This Road Network")
print("---------------------------------------------------")
for street in sorted(traffic_network_matches):
    print(street)