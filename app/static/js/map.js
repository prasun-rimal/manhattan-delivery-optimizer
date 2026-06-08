
const map = L.map("map").setView([40.7115, -74.0045], 14);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors"
}).addTo(map);

let baselineRouteLayer = null;
let optimizedRouteLayer = null;
let startMarker = null;
let destinationMarker = null;

function formatNumber(value, decimals = 2) {
    return Number(value).toFixed(decimals);
}

function clearMapLayers() {
    if (baselineRouteLayer) {
        map.removeLayer(baselineRouteLayer);
    }

    if (optimizedRouteLayer) {
        map.removeLayer(optimizedRouteLayer);
    }

    if (startMarker) {
        map.removeLayer(startMarker);
    }

    if (destinationMarker) {
        map.removeLayer(destinationMarker);
    }
}

function updateResults(comparison) {
    document.getElementById("baseline-distance").textContent =
        `${formatNumber(comparison.baseline_distance_miles)} mi`;

    document.getElementById("optimized-distance").textContent =
        `${formatNumber(comparison.optimized_distance_miles)} mi`;

    document.getElementById("added-distance").textContent =
        `${formatNumber(comparison.added_distance_meters)} m`;

    document.getElementById("cost-improvement").textContent =
        `${formatNumber(comparison.delivery_cost_improvement)} units`;

    document.getElementById("traffic-coverage").textContent =
        `${formatNumber(comparison.optimized_traffic_coverage_percent)}%`;

    document.getElementById("parking-coverage").textContent =
        `${formatNumber(comparison.optimized_parking_coverage_percent)}%`;

    document.getElementById("truck-coverage").textContent =
        `${formatNumber(comparison.optimized_truck_coverage_percent)}%`;

    document.getElementById("two-component-coverage").textContent =
        `${formatNumber(comparison.optimized_two_component_coverage_percent)}%`;

    const algorithmText = comparison.dijkstra_and_astar_agree
        ? "Algorithm check: Dijkstra and A* agree on the delivery-aware route."
        : "Algorithm check: Dijkstra and A* returned different routes.";

    document.getElementById("algorithm-check").textContent = algorithmText;
}

function drawRoutes(data) {
    clearMapLayers();

    const baselineCoordinates = data.baseline_coordinates;
    const optimizedCoordinates = data.optimized_coordinates;

    baselineRouteLayer = L.polyline(baselineCoordinates, {
        color: "#2f86c1",
        weight: 6,
        opacity: 0.9
    }).addTo(map);

    optimizedRouteLayer = L.polyline(optimizedCoordinates, {
        color: "#e63946",
        weight: 6,
        opacity: 0.9
    }).addTo(map);

    const startCoordinate = optimizedCoordinates[0];
    const destinationCoordinate =
        optimizedCoordinates[optimizedCoordinates.length - 1];

    startMarker = L.marker(startCoordinate)
        .addTo(map)
        .bindPopup("Start");

    destinationMarker = L.marker(destinationCoordinate)
        .addTo(map)
        .bindPopup("Destination");

    const routeBounds = L.latLngBounds([
        ...baselineCoordinates,
        ...optimizedCoordinates
    ]);

    map.fitBounds(routeBounds, {
        padding: [40, 40]
    });
}

async function calculateRoute() {
    const origin = document.getElementById("origin").value;
    const destination = document.getElementById("destination").value;
    const errorBox = document.getElementById("error-message");

    errorBox.textContent = "";

    if (origin === destination) {
        errorBox.textContent = "Please choose two different locations.";
        return;
    }

    try {
        const response = await fetch("/api/route", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                origin: origin,
                destination: destination
            })
        });

        const data = await response.json();

        if (!response.ok) {
            errorBox.textContent = data.error || "Something went wrong.";
            return;
        }

        updateResults(data.comparison);
        drawRoutes(data);

    } catch (error) {
        errorBox.textContent =
            "Could not calculate route. Check that the Flask server is running.";
        console.error(error);
    }
}

document
    .getElementById("calculate-route-button")
    .addEventListener("click", calculateRoute);

window.addEventListener("load", calculateRoute);