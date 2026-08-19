import json
from datetime import datetime, timezone

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from app.models.database import connect
from app.routes.common import (
    current_user,
    csrf_token,
    login_required,
    valid_csrf,
)
from app.services.calculations import (
    CalculationError,
    calculate_assessment,
)


workspace = Blueprint("workspace", __name__)


MEALS = [
    "Breakfast",
    "Mid-morning snack",
    "Lunch",
    "Evening snack",
    "Dinner",
    "Bedtime snack",
]


def now():
    return datetime.now(timezone.utc).isoformat()


def owned_patient(db, user_id, patient_id):
    return db.execute(
        "SELECT * FROM patients WHERE id=? AND user_id=?",
        (patient_id, user_id),
    ).fetchone()


@workspace.get("/calculators")
def calculators_page():
    return render_template("calculator.html")

@workspace.get("/calculators/assessment-result")
def assessment_result_page():
    return render_template("assessment_result.html")

@workspace.get("/foods/<int:food_id>")
@login_required
def food_detail_page(food_id):
    db = connect(current_app.config["DATABASE"])

    # ---------------------------------------------------------
    # FOOD
    # ---------------------------------------------------------

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
        return ("Food not found", 404)

    # ---------------------------------------------------------
    # LOCAL / COMMON NAMES
    # ---------------------------------------------------------

    aliases = db.execute(
        """
        SELECT
            id,
            alias,
            alias_type
        FROM food_aliases
        WHERE food_id = ?
        ORDER BY id
        """,
        (food_id,),
    ).fetchall()

    # ---------------------------------------------------------
    # ALL IFCT COMPONENTS
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # GROUP COMPONENTS BY CATEGORY
    # ---------------------------------------------------------

    component_groups = {}

    for component in components:
        category = component["category"] or "other"

        component_groups.setdefault(
            category,
            []
        ).append(dict(component))

    # ---------------------------------------------------------
    # DETERMINE WHETHER THIS IS AN IFCT FOOD
    # ---------------------------------------------------------

    is_ifct = bool(
        food["source_food_code"]
        or food["source_food_name"]
        or food["ifct_group_code"]
    )

    # ---------------------------------------------------------
    # RENDER
    # ---------------------------------------------------------

    return render_template(
        "food_detail.html",
        food=dict(food),
        aliases=[dict(row) for row in aliases],
        components=[dict(row) for row in components],
        component_groups=component_groups,
        is_ifct=is_ifct,
    )


@workspace.get("/dashboard")
@login_required
def dashboard():
    user = current_user()
    db = connect(current_app.config["DATABASE"])

    with db:
        counts = {
            "patients": db.execute(
                "SELECT count(*) FROM patients "
                "WHERE user_id=? AND archived_at IS NULL",
                (user["id"],),
            ).fetchone()[0],
            "plans": db.execute(
                "SELECT count(*) FROM diet_plans WHERE user_id=?",
                (user["id"],),
            ).fetchone()[0],
            "assessments": db.execute(
                "SELECT count(*) FROM assessments WHERE user_id=?",
                (user["id"],),
            ).fetchone()[0],
            "reports": db.execute(
                "SELECT count(*) FROM reports WHERE user_id=?",
                (user["id"],),
            ).fetchone()[0],
        }

        recent = db.execute(
            "SELECT full_name,created_at FROM patients "
            "WHERE user_id=? ORDER BY created_at DESC LIMIT 4",
            (user["id"],),
        ).fetchall()

    return render_template(
        "dashboard.html",
        user=user,
        counts=counts,
        recent=recent,
        csrf_token=csrf_token(),
    )


