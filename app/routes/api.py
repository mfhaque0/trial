from flask import Blueprint, current_app, jsonify, request

from app.models.database import connect
from app.routes.common import current_user
from app.services.calculations import (
    CalculationError,
    calculate_assessment,
)

api = Blueprint("api", __name__)


def auth_error():
    return jsonify(error="Authentication required."), 401


@api.post("/auth/current")
def current():
    user = current_user()
    return jsonify(user=dict(user) if user else None)


@api.post("/assessments/calculate")
def calculate():
    """
    Public nutrition calculation endpoint.

    Login is NOT required because this endpoint only
    performs a calculation and does not save private data.
    """
    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return jsonify(error="Send a JSON object."), 400

    try:
        return jsonify(calculate_assessment(payload))

    except CalculationError as error:
        return jsonify(error=str(error)), 400


@api.get("/patients")
def patient_list():
    """
    Private patient endpoint.
    Login IS required because patient data is private.
    """
    user = current_user()

    if not user:
        return auth_error()

    db = connect(current_app.config["DATABASE"])

    rows = db.execute(
        """
        SELECT id, full_name, updated_at
        FROM patients
        WHERE user_id = ?
          AND archived_at IS NULL
        """,
        (user["id"],),
    ).fetchall()

    return jsonify(
        patients=[dict(row) for row in rows]
    )

@api.get("/foods")
def food_list():
    """
    Search the shared IFCT food library.

    Returns basic nutrition and IFCT source information.
    Login is required because this endpoint is used inside
    the authenticated workspace.
    """

    user = current_user()

    if not user:
        return auth_error()

    query = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    limit = min(max(int(request.args.get("limit", 50)), 1), 100)

    db = connect(current_app.config["DATABASE"])

    conditions = ["foods.user_id IS NULL"]
    params = []

    if query:
        conditions.append(
            "(foods.name LIKE ? OR food_sources.source_food_code LIKE ?)"
        )
        search = f"%{query}%"
        params.extend([search, search])

    if category:
        conditions.append("foods.category = ?")
        params.append(category)

    params.append(limit)

    rows = db.execute(
        f"""
        SELECT
            foods.id,
            foods.name,
            foods.category,
            foods.serving_size,
            foods.unit,
            foods.calories,
            foods.protein,
            foods.carbohydrates,
            foods.fat,
            foods.fiber,

            food_sources.source_food_code,
            food_sources.source_food_name,
            food_sources.ifct_group_code,
            food_sources.ifct_group_name,
            food_sources.regions_count,
            food_sources.source_name,
            food_sources.source_version

        FROM foods

        LEFT JOIN food_sources
            ON food_sources.food_id = foods.id

        WHERE {" AND ".join(conditions)}

        ORDER BY foods.category, foods.name

        LIMIT ?
        """,
        params,
    ).fetchall()

    return jsonify(
        foods=[dict(row) for row in rows],
        count=len(rows),
        query=query,
        category=category,
    )

@api.get("/foods/<int:food_id>")
def food_detail(food_id):
    """
    Return complete IFCT information for one food.

    Includes basic nutrition, IFCT source metadata,
    and all available component measurements.
    """

    user = current_user()

    if not user:
        return auth_error()

    db = connect(current_app.config["DATABASE"])

    food = db.execute(
        """
        SELECT
            foods.id,
            foods.name,
            foods.category,
            foods.serving_size,
            foods.unit,
            foods.calories,
            foods.protein,
            foods.carbohydrates,
            foods.fat,
            foods.fiber,

            food_sources.source_food_code,
            food_sources.source_food_name,
            food_sources.ifct_group_code,
            food_sources.ifct_group_name,
            food_sources.regions_count,
            food_sources.source_name,
            food_sources.source_version,
            food_sources.source_reference

        FROM foods

        LEFT JOIN food_sources
            ON food_sources.food_id = foods.id

        WHERE foods.id = ?
          AND foods.user_id IS NULL
        """,
        (food_id,),
    ).fetchone()

    if not food:
        return jsonify(error="Food not found."), 404

    components = db.execute(
        """
        SELECT
            component_definitions.code,
            component_definitions.name,
            component_definitions.category,
            component_definitions.unit,
            component_definitions.basis,
            component_definitions.description,

            food_components.value,
            food_components.standard_deviation,
            food_components.measurement_status,
            food_components.source_reference

        FROM food_components

        JOIN component_definitions
            ON component_definitions.id = food_components.component_id

        WHERE food_components.food_id = ?

        ORDER BY
            component_definitions.category,
            component_definitions.name
        """,
        (food_id,),
    ).fetchall()

    return jsonify(
        food=dict(food),
        components=[dict(row) for row in components],
    )