from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

project_folder = Path(__file__).resolve().parent.parent
truck_file = project_folder / "data" / "input" / "truck_routes.csv"
output_folder = project_folder / "data" / "output"
figures_folder = project_folder / "figures"

output_folder.mkdir(parents=True, exist_ok=True)
figures_folder.mkdir(parents=True, exist_ok=True)

truck_data = pd.read_csv(truck_file)

truck_data["has_restriction"] = truck_data["Restrictio"].notna()

route_type_summary = (
    truck_data["RouteType"]
    .value_counts()
    .rename_axis("route_type")
    .reset_index(name="number_of_segments")
)

restriction_summary = (
    truck_data.groupby(["RouteType", "has_restriction"])
    .size()
    .reset_index(name="number_of_segments")
)

restriction_summary["restriction_status"] = restriction_summary[
    "has_restriction"
].map({
    True: "Listed restriction",
    False: "No listed restriction"
})

restriction_summary = restriction_summary[
    ["RouteType", "restriction_status", "number_of_segments"]
]

total_segments = len(truck_data)
restricted_segments = truck_data["has_restriction"].sum()
unrestricted_segments = total_segments - restricted_segments
restricted_percentage = round((restricted_segments / total_segments) * 100, 2)

route_output_file = output_folder / "truck_route_type_summary.csv"
restriction_output_file = output_folder / "truck_route_restriction_summary.csv"

route_type_summary.to_csv(route_output_file, index=False)
restriction_summary.to_csv(restriction_output_file, index=False)

print("Truck Route Analysis")
print("--------------------")
print(f"Official truck-route segments: {total_segments:,}")
print(f"Segments with listed restrictions: {restricted_segments:,}")
print(f"Segments without listed restrictions: {unrestricted_segments:,}")
print(f"Percent with listed restrictions: {restricted_percentage}%")

print("\nRoute Type Summary")
print("------------------")
print(route_type_summary.to_string(index=False))

print("\nRestrictions by Route Type")
print("--------------------------")
print(restriction_summary.to_string(index=False))

plt.figure(figsize=(8, 5))
plt.bar(
    route_type_summary["route_type"],
    route_type_summary["number_of_segments"]
)

plt.title("Official Truck-Route Segments in Manhattan")
plt.xlabel("Route Type")
plt.ylabel("Number of Segments")
plt.grid(axis="y", linestyle="--", alpha=0.4)
plt.tight_layout()

chart_file = figures_folder / "truck_route_type_distribution.png"
plt.savefig(chart_file, dpi=300)
plt.close()

print("\nFiles created:")
print(f"- {route_output_file}")
print(f"- {restriction_output_file}")
print(f"- {chart_file}")