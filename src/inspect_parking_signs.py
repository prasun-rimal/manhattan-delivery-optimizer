from pathlib import Path
import pandas as pd

project_folder = Path(__file__).resolve().parent.parent
parking_file = project_folder / "data" / "input" / "parking_signs.csv"

parking_data = pd.read_csv(parking_file)

print("Parking Sign Data Inspection")
print("----------------------------")
print(f"Total sign records: {len(parking_data):,}")
print(f"Unique streets: {parking_data['on_street'].nunique():,}")
print(f"Unique sign descriptions: {parking_data['sign_description'].nunique():,}")

common_signs = (
    parking_data["sign_description"]
    .fillna("MISSING DESCRIPTION")
    .value_counts()
    .head(25)
)

print("\n25 Most Common Sign Descriptions")
print("--------------------------------")
print(common_signs.to_string())

delivery_keywords = "COMMERCIAL|TRUCK|LOADING|NO STANDING|NO PARKING"

delivery_related_signs = parking_data[
    parking_data["sign_description"]
    .fillna("")
    .str.upper()
    .str.contains(delivery_keywords, regex=True)
]

print("\nDelivery-Related Sign Records")
print("-----------------------------")
print(f"Matching records: {len(delivery_related_signs):,}")

print("\nSample Delivery-Related Sign Descriptions")
print("-----------------------------------------")
print(
    delivery_related_signs["sign_description"]
    .dropna()
    .drop_duplicates()
    .head(30)
    .to_string(index=False)
)