# Manhattan Last-Mile Delivery Optimizer

A delivery-aware routing prototype for Lower Manhattan that compares traditional shortest-distance routing with optimized routes designed for last-mile delivery constraints.

This project uses real NYC transportation datasets, OpenStreetMap road networks, graph algorithms, and a Flask/Leaflet web application to model how delivery routes can be improved when congestion, curb/loading access, and truck-route restrictions are considered.

---

## Project Overview

Last-mile delivery in Manhattan is not only about finding the shortest route. Delivery drivers also have to deal with traffic congestion, legal truck routes, loading zones, parking restrictions, and limited curb access.

This project builds a routing prototype that compares:

* a shortest-distance baseline route
* a delivery-aware optimized route

The delivery-aware route uses a custom graph edge cost that considers:

* traffic congestion
* parking/loading access
* truck-route restriction risk

The result is a system that demonstrates how real-world urban delivery constraints can be incorporated into graph-based routing.

---

## Project Status

This project is a local research prototype with a runnable Flask/Leaflet demo. The repository includes the processed graph and output files needed to run the demo without downloading the large raw NYC datasets.

The app is not currently deployed online, but it is structured so a reviewer can clone the repository, install dependencies, run the Flask app, and test the route comparison locally.

---

## Demo / Showcase Result

The main showcase route compares travel from the Financial District to Chinatown.

| Metric                    |      Result |
| ------------------------- | ----------: |
| Baseline distance         |  2,577.56 m |
| Optimized distance        |  2,612.57 m |
| Added distance            |     35.01 m |
| Baseline delivery cost    |    3,464.60 |
| Optimized delivery cost   |    3,429.98 |
| Delivery-cost improvement | 34.62 units |
| Dijkstra and A* agreement |        True |

The optimized route added only **35.01 meters** while reducing the modeled delivery cost by **34.62 units**.

![Financial District to Chinatown Showcase Route](figures/financial_district_to_chinatown_showcase_route.png)

---

## Web App Demo Flow

To evaluate the interactive demo:

1. Start the Flask app with `python app/app.py`
2. Open `http://127.0.0.1:5000`
3. Select `Financial District` as the origin
4. Select `Chinatown` as the destination
5. Click `Calculate Route`
6. Compare the blue shortest-distance route with the red delivery-aware route

The results panel shows distance, added distance, modeled delivery-cost improvement, data coverage, and whether Dijkstra and A* agree on the optimized route.

---

## Features

* Builds a routable Lower Manhattan street network using OSMnx and NetworkX
* Compares shortest-distance routing against delivery-aware routing
* Implements Dijkstra's algorithm and A* search
* Uses real NYC traffic, parking/loading sign, and truck-route datasets
* Applies a component-based scoring model for incomplete public data coverage
* Reports route distance, cost improvement, and route-level data coverage
* Visualizes routes through a Flask and Leaflet web application
* Generates charts and CSV outputs for analysis and validation

---

## Key Files

* `app/app.py` - Flask API and web app entry point
* `app/templates/index.html` - Leaflet demo interface
* `app/static/js/map.js` - frontend route request and map rendering logic
* `src/routing_engine/router.py` - shortest-distance and delivery-aware route calculations
* `src/routing_engine/locations.py` - verified Lower Manhattan demo locations
* `src/create_component_weighted_network.py` - builds the delivery-weighted street graph
* `src/evaluate_component_routes.py` - compares baseline and optimized routes
* `data/output/` - processed demo-ready graph and route-analysis outputs

---

## Tech Stack

* **Languages:** Python, JavaScript, HTML, CSS
* **Backend:** Flask
* **Mapping:** Leaflet.js, OpenStreetMap
* **Data / Graph Tools:** pandas, NetworkX, OSMnx
* **Visualization:** Matplotlib
* **Algorithms:** Dijkstra's algorithm, A* search

---

## Data Sources

The project uses four main data sources:

1. NYC traffic volume data
2. NYC parking/loading regulation sign data
3. NYC official truck-route data
4. OpenStreetMap road network data through OSMnx

The system combines these datasets with a Lower Manhattan driving graph to assign delivery-aware costs to road segments.

