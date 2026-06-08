"""
Preset delivery locations for the Manhattan Last-Mile Delivery Optimizer.

Version 1 of the application uses verified sample locations inside the
Lower Manhattan road network. A future version can add typed addresses
and geocoding.
"""

DELIVERY_LOCATIONS = {
    "Battery Park": {
        "latitude": 40.7033,
        "longitude": -74.0170
    },
    "Financial District": {
        "latitude": 40.7075,
        "longitude": -74.0113
    },
    "South Street Seaport": {
        "latitude": 40.7068,
        "longitude": -74.0035
    },
    "Civic Center": {
        "latitude": 40.7135,
        "longitude": -74.0055
    },
    "Chinatown": {
        "latitude": 40.7157,
        "longitude": -73.9970
    },
    "Lower East Side": {
        "latitude": 40.7163,
        "longitude": -73.9895
    },
    "East Village South": {
        "latitude": 40.7220,
        "longitude": -73.9865
    }
}


def get_location_names():
    """Return the available location names for a dropdown menu."""
    return list(DELIVERY_LOCATIONS.keys())


def get_coordinates(location_name):
    """
    Return coordinates for a selected location.

    Raises an error if the supplied location is not available.
    """
    if location_name not in DELIVERY_LOCATIONS:
        raise ValueError(f"Unknown delivery location: {location_name}")

    location = DELIVERY_LOCATIONS[location_name]

    return location["latitude"], location["longitude"]


if __name__ == "__main__":
    print("Available Delivery Locations")
    print("----------------------------")

    for name in get_location_names():
        latitude, longitude = get_coordinates(name)
        print(f"{name}: ({latitude}, {longitude})")