from pathlib import Path
import pandas as pd
import re

project_folder = Path(__file__).resolve().parent.parent
input_folder = project_folder / "data" / "input"
output_folder = project_folder / "data" / "output"

traffic_file = input_folder / "traffic_volume.csv"
truck_file = input_folder / "truck_routes.csv"
parking_file = input_folder / "parking_signs.csv"

output_folder.mkdir(parents=True, exist_ok=True)

traffic_data = pd.read_csv(traffic_file)
truck_data = pd.read_csv(truck_file)
parking_data = pd.read_csv(parking_file)


def normalize_street_name(street_name):
    """
    Standardize street names for an initial comparison.
    This version handles capitalization and repeated spaces.
    """
    if pd.isna(street_name):
        return ""

    standardized_name = str(street_name).upper().strip()
    standardized_name = re.sub(r"\s+", " ", standardized_name)

    return standardized_name


traffic_data["street_standardized"] = traffic_data["street"].apply(
    normalize_street_name
)

truck_data["street_standardized"] = truck_data["Street"].apply(
    normalize_street_name
)

parking_data["street_standardized"] = parking_data["on_street"].apply(
    normalize_street_name
)

traffic_streets = set(traffic_data["street_standardized"]) - {""}
truck_streets = set(truck_data["street_standardized"]) - {""}
parking_streets = set(parking_data["street_standardized"]) - {""}

traffic_and_truck = traffic_streets.intersection(truck_streets)
traffic_and_parking = traffic_streets.intersection(parking_streets)
truck_and_parking = truck_streets.intersection(parking_streets)
all_three = traffic_streets.intersection(truck_streets, parking_streets)

coverage_summary = pd.DataFrame(
    {
        "metric": [
            "Unique traffic streets",
            "Unique truck-route streets",
            "Unique parking streets",
            "Traffic and truck-route overlap",
            "Traffic and parking overlap",
            "Truck-route and parking overlap",
            "Streets found in all three datasets",
        ],
        "count": [
            len(traffic_streets),
            len(truck_streets),
            len(parking_streets),
            len(traffic_and_truck),
            len(traffic_and_parking),
            len(truck_and_parking),
            len(all_three),
        ],
    }
)

all_three_streets = pd.DataFrame(
    {"street_found_in_all_three_datasets": sorted(all_three)}
)

summary_file = output_folder / "dataset_street_coverage_summary.csv"
overlap_file = output_folder / "streets_found_in_all_three_datasets.csv"

coverage_summary.to_csv(summary_file, index=False)
all_three_streets.to_csv(overlap_file, index=False)

print("Street Name and Data Coverage Audit")
print("-----------------------------------")
print(coverage_summary.to_string(index=False))

print("\nStreets Found in All Three Datasets")
print("-----------------------------------")
print(all_three_streets.to_string(index=False))

print("\nImportant Finding")
print("-----------------")
print(
    "The traffic dataset contains observations for only "
    f"{len(traffic_streets)} unique streets. "
    "A complete Manhattan routing application will require "
    "a separate full street-network source."
)

print("\nFiles created:")
print(f"- {summary_file}")
print(f"- {overlap_file}")