from flask import Blueprint, jsonify, request

from app.services.calculations import (
    CalculationError,
    calculate_assessment,
)

calculators = Blueprint("calculators", __name__)


@calculators.post("/assessment")
def assessment():
    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return jsonify(
            error="Send a JSON object with the assessment details."
        ), 400

    try:
        return jsonify(calculate_assessment(payload))

    except CalculationError as error:
        return jsonify(error=str(error)), 400