from pathlib import Path
import pandas as pd


project_folder = Path(__file__).resolve().parent.parent


input_folder = project_folder / "data" / "input"


traffic_file = input_folder / "traffic_volume.csv"
truck_file = input_folder / "truck_routes.csv"
parking_file = input_folder / "parking_signs.csv"


traffic_data = pd.read_csv(traffic_file)
truck_data = pd.read_csv(truck_file)
parking_data = pd.read_csv(parking_file)


print("Manhattan Last-Mile Delivery Optimizer")
print("--------------------------------------")
print("Traffic data rows:", len(traffic_data))
print("Truck route data rows:", len(truck_data))
print("Parking sign data rows:", len(parking_data))

print("\nTraffic data columns:")
print(list(traffic_data.columns))

print("\nTruck route data columns:")
print(list(truck_data.columns))

print("\nParking sign data columns:")
print(list(parking_data.columns))

print("\nSuccess: all three datasets loaded correctly.")