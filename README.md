# Manhattan Last-Mile Delivery Optimizer

A Python and Flask-based routing prototype that compares shortest-distance routes with delivery-aware optimized routes in Lower Manhattan.

The project uses real NYC transportation datasets and an OpenStreetMap-derived road network to model last-mile delivery constraints such as congestion, curb/loading access, and truck-route restriction risk.

## Features

- Builds a routable Lower Manhattan street graph using OSMnx and NetworkX
- Compares shortest-distance routing with delivery-aware routing
- Uses Dijkstra's algorithm and A* search
- Incorporates traffic volume, parking/loading sign, and truck-route data
- Reports route distance, added distance, modeled delivery cost improvement, and data coverage
- Provides a Flask and Leaflet web interface for route visualization

## Tech Stack

- Python
- Flask
- pandas
- NetworkX
- OSMnx
- Matplotlib
- Leaflet.js
- HTML/CSS/JavaScript

## Methodology

The road network is represented as a graph where intersections are nodes and road segments are edges. The baseline route minimizes physical distance. The delivery-aware route uses a custom edge cost that combines congestion, parking/loading access, and truck-route restriction risk.

Because public street-level datasets have incomplete coverage, the model uses a component-based scoring approach. Available data is used where present, and neutral fallback values are applied where data is missing. The app also reports route-level data coverage to keep the recommendation transparent.

## Key Result

In the main showcase route from the Financial District to Chinatown, the delivery-aware route added only 35.01 meters while reducing modeled delivery cost by 34.62 units.

## Limitations

This is a research prototype, not a production routing platform. The current implementation focuses on Lower Manhattan, and traffic coverage is limited by the available public dataset. Future work includes full Manhattan expansion, live traffic data, time-dependent parking rules, address-based input, and adjustable weighting controls.

## How to Run

Clone the repository:

```bash
git clone https://github.com/prasun-rimal/manhattan-delivery-optimizer.git
cd manhattan-delivery-optimizer
pip install -r requirements.txt
python app/app.py
