class CalculationError(Exception):
    """Raised when nutrition calculation inputs are invalid."""
    pass


def _positive_float(value, label):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise CalculationError(f"A valid {label} is required.")

    if number <= 0:
        raise CalculationError(f"{label.capitalize()} must be greater than zero.")

    return number


def _non_negative_float(value, label):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise CalculationError(f"A valid {label} is required.")

    if number < 0:
        raise CalculationError(f"{label.capitalize()} cannot be negative.")

    return number


def _percentage(value, label):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise CalculationError(f"A valid {label} percentage is required.")

    if number < 0 or number > 100:
        raise CalculationError(
            f"{label.capitalize()} percentage must be between 0 and 100."
        )

    return number


def calculate_assessment(data):
    """
    Core nutrition calculation engine.

    This function is the single source of truth for the application's
    nutrition calculations. Frontend code should display these results
    rather than reimplementing the formulas.
    """

    # ============================================================
    # 1. PATIENT / AGE
    # ============================================================

    patient_name = str(data.get("patient_name", "")).strip()

    if not patient_name:
        raise CalculationError("Patient name is required.")

    if len(patient_name) > 120:
        raise CalculationError("Patient name is too long.")

    age = _positive_float(data.get("age"), "age")

    # This calculator is designed for adult nutrition assessment.
    if age < 18 or age > 120:
        raise CalculationError(
            "This calculator currently supports adults aged 18 to 120 years."
        )

    # ============================================================
    # 2. SEX
    # ============================================================

    sex = str(data.get("sex", "")).strip().lower()

    if sex not in {"male", "female"}:
        raise CalculationError(
            "Sex must be specified as 'male' or 'female'."
        )

    # ============================================================
    # 3. WEIGHT NORMALIZATION
    # ============================================================

    weight = _positive_float(data.get("weight"), "weight")

    weight_unit = str(
        data.get("weight_unit", "kg")
    ).strip().lower()

    if weight_unit == "kg":
        weight_kg = weight

    elif weight_unit == "lb":
        weight_kg = weight * 0.45359237

    else:
        raise CalculationError(
            "Unsupported weight unit. Use 'kg' or 'lb'."
        )

    # Basic adult plausibility validation.
    if weight_kg < 20 or weight_kg > 500:
        raise CalculationError(
            "Weight must be between 20 and 500 kg for this adult calculator."
        )

    # ============================================================
    # 4. HEIGHT NORMALIZATION
    # ============================================================

    height_unit = str(
        data.get("height_unit", "cm")
    ).strip().lower()

    if height_unit == "ft + inches":
        feet = _positive_float(data.get("height"), "height")

        try:
            extra_inches = float(
                data.get("height_inches", 0)
            )
        except (TypeError, ValueError):
            raise CalculationError(
                "A valid additional height in inches is required."
            )

        if extra_inches < 0 or extra_inches >= 12:
            raise CalculationError(
                "Additional inches must be between 0 and less than 12."
            )

        total_inches = (feet * 12.0) + extra_inches
        height_m = total_inches * 0.0254

    else:
        height = _positive_float(
            data.get("height"),
            "height",
        )

        if height_unit == "cm":
            height_m = height / 100.0

        elif height_unit == "m":
            height_m = height

        elif height_unit in {"inches", "inch", "in"}:
            height_m = height * 0.0254

        else:
            raise CalculationError(
                "Unsupported height unit."
            )

    height_cm = height_m * 100.0
    height_in = height_m / 0.0254

    if height_cm < 100 or height_cm > 250:
        raise CalculationError(
            "Height must be between 100 and 250 cm for this adult calculator."
        )

    # ============================================================
    # 5. BMI
    # ============================================================

    bmi = weight_kg / (height_m ** 2)

    if bmi < 18.5:
        bmi_category = "Underweight"
    elif bmi < 25.0:
        bmi_category = "Normal / Healthy Weight"
    elif bmi < 30.0:
        bmi_category = "Overweight"
    else:
        bmi_category = "Obesity"

    # BMI is a screening measure, not a diagnosis.

    # ============================================================
    # 6. IBW — DEVINE REFERENCE
    # ============================================================

    if sex == "male":
        ibw = 50.0 + 2.3 * (height_in - 60.0)
    else:
        ibw = 45.5 + 2.3 * (height_in - 60.0)

    # Prevent a mathematically negative reference value at unusual heights.
    ibw = max(0.0, ibw)

    # ============================================================
    # 7. Mifflin-St Jeor REE / BMR
    # ============================================================

    if sex == "male":
        ree = (
            (10.0 * weight_kg)
            + (6.25 * height_cm)
            - (5.0 * age)
            + 5.0
        )
    else:
        ree = (
            (10.0 * weight_kg)
            + (6.25 * height_cm)
            - (5.0 * age)
            - 161.0
        )

    if ree <= 0:
        raise CalculationError(
            "Calculated resting energy expenditure is invalid."
        )

    # ============================================================
    # 8. ACTIVITY / TDEE
    # ============================================================

    activity = str(
        data.get("activity", "sedentary")
    ).strip().lower()

    activity_factors = {
        "sedentary": 1.20,
        "light": 1.375,
        "moderate": 1.55,
        "very": 1.725,
        "extra": 1.90,
    }

    if activity not in activity_factors:
        raise CalculationError(
            "Unsupported activity level selected."
        )

    activity_factor = activity_factors[activity]

    tdee = ree * activity_factor

    # ============================================================
    # 9. GOAL-BASED CALORIE TARGET
    # ============================================================

    goal = str(
        data.get("goal", "maintain")
    ).strip().lower()

    if goal in {"maintain", "maintenance"}:
        target_calories = tdee
        adjustment = 0.0

    elif goal == "loss":
        deficit = _positive_float(
            data.get("custom_deficit", 500.0),
            "calorie deficit",
        )

        target_calories = tdee - deficit
        adjustment = -deficit

    elif goal == "gain":
        surplus = _positive_float(
            data.get("custom_surplus", 300.0),
            "calorie surplus",
        )

        target_calories = tdee + surplus
        adjustment = surplus

    else:
        raise CalculationError(
            "Unsupported goal. Select loss, gain, or maintain."
        )

    if target_calories <= 0:
        raise CalculationError(
            "Target calories must be greater than zero."
        )

    # Keep this as a review warning rather than pretending
    # that one universal minimum is a prescription.
    warnings = []

    if target_calories < 1200:
        warnings.append(
            "Review required: Target calories are unusually low."
        )

    if bmi >= 30:
        warnings.append(
            "Estimate should be interpreted alongside clinical "
            "assessment (BMI indicates Obesity)."
        )

    # ============================================================
    # 10. STRUCTURED CLINICAL CONTEXT
    # ============================================================

    pregnancy_status = str(
        data.get("pregnancy_status", "")
    ).strip().lower()

    lactation_status = str(
        data.get("lactation_status", "")
    ).strip().lower()

    medical_condition = str(
        data.get("medical_condition", "")
    ).strip()

    dietary_preference = str(
        data.get("dietary_preference", "")
    ).strip()

    medical_notes = str(
        data.get("medical_notes", "")
    ).strip()

    if pregnancy_status in {
        "yes",
        "pregnant",
        "true",
    }:
        warnings.append(
            "Review required: Pregnancy is present. "
            "Standard adult energy and nutrient estimates "
            "may not be appropriate."
        )

    if lactation_status in {
        "yes",
        "lactating",
        "true",
    }:
        warnings.append(
            "Review required: Lactation is present. "
            "Standard adult energy and nutrient estimates "
            "may not be appropriate."
        )

    clinical_text = (
        f"{medical_condition} "
        f"{medical_notes}"
    ).lower()

    if any(
        term in clinical_text
        for term in (
            "renal",
            "kidney",
            "dialysis",
            "hepatic",
            "liver",
            "cardiac",
            "heart",
        )
    ):
        warnings.append(
            "Review required: A medical condition was entered "
            "that may substantially alter protein, fluid, or "
            "energy requirements."
        )

    # ============================================================
    # 11. FLUID REQUIREMENT
    # ============================================================

    min_fluid_factor = 30.0
    max_fluid_factor = 35.0

    custom_fluid_value = data.get(
        "custom_fluid_ml_per_kg"
    )

    if (
        custom_fluid_value is not None
        and str(custom_fluid_value).strip() != ""
    ):
        custom_fluid_factor = _positive_float(
            custom_fluid_value,
            "custom fluid requirement",
        )

        fluid_ml_min = (
            weight_kg * custom_fluid_factor
        )
        fluid_ml_max = fluid_ml_min

    else:
        fluid_ml_min = (
            weight_kg * min_fluid_factor
        )
        fluid_ml_max = (
            weight_kg * max_fluid_factor
        )

    fluid_ml = (
        fluid_ml_min + fluid_ml_max
    ) / 2.0

    fluid_l_min = fluid_ml_min / 1000.0
    fluid_l_max = fluid_ml_max / 1000.0
    fluid_l = fluid_ml / 1000.0

    # ============================================================
    # 12. MACRONUTRIENT SETTINGS
    # ============================================================

    protein_method = str(
        data.get("protein_method", "percent")
    ).strip().lower()

    carbs_pct = _percentage(
        data.get("carbs_pct", 55.0),
        "carbohydrate",
    )

    fat_pct = _percentage(
        data.get("fat_pct", 30.0),
        "fat",
    )

    protein_pct = _percentage(
        data.get("protein_pct", 15.0),
        "protein",
    )

    # ============================================================
    # 13. PROTEIN
    # ============================================================

    if protein_method == "g_per_kg":

        protein_g_per_kg = _positive_float(
            data.get("protein_g_per_kg", 0.83),
            "protein requirement",
        )

        protein_g = (
            weight_kg * protein_g_per_kg
        )

        protein_kcal = protein_g * 4.0

        protein_pct_actual = (
            protein_kcal / target_calories
        ) * 100.0

        # In g/kg mode, carbohydrate + fat percentages
        # must account for the remaining energy.
        macro_total = (
            carbs_pct
            + fat_pct
            + protein_pct_actual
        )

        if abs(macro_total - 100.0) > 0.1:
            raise CalculationError(
                "When protein is calculated by g/kg, "
                "carbohydrate + fat percentages must make "
                "the total macro energy equal 100%. "
                f"Current total: {macro_total:.1f}%."
            )

        protein_method_label = "g/kg/day"

    elif protein_method == "custom_g":

        protein_g = _positive_float(
            data.get("protein_custom_g"),
            "custom protein requirement",
        )

        protein_kcal = protein_g * 4.0

        protein_pct_actual = (
            protein_kcal / target_calories
        ) * 100.0

        macro_total = (
            carbs_pct
            + fat_pct
            + protein_pct_actual
        )

        if abs(macro_total - 100.0) > 0.1:
            raise CalculationError(
                "When protein is entered as custom grams, "
                "carbohydrate + fat percentages must make "
                "the total macro energy equal 100%. "
                f"Current total: {macro_total:.1f}%."
            )

        protein_method_label = "custom g/day"

    elif protein_method == "percent":

        total_pct = (
            carbs_pct
            + protein_pct
            + fat_pct
        )

        if abs(total_pct - 100.0) > 0.1:
            raise CalculationError(
                "Macro percentages must total exactly 100%. "
                f"Current total: {total_pct:.1f}%."
            )

        protein_g = (
            target_calories
            * protein_pct
            / 100.0
            / 4.0
        )

        protein_pct_actual = protein_pct

        protein_method_label = "percentage of calories"

    else:
        raise CalculationError(
            "Unsupported protein calculation method."
        )

    # ============================================================
    # 14. CARBOHYDRATE + FAT
    # ============================================================

    carbs_g = (
        target_calories
        * carbs_pct
        / 100.0
        / 4.0
    )

    fat_g = (
        target_calories
        * fat_pct
        / 100.0
        / 9.0
    )

    # ============================================================
    # 15. MACRO ENERGY CHECK
    # ============================================================

    macro_kcal = (
        protein_g * 4.0
        + carbs_g * 4.0
        + fat_g * 9.0
    )

    macro_difference = (
        macro_kcal - target_calories
    )

    if abs(macro_difference) > 1.0:
        warnings.append(
            "Review required: Macronutrient energy does not "
            "exactly match the target calorie value."
        )

    macros = {
        "protein": {
            "method": protein_method,
            "method_label": protein_method_label,
            "grams": round(protein_g, 1),
            "percentage": round(
                protein_pct_actual,
                1,
            ),
        },
        "carbohydrate": {
            "percentage": round(
                carbs_pct,
                1,
            ),
            "grams": round(
                carbs_g,
                1,
            ),
        },
        "fat": {
            "percentage": round(
                fat_pct,
                1,
            ),
            "grams": round(
                fat_g,
                1,
            ),
        },
    }

    # ============================================================
    # 16. FINAL RESULT
    # ============================================================

    return {
        "patient": {
            "name": patient_name,
            "age": round(age, 1),
            "sex": sex,
            "weight_kg": round(weight_kg, 2),
            "height_cm": round(height_cm, 1),
            "activity": activity,
            "goal": goal,
            "pregnancy_status": pregnancy_status,
            "lactation_status": lactation_status,
            "medical_condition": medical_condition,
            "dietary_preference": dietary_preference,
        },

        "normalised": {
            "height_m": round(height_m, 3),
            "height_cm": round(height_cm, 1),
            "height_in": round(height_in, 2),
            "weight_kg": round(weight_kg, 2),
        },

        "bmi": {
            "value": round(bmi, 1),
            "category": bmi_category,
        },

        "ibw": {
            "value": round(ibw, 1),
            "method": "Devine reference IBW",
        },

        "bmr": round(ree),

        "ree": {
            "value": round(ree),
            "method": "Mifflin-St Jeor",
            "unit": "kcal/day",
        },

        "activity": {
            "level": activity,
            "factor": activity_factor,
        },

        "tdee": round(tdee),

        "goal": {
            "type": goal,
            "adjustment": round(adjustment),
            "target_calories": round(target_calories),
        },

        "target": round(target_calories),

        "macros": macros,

        "fluid": {
            "method": (
                "custom"
                if custom_fluid_value is not None
                and str(custom_fluid_value).strip() != ""
                else "30–35 mL/kg/day"
            ),
            "estimated_ml_range": [
                round(fluid_ml_min),
                round(fluid_ml_max),
            ],
            "estimated_l_range": [
                round(fluid_l_min, 1),
                round(fluid_l_max, 1),
            ],
            "target_ml": round(fluid_ml),
            "target_l": round(fluid_l, 1),
        },

        # Kept for backward compatibility with existing database/UI.
        "water_litres": round(fluid_l, 1),

        "clinical_context": {
            "pregnancy_status": pregnancy_status,
            "lactation_status": lactation_status,
            "medical_condition": medical_condition,
            "dietary_preference": dietary_preference,
            "medical_notes": medical_notes,
        },

        "warnings": warnings,
    }