### Data Availability Note

This repository includes the processed output files needed to run the demo application locally, including the prepared Lower Manhattan graph and route-analysis outputs.

The raw input CSV datasets are not included in the repository because they are large public datasets and are better downloaded directly from their original sources if someone wants to fully rebuild the data pipeline.

---

## Methodology

The road network is represented as a directed graph:

* intersections are nodes
* road segments are edges
* each edge has a physical distance
* each edge receives a delivery difficulty score when data is available

The baseline route minimizes physical distance.

The delivery-aware route uses a custom cost function:

```text
Delivery Cost = Edge Length × (1 + Delivery Difficulty Score)
```

The delivery difficulty score combines:

```text
0.40 × congestion penalty
0.30 × parking/loading penalty
0.30 × truck-route restriction penalty
```

Because public datasets do not cover every street evenly, the project uses a component-based scoring method. If a street segment has traffic, parking, or truck-route data, that information is used. If a component is missing, the model applies a neutral fallback value and reports data coverage for transparency.

---

## What Happens When the App Runs

When the Flask app is started locally, the system:

1. Loads the prepared Lower Manhattan delivery-weighted graph
2. Allows the user to select an origin and destination
3. Computes the shortest-distance baseline route
4. Computes the delivery-aware optimized route
5. Verifies the delivery-aware result using A* search
6. Returns route coordinates and metrics to the browser
7. Displays both routes on a Leaflet map

The baseline route is shown in blue, and the delivery-aware route is shown in red.

---

## Visualizations

### Showcase Route

![Financial District to Chinatown Showcase Route](figures/financial_district_to_chinatown_showcase_route.png)

### Average Traffic Volume by Hour

![Average Traffic Volume by Hour](figures/average_traffic_volume_by_hour.png)

### Truck Route Type Distribution

![Truck Route Type Distribution](figures/truck_route_type_distribution.png)

### Lower Manhattan Network

![Lower Manhattan Network](figures/lower_manhattan_network.png)

---

## Project Structure

```text
manhattan-delivery-optimizer/
│
├── app/
│   ├── app.py
│   ├── static/
│   │   ├── css/
│   │   └── js/
│   └── templates/
│
├── src/
│   ├── routing_engine/
│   ├── traffic_analysis.py
│   ├── parking_analysis.py
│   ├── truck_analysis.py
│   ├── create_lower_manhattan_network.py
│   ├── create_component_weighted_network.py
│   └── evaluate_component_routes.py
│
├── data/
│   └── output/
│
├── figures/
│
├── README.md
├── requirements.txt
└── .gitignore
```

---

## How to Run Locally

Clone the repository:

```bash
git clone https://github.com/prasun-rimal/manhattan-delivery-optimizer.git
cd manhattan-delivery-optimizer
```

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the Flask app:

```bash
python app/app.py
```

Then open the local URL shown in the terminal. It will usually look like:

```text
http://127.0.0.1:5000
```

---

## Important Run Note

The demo app is designed to run using the processed graph and output files already included in `data/output/`.

To fully rebuild the project from raw datasets, the original NYC traffic, parking/loading sign, and truck-route datasets would need to be downloaded separately and placed into the expected local input folder.

---

## Limitations

This project is a research prototype, not a production routing platform.

Current limitations include:

* the prototype focuses on Lower Manhattan rather than all of Manhattan
* traffic data coverage is limited by the available public dataset
* parking/loading access is scored through rule-based text matching
* parking rules are not yet time-dependent
* vehicle-specific restrictions such as height, weight, axle count, and hazardous materials are not yet modeled
* the delivery-cost score is a relative decision-support metric, not a direct measurement of travel time or financial cost

---

## Future Work

Future improvements could include:

* expanding the graph to full Manhattan
* adding live or broader traffic data
* parsing time-dependent parking/loading rules
* allowing users to adjust congestion, parking, and truck-route weights
* adding address-based input with geocoding
* improving route explanations in the web interface
* deploying the web app online

---

## Author

**Prasun Rimal**
B.S. Mathematics and B.S. Computer Science
St. Joseph's University, New York