@workspace.route("/patients", methods=["GET", "POST"])
@login_required
def patients():
    user = current_user()
    query = request.args.get("q", "").strip()
    db = connect(current_app.config["DATABASE"])

    if request.method == "POST":
        if not valid_csrf(request.form.get("csrf_token")):
            flash("Your form expired.", "error")

        elif not request.form.get("full_name", "").strip():
            flash("Patient name is required.", "error")

        else:
            t = now()

            db.execute(
                "INSERT INTO patients("
                "user_id,full_name,date_of_birth,sex,contact,height,height_unit,"
                "weight,weight_unit,activity_level,goal,allergies,"
                "dietary_preferences,medical_notes,created_at,updated_at"
                ") VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    user["id"],
                    request.form["full_name"].strip(),
                    request.form.get("date_of_birth"),
                    request.form.get("sex"),
                    request.form.get("contact"),
                    request.form.get("height") or None,
                    request.form.get("height_unit"),
                    request.form.get("weight") or None,
                    request.form.get("weight_unit"),
                    request.form.get("activity_level"),
                    request.form.get("goal"),
                    request.form.get("allergies", ""),
                    request.form.get("dietary_preferences", ""),
                    request.form.get("medical_notes", ""),
                    t,
                    t,
                ),
            )

            db.commit()
            flash("Patient added.", "success")
            return redirect(url_for("workspace.patients"))

    rows = db.execute(
        "SELECT * FROM patients "
        "WHERE user_id=? AND archived_at IS NULL "
        "AND full_name LIKE ? "
        "ORDER BY updated_at DESC",
        (user["id"], f"%{query}%"),
    ).fetchall()

    return render_template(
        "patients.html",
        patients=rows,
        query=query,
        csrf_token=csrf_token(),
    )


@workspace.route("/patients/<int:patient_id>", methods=["GET", "POST"])
@login_required
def patient_detail(patient_id):
    user = current_user()
    db = connect(current_app.config["DATABASE"])

    patient = owned_patient(db, user["id"], patient_id)

    if not patient:
        return ("Not found", 404)

    if request.method == "POST":
        if (
            valid_csrf(request.form.get("csrf_token"))
            and request.form.get("action") == "archive"
        ):
            db.execute(
                "UPDATE patients SET archived_at=?,updated_at=? "
                "WHERE id=? AND user_id=?",
                (now(), now(), patient_id, user["id"]),
            )

            db.commit()

            flash("Patient archived.", "success")
            return redirect(url_for("workspace.patients"))

    assessments = db.execute(
        "SELECT * FROM assessments "
        "WHERE patient_id=? AND user_id=? "
        "ORDER BY created_at DESC",
        (patient_id, user["id"]),
    ).fetchall()

    plans = db.execute(
        "SELECT * FROM diet_plans "
        "WHERE patient_id=? AND user_id=? "
        "ORDER BY updated_at DESC",
        (patient_id, user["id"]),
    ).fetchall()

    return render_template(
        "patient_detail.html",
        patient=patient,
        assessments=assessments,
        plans=plans,
        csrf_token=csrf_token(),
    )


@workspace.route(
    "/patients/<int:patient_id>/assessment",
    methods=["GET", "POST"],
)
@login_required
def assessment(patient_id):
    user = current_user()
    db = connect(current_app.config["DATABASE"])

    patient = owned_patient(db, user["id"], patient_id)

    if not patient:
        return ("Not found", 404)

    if request.method == "POST":
        if not valid_csrf(request.form.get("csrf_token")):
            flash("Your form expired.", "error")

        else:
            try:
                data = dict(request.form)

                data["custom_macros"] = bool(
                    request.form.get("custom_macros")
                )

                data["macros"] = {
                    k: request.form.get(k)
                    for k in ("protein", "carbs", "fat")
                }

                result = calculate_assessment(data)
                t = now()

                db.execute(
                    "INSERT INTO assessments("
                    "user_id,patient_id,height_m,weight_kg,bmi,bmi_category,"
                    "bmr,tdee,target,macros_json,water_litres,"
                    "activity_level,goal,notes,created_at"
                    ") VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        user["id"],
                        patient_id,
                        result["normalised"]["height_m"],
                        result["normalised"]["weight_kg"],
                        result["bmi"]["value"],
                        result["bmi"]["category"],
                        result["bmr"],
                        result["tdee"],
                        result["target"],
                        json.dumps(result["macros"]),
                        result["water_litres"],
                        data["activity"],
                        data["goal"],
                        request.form.get("notes", ""),
                        t,
                    ),
                )

                db.commit()
                flash("Assessment saved to history.", "success")

                return redirect(
                    url_for(
                        "workspace.patient_detail",
                        patient_id=patient_id,
                    )
                )

            except CalculationError as error:
                flash(str(error), "error")

    return render_template(
        "assessment.html",
        patient=patient,
        csrf_token=csrf_token(),
    )


