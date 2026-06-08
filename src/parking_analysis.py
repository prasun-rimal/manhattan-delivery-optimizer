from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

project_folder = Path(__file__).resolve().parent.parent
parking_file = project_folder / "data" / "input" / "parking_signs.csv"
output_folder = project_folder / "data" / "output"
figures_folder = project_folder / "figures"

output_folder.mkdir(parents=True, exist_ok=True)
figures_folder.mkdir(parents=True, exist_ok=True)

parking_data = pd.read_csv(parking_file)


def calculate_parking_access_score(sign_description):
    """
    Give each parking sign an initial delivery-access score.
    Higher values mean better curb access for delivery vehicles.
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


parking_data["parking_access_score"] = parking_data[
    "sign_description"
].apply(calculate_parking_access_score)

street_parking_scores = (
    parking_data.groupby("on_street")
    .agg(
        number_of_signs=("sign_description", "count"),
        average_parking_access_score=("parking_access_score", "mean")
    )
    .reset_index()
)

street_parking_scores["average_parking_access_score"] = (
    street_parking_scores["average_parking_access_score"].round(3)
)

street_parking_scores = street_parking_scores.sort_values(
    by=["average_parking_access_score", "number_of_signs"],
    ascending=[False, False]
)

output_file = output_folder / "street_parking_access_scores.csv"
street_parking_scores.to_csv(output_file, index=False)

print("Parking Access Score Analysis")
print("-----------------------------")
print(f"Parking sign records scored: {len(parking_data):,}")
print(f"Streets scored: {len(street_parking_scores):,}")

print("\nScore Distribution Across Sign Records")
print("--------------------------------------")
print(parking_data["parking_access_score"].value_counts().sort_index().to_string())

print("\nTop 10 Streets by Delivery Parking Access")
print("-----------------------------------------")
print(street_parking_scores.head(10).to_string(index=False))

top_streets = street_parking_scores.head(10).sort_values(
    by="average_parking_access_score",
    ascending=True
)

plt.figure(figsize=(10, 6))
plt.barh(
    top_streets["on_street"],
    top_streets["average_parking_access_score"]
)
plt.title("Top 10 Manhattan Streets by Delivery Parking Access Score")
plt.xlabel("Average Parking Access Score (0 to 1)")
plt.ylabel("Street")
plt.xlim(0, 1.05)
plt.grid(axis="x", linestyle="--", alpha=0.4)
plt.tight_layout()

chart_file = figures_folder / "top_streets_by_parking_access.png"
plt.savefig(chart_file, dpi=300)
plt.close()

print("\nFiles created:")
print(f"- {output_file}")
print(f"- {chart_file}")