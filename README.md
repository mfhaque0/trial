# Nourish — Nutrition Workspace

A multi-user Flask nutrition workspace with secure accounts, patient records, assessment history, food references, diet plans, reports foundation, and reusable adult calculation services.

## Run locally

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`. Set `DIETITIAN_SECRET_KEY` before adding session-based features in production.

SQLite is initialised reproducibly in `instance/` on startup and is excluded from version control. Set `DIETITIAN_SECRET_KEY` in production and deploy behind HTTPS with a production WSGI server.

## Test

```bash
python -m unittest discover -s tests -v
```

## Architecture

```
Web frontend / future mobile client → Flask JSON API → reusable nutrition services → SQLite repositories / structured data
```

- `app/routes/`: Jinja page and API endpoints
- `app/services/calculations.py`: validation, conversion, formulas
- `app/models/database.py`: reproducible SQLite schema for users, patients, assessments, foods, exchanges, diet plans, meals, foods, and report records
- `data/exchanges.json`: editable exchange-list structure

## API

`POST /api/calculators/assessment` accepts JSON such as `{"age":32,"sex":"female","height_unit":"cm","height":165,"weight":65,"weight_unit":"kg","activity":"moderate","goal":"maintain","custom_macros":false}`.

Responses contain `bmi`, `bmr`, `tdee`, `target`, `macros`, `water_litres`, and `warnings`, so Android, iOS, and desktop clients can use the same logic.

## Methodology

BMI normalises height to metres and weight to kilograms. BMR uses Mifflin–St Jeor; TDEE applies the selected activity factor. The target applies configurable goal adjustments and returns a review warning for unusually low targets rather than silently changing them. Fluid is a general `weight_kg × 0.033` estimate. All values are estimates, not clinical prescriptions.

## V1 features

Accounts use Werkzeug password hashes and server sessions. Every patient, assessment, plan, and report query is scoped by `user_id`; records are archived rather than deleted. Food and exchange structures are editable and development values are never presented as verified clinical data. Diet plan meals are normalised into `diet_plans`, `diet_plan_meals`, and `diet_plan_foods`.

## Backup and mobile readiness

The database remains private in `instance/`; no raw database export endpoint is exposed. The JSON calculation and patient APIs are intentionally separate from templates, allowing future mobile clients to reuse backend services. Add encrypted, authenticated backups before any user-facing export feature.

## Recommended next phase

Add clinician-approved regional food/exchange data, reportlab/WeasyPrint PDF rendering, signed backup exports, patient editing UI, and automated browser accessibility tests.