# -------------------------------------------------------------------
# FOOD LIBRARY
# -------------------------------------------------------------------

@workspace.get("/foods")
@login_required
def foods():
    user = current_user()
    db = connect(current_app.config["DATABASE"])

    rows = db.execute(
        "SELECT * FROM foods "
        "WHERE user_id IS NULL OR user_id=? "
        "ORDER BY category,name",
        (user["id"],),
    ).fetchall()

    exchange_groups = db.execute(
        """
        SELECT *
        FROM exchange_groups
        WHERE user_id IS NULL OR user_id=?
        ORDER BY category, name
        """,
        (user["id"],),
    ).fetchall()
    
    recipes = db.execute(
        """
        SELECT *
        FROM recipes
        WHERE user_id=?
        ORDER BY category, name
        """,
        (user["id"],),
    ).fetchall()
    return render_template(
        "foods.html",
        foods=rows,
        exchange_groups=exchange_groups,
        recipes=recipes,
        csrf_token=csrf_token(),
    )


@workspace.route("/foods/new", methods=["GET", "POST"])
@login_required
def food_new():
    user = current_user()
    db = connect(current_app.config["DATABASE"])

    if request.method == "POST":
        if not valid_csrf(request.form.get("csrf_token")):
            flash("Your form expired.", "error")

        else:
            try:
                name = request.form.get("name", "").strip()

                if not name:
                    raise ValueError("name")

                values = (
                    user["id"],
                    name,
                    request.form.get("food_type", "Vegetarian"),
                    request.form.get("category", ""),
                    request.form.get("meal_type", ""),
                    request.form.get(
                        "serving_size",
                        "1 serving",
                    ),
                    request.form.get(
                        "unit",
                        "serving",
                    ),
                    _number(
                        request.form.get("calories"),
                        "calories",
                    ),
                    _number(
                        request.form.get("protein"),
                        "protein",
                    ),
                    _number(
                        request.form.get("carbohydrates"),
                        "carbohydrates",
                    ),
                    _number(
                        request.form.get("fat"),
                        "fat",
                    ),
                    _number(
                        request.form.get("fiber"),
                        "fiber",
                    ),
                    now(),
                )

                db.execute(
                    "INSERT INTO foods("
                    "user_id,name,food_type,category,meal_type,"
                    "serving_size,unit,"
                    "calories,protein,carbohydrates,fat,fiber,created_at"
                    ") VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    values,
                )

                db.commit()

                flash(
                    "Food saved as your own reference item.",
                    "success",
                )

                return redirect(url_for("workspace.foods"))

            except (ValueError, KeyError):
                flash(
                    "Enter a name and valid nutrition values.",
                    "error",
                )

    return render_template(
        "food_new.html",
        csrf_token=csrf_token(),
    )


def _number(value, label):
    value = float(value or 0)

    if value < 0:
        return (_ for _ in ()).throw(ValueError(label))

    return value


@workspace.route("/plans", methods=["GET", "POST"])
@login_required
def plans():
    user = current_user()
    db = connect(current_app.config["DATABASE"])

    if request.method == "POST" and valid_csrf(
        request.form.get("csrf_token")
    ):
        patient_id = int(request.form.get("patient_id", 0))
        patient = owned_patient(db, user["id"], patient_id)

        if not patient:
            flash("Choose one of your patients.", "error")

        else:
            t = now()

            title = (
                request.form.get("title", "").strip()
                or f"Nutrition plan for {patient['full_name']}"
            )

            cursor = db.execute(
                "INSERT INTO diet_plans("
                "user_id,patient_id,title,notes,created_at,updated_at"
                ") VALUES(?,?,?,?,?,?)",
                (
                    user["id"],
                    patient_id,
                    title,
                    request.form.get("notes", ""),
                    t,
                    t,
                ),
            )

            plan_id = cursor.lastrowid

            for order, meal in enumerate(MEALS):
                db.execute(
                    "INSERT INTO diet_plan_meals("
                    "diet_plan_id,meal_type,sort_order"
                    ") VALUES(?,?,?)",
                    (
                        plan_id,
                        meal,
                        order,
                    ),
                )

            db.commit()

            return redirect(
                url_for(
                    "workspace.plan_detail",
                    plan_id=plan_id,
                )
            )

    rows = db.execute(
        "SELECT diet_plans.*,patients.full_name "
        "FROM diet_plans "
        "JOIN patients ON patients.id=diet_plans.patient_id "
        "WHERE diet_plans.user_id=? "
        "ORDER BY updated_at DESC",
        (user["id"],),
    ).fetchall()

    patients = db.execute(
        "SELECT id,full_name FROM patients "
        "WHERE user_id=? AND archived_at IS NULL",
        (user["id"],),
    ).fetchall()

    return render_template(
        "plans.html",
        plans=rows,
        patients=patients,
        csrf_token=csrf_token(),
    )

