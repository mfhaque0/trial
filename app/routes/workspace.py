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