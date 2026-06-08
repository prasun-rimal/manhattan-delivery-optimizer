from pathlib import Path
import pandas as pd

project_folder = Path(__file__).resolve().parent.parent
truck_file = project_folder / "data" / "input" / "truck_routes.csv"

truck_data = pd.read_csv(truck_file)

print("Truck Route Data Inspection")
print("---------------------------")
print(f"Total truck-route records: {len(truck_data):,}")
print(f"Unique streets: {truck_data['Street'].nunique():,}")

print("\nColumn Names")
print("------------")
print(list(truck_data.columns))

print("\nRoute Type Counts")
print("-----------------")
print(truck_data["RouteType"].value_counts(dropna=False).to_string())

print("\nTruckRoute Column Values")
print("------------------------")
print(truck_data["TruckRoute"].value_counts(dropna=False).head(20).to_string())

print("\nRestriction Column Values")
print("-------------------------")
print(truck_data["Restrictio"].value_counts(dropna=False).head(20).to_string())

print("\nSample Truck Route Records")
print("--------------------------")
print(truck_data.head(15).to_string(index=False))