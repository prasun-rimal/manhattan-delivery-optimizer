"""
Flask web application for the Manhattan Last-Mile Delivery Optimizer.

This app connects the reusable routing engine to a simple web interface.
"""

from pathlib import Path
import os
import sys

from flask import Flask, jsonify, render_template, request

PROJECT_FOLDER = Path(__file__).resolve().parent.parent
ROUTING_ENGINE_FOLDER = PROJECT_FOLDER / "src" / "routing_engine"

if str(ROUTING_ENGINE_FOLDER) not in sys.path:
    sys.path.append(str(ROUTING_ENGINE_FOLDER))

from locations import get_location_names
from router import calculate_routes


app = Flask(__name__)


@app.route("/")
def index():
    """Display the main web page."""
    locations = get_location_names()

    return render_template(
        "index.html",
        locations=locations
    )


@app.route("/api/route", methods=["POST"])
def api_route():
    """
    Calculate route results from the selected origin and destination.

    Expected JSON:
    {
        "origin": "Financial District",
        "destination": "Chinatown"
    }
    """
    data = request.get_json()

    if data is None:
        return jsonify({"error": "Missing JSON request body."}), 400

    origin = data.get("origin")
    destination = data.get("destination")

    if not origin or not destination:
        return jsonify(
            {"error": "Both origin and destination are required."}
        ), 400

    if origin == destination:
        return jsonify(
            {"error": "Origin and destination must be different."}
        ), 400

    try:
        route_result = calculate_routes(origin, destination)

        response = {
            "comparison": route_result["comparison"],
            "baseline_coordinates": route_result["baseline_coordinates"],
            "optimized_coordinates": route_result["optimized_coordinates"]
        }

        return jsonify(response)

    except Exception as error:
        return jsonify({"error": str(error)}), 500


if __name__ == "__main__":
    app.run(
        debug=os.getenv("FLASK_DEBUG") == "1",
        host="127.0.0.1",
        port=5000,
        use_reloader=False
    )