@workspace.route("/foods/recipes/new", methods=["GET", "POST"])
@login_required
def recipe_new():
    user = current_user()
    db = connect(current_app.config["DATABASE"])

    if request.method == "POST":
        if not valid_csrf(request.form.get("csrf_token")):
            flash("Your form expired. Please try again.", "error")
            return redirect(url_for("workspace.recipe_new"))

        # ---------------------------------------------------------
        # RECIPE INFORMATION
        # ---------------------------------------------------------

        name = request.form.get("name", "").strip()
        food_type = request.form.get("food_type", "Vegetarian").strip()
        category = request.form.get("category", "").strip()
        meal_type = request.form.get("meal_type", "").strip()

        if not name:
            flash("Recipe name is required.", "error")
            return redirect(url_for("workspace.recipe_new"))

        try:
            servings = float(request.form.get("servings", 1))
        except (TypeError, ValueError):
            flash("Servings must be a valid number.", "error")
            return redirect(url_for("workspace.recipe_new"))

        if servings <= 0:
            flash("Servings must be greater than zero.", "error")
            return redirect(url_for("workspace.recipe_new"))

        preparation_method = request.form.get(
            "preparation_method", ""
        ).strip()

        notes = request.form.get("notes", "").strip()

        # ---------------------------------------------------------
        # INGREDIENTS
        # ---------------------------------------------------------

        food_ids = request.form.getlist("ingredient_food_id[]")
        quantities = request.form.getlist("ingredient_quantity[]")
        units = request.form.getlist("ingredient_unit[]")

        if not food_ids:
            flash("Add at least one ingredient.", "error")
            return redirect(url_for("workspace.recipe_new"))

        if not (
            len(food_ids)
            == len(quantities)
            == len(units)
        ):
            flash("Invalid ingredient data.", "error")
            return redirect(url_for("workspace.recipe_new"))

        ingredients = []

        try:
            for food_id_raw, quantity_raw, unit_raw in zip(
                food_ids,
                quantities,
                units,
            ):
                if not food_id_raw:
                    raise ValueError("food")

                food_id = int(food_id_raw)

                quantity = float(quantity_raw)

                unit = unit_raw.strip()

                if quantity <= 0:
                    raise ValueError("quantity")

                if not unit:
                    raise ValueError("unit")

                # -------------------------------------------------
                # Verify food belongs to shared library or user
                # -------------------------------------------------

                food = db.execute(
                    """
                    SELECT id
                    FROM foods
                    WHERE id = ?
                      AND (user_id IS NULL OR user_id = ?)
                    """,
                    (food_id, user["id"]),
                ).fetchone()

                if not food:
                    raise ValueError("food")

                ingredients.append(
                    {
                        "food_id": food_id,
                        "quantity": quantity,
                        "unit": unit,
                    }
                )

        except (TypeError, ValueError):
            flash(
                "Please check all ingredients, quantities, and units.",
                "error",
            )
            return redirect(url_for("workspace.recipe_new"))

        # ---------------------------------------------------------
        # SAVE RECIPE + INGREDIENTS
        # ---------------------------------------------------------

        timestamp = now()

        try:
            with db:
                cursor = db.execute(
                    """
                    INSERT INTO recipes (
                        user_id,
                        name,
                        food_type,
                        category,
                        meal_type,
                        servings,
                        preparation_method,
                        notes,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user["id"],
                        name,
                        food_type,
                        category,
                        meal_type,
                        servings,
                        preparation_method,
                        notes,
                        timestamp,
                        timestamp,
                    ),
                )

                recipe_id = cursor.lastrowid

                for ingredient in ingredients:
                    db.execute(
                        """
                        INSERT INTO recipe_ingredients (
                            recipe_id,
                            food_id,
                            quantity,
                            unit,
                            notes,
                            created_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            recipe_id,
                            ingredient["food_id"],
                            ingredient["quantity"],
                            ingredient["unit"],
                            "",
                            timestamp,
                        ),
                    )

        except Exception:
            flash(
                "Unable to save the recipe. Please try again.",
                "error",
            )
            return redirect(url_for("workspace.recipe_new"))

        flash("Recipe saved successfully.", "success")

        return redirect(
            url_for(
                "workspace.recipe_detail",
                recipe_id=recipe_id,
            )
        )

    # -------------------------------------------------------------
    # LOAD FOODS FOR FORM
    # -------------------------------------------------------------

    foods = db.execute(
        """
        SELECT
            id,
            name,
            food_type,
            category,
            serving_size,
            unit,
            calories,
            protein,
            carbohydrates,
            fat,
            fiber
        FROM foods
        WHERE user_id IS NULL OR user_id=?
        ORDER BY category, name
        """,
        (user["id"],),
    ).fetchall()

    return render_template(
        "recipe_new.html",
        foods=foods,
        csrf_token=csrf_token(),
    )

