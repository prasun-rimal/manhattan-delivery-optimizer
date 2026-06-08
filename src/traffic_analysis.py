from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

project_folder = Path(__file__).resolve().parent.parent
traffic_file = project_folder / "data" / "input" / "traffic_volume.csv"
output_folder = project_folder / "data" / "output"
figures_folder = project_folder / "figures"

output_folder.mkdir(parents=True, exist_ok=True)
figures_folder.mkdir(parents=True, exist_ok=True)

traffic_data = pd.read_csv(traffic_file)

hourly_traffic = (
    traffic_data.groupby("hour")["Vol"]
    .mean()
    .round(2)
    .reset_index()
)

hourly_traffic = hourly_traffic.rename(
    columns={"Vol": "average_vehicle_volume"}
)

hourly_output_file = output_folder / "hourly_traffic_summary.csv"
hourly_traffic.to_csv(hourly_output_file, index=False)

print("Average Traffic Volume by Hour in Manhattan")
print("--------------------------------------------")
print(hourly_traffic.to_string(index=False))

busiest_hour = hourly_traffic.loc[
    hourly_traffic["average_vehicle_volume"].idxmax()
]

print("\nBusiest hour in the dataset:")
print(
    f"{int(busiest_hour['hour'])}:00, "
    f"with an average vehicle volume of "
    f"{busiest_hour['average_vehicle_volume']}"
)

plt.figure(figsize=(11, 6))
plt.bar(
    hourly_traffic["hour"],
    hourly_traffic["average_vehicle_volume"]
)

plt.title("Average Traffic Volume by Hour in Manhattan")
plt.xlabel("Hour of Day")
plt.ylabel("Average Vehicle Volume")
plt.xticks(range(24))
plt.grid(axis="y", linestyle="--", alpha=0.4)
plt.tight_layout()


chart_file = figures_folder / "average_traffic_volume_by_hour.png"
plt.savefig(chart_file, dpi=300)
plt.close()

print("\nFiles created:")
print(f"- {hourly_output_file}")
print(f"- {chart_file}")