@workspace.route("/foods/recipes/<int:recipe_id>")
@login_required
def recipe_detail(recipe_id):
    user = current_user()
    db = connect(current_app.config["DATABASE"])

    recipe = db.execute(
        """
        SELECT
            id,
            name,
            food_type,
            category,
            meal_type,
            servings,
            preparation_method,
            notes,
            created_at,
            updated_at
        FROM recipes
        WHERE id = ?
          AND user_id = ?
        """,
        (recipe_id, user["id"]),
    ).fetchone()

    if not recipe:
        return ("Recipe not found", 404)

    ingredients = db.execute(
        """
        SELECT
            recipe_ingredients.id,
            recipe_ingredients.food_id,
            recipe_ingredients.quantity,
            recipe_ingredients.unit,
            recipe_ingredients.notes,

            foods.name,
            foods.serving_size,
            foods.calories,
            foods.protein,
            foods.carbohydrates,
            foods.fat,
            foods.fiber

        FROM recipe_ingredients

        JOIN foods
            ON foods.id = recipe_ingredients.food_id

        WHERE recipe_ingredients.recipe_id = ?

        ORDER BY recipe_ingredients.id
        """,
        (recipe_id,),
    ).fetchall()

    # ---------------------------------------------------------
    # NUTRITION TOTALS
    # ---------------------------------------------------------

    totals = {
        "calories": 0.0,
        "protein": 0.0,
        "carbohydrates": 0.0,
        "fat": 0.0,
        "fiber": 0.0,
    }

    ingredient_rows = []

    for ingredient in ingredients:
        quantity = float(ingredient["quantity"] or 0)

        # Current IFCT food values are stored per 100 g.
        factor = quantity / 100.0

        nutrition = {
            "calories": float(
                ingredient["calories"] or 0
            ) * factor,

            "protein": float(
                ingredient["protein"] or 0
            ) * factor,

            "carbohydrates": float(
                ingredient["carbohydrates"] or 0
            ) * factor,

            "fat": float(
                ingredient["fat"] or 0
            ) * factor,

            "fiber": float(
                ingredient["fiber"] or 0
            ) * factor,
        }

        for key in totals:
            totals[key] += nutrition[key]

        ingredient_rows.append(
            {
                "name": ingredient["name"],
                "quantity": quantity,
                "unit": ingredient["unit"],
                "nutrition": nutrition,
            }
        )

    # ---------------------------------------------------------
    # PER SERVING
    # ---------------------------------------------------------

    servings = float(recipe["servings"] or 1)

    per_serving = {
        key: totals[key] / servings
        for key in totals
    }

    return render_template(
        "recipe_detail.html",
        recipe=dict(recipe),
        ingredients=ingredient_rows,
        totals=totals,
        per_serving=per_serving,
    )

@workspace.route(
    "/plans/<int:plan_id>",
    methods=["GET", "POST"],
)
@login_required
def plan_detail(plan_id):
    user = current_user()
    db = connect(current_app.config["DATABASE"])

    plan = db.execute(
        "SELECT diet_plans.*,patients.full_name "
        "FROM diet_plans "
        "JOIN patients ON patients.id=diet_plans.patient_id "
        "WHERE diet_plans.id=? AND diet_plans.user_id=?",
        (
            plan_id,
            user["id"],
        ),
    ).fetchone()

    if not plan:
        return ("Not found", 404)

    if request.method == "POST" and valid_csrf(
        request.form.get("csrf_token")
    ):
        meal_id = int(request.form.get("meal_id", 0))
        food_id = int(request.form.get("food_id", 0))
        quantity = float(request.form.get("quantity", 0))

        meal = db.execute(
            "SELECT id FROM diet_plan_meals "
            "WHERE id=? AND diet_plan_id=?",
            (
                meal_id,
                plan_id,
            ),
        ).fetchone()

        food = db.execute(
            "SELECT * FROM foods "
            "WHERE id=? AND (user_id IS NULL OR user_id=?)",
            (
                food_id,
                user["id"],
            ),
        ).fetchone()

        if meal and food and quantity > 0:
            db.execute(
                "INSERT INTO diet_plan_foods("
                "meal_id,food_id,quantity,unit"
                ") VALUES(?,?,?,?)",
                (
                    meal_id,
                    food_id,
                    quantity,
                    food["unit"],
                ),
            )

            db.execute(
                "UPDATE diet_plans SET updated_at=? WHERE id=?",
                (
                    now(),
                    plan_id,
                ),
            )

            db.commit()
            flash("Food added.", "success")

        else:
            flash(
                "Choose a food and quantity greater than zero.",
                "error",
            )

        return redirect(
            url_for(
                "workspace.plan_detail",
                plan_id=plan_id,
            )
        )

    meals = db.execute(
        "SELECT * FROM diet_plan_meals "
        "WHERE diet_plan_id=? "
        "ORDER BY sort_order",
        (plan_id,),
    ).fetchall()

    foods = db.execute(
        "SELECT * FROM foods "
        "WHERE user_id IS NULL OR user_id=? "
        "ORDER BY name",
        (user["id"],),
    ).fetchall()

    items = db.execute(
        "SELECT diet_plan_foods.*,foods.name,foods.calories,"
        "foods.protein,foods.carbohydrates,foods.fat "
        "FROM diet_plan_foods "
        "JOIN foods ON foods.id=diet_plan_foods.food_id "
        "WHERE meal_id IN ("
        "SELECT id FROM diet_plan_meals "
        "WHERE diet_plan_id=?"
        ")",
        (plan_id,),
    ).fetchall()

    totals = {
        key: sum(
            item[key] * item["quantity"]
            for item in items
        )
        for key in (
            "calories",
            "protein",
            "carbohydrates",
            "fat",
        )
    }

    return render_template(
        "plan_detail.html",
        plan=plan,
        meals=meals,
        foods=foods,
        items=items,
        totals=totals,
        csrf_token=csrf_token(),
    )


@workspace.get("/reports")
@login_required
def reports():
    user = current_user()
    db = connect(current_app.config["DATABASE"])

    rows = db.execute(
        "SELECT reports.*,patients.full_name "
        "FROM reports "
        "JOIN patients ON patients.id=reports.patient_id "
        "WHERE reports.user_id=? "
        "ORDER BY reports.created_at DESC",
        (user["id"],),
    ).fetchall()

    return render_template(
        "reports.html",
        reports=rows,
    )


@workspace.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    user = current_user()

    if request.method == "POST" and valid_csrf(
        request.form.get("csrf_token")
    ):
        name = request.form.get(
            "display_name",
            "",
        ).strip()

        if 2 <= len(name) <= 80:
            db = connect(
                current_app.config["DATABASE"]
            )

            db.execute(
                "UPDATE users SET display_name=?,updated_at=? "
                "WHERE id=?",
                (
                    name,
                    now(),
                    user["id"],
                ),
            )

            db.commit()

            flash("Profile updated.", "success")

            return redirect(
                url_for("workspace.settings")
            )

        flash(
            "Display name must contain 2–80 characters.",
            "error",
        )

    return render_template(
        "settings.html",
        user=user,
        csrf_token=csrf_token(),
    )