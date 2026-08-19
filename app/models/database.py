"""SQLite schema and connection helpers. Queries are always parameterised."""

import sqlite3
from pathlib import Path


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    display_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    full_name TEXT NOT NULL,
    date_of_birth TEXT,
    sex TEXT,
    contact TEXT,
    height REAL,
    height_unit TEXT,
    weight REAL,
    weight_unit TEXT,
    activity_level TEXT,
    goal TEXT,
    allergies TEXT NOT NULL DEFAULT '',
    dietary_preferences TEXT NOT NULL DEFAULT '',
    medical_notes TEXT NOT NULL DEFAULT '',
    archived_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS assessments (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    height_m REAL NOT NULL,
    weight_kg REAL NOT NULL,
    bmi REAL NOT NULL,
    bmi_category TEXT NOT NULL,
    bmr INTEGER NOT NULL,
    tdee INTEGER NOT NULL,
    target INTEGER NOT NULL,
    macros_json TEXT NOT NULL,
    water_litres REAL NOT NULL,
    activity_level TEXT NOT NULL,
    goal TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS foods (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    serving_size TEXT NOT NULL,
    unit TEXT NOT NULL,
    calories REAL NOT NULL,
    protein REAL NOT NULL,
    carbohydrates REAL NOT NULL,
    fat REAL NOT NULL,
    fiber REAL NOT NULL DEFAULT 0,
    food_type TEXT NOT NULL DEFAULT 'Vegetarian',
    meal_type TEXT NOT NULL DEFAULT '',
    is_demo INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS exchanges (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    category TEXT NOT NULL,
    name TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    is_demo INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS exchange_groups (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    category TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    source_name TEXT NOT NULL,
    source_version TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS exchange_items (
    id INTEGER PRIMARY KEY,
    exchange_group_id INTEGER NOT NULL
        REFERENCES exchange_groups(id) ON DELETE CASCADE,
    food_id INTEGER
        REFERENCES foods(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    quantity REAL NOT NULL CHECK(quantity > 0),
    unit TEXT NOT NULL,
    calories REAL,
    carbohydrates REAL,
    protein REAL,
    fat REAL,
    fiber REAL,
    notes TEXT NOT NULL DEFAULT '',
    source_reference TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS diet_plans (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    title TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS recipes (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    food_type TEXT NOT NULL DEFAULT 'Vegetarian',
    category TEXT NOT NULL DEFAULT '',
    meal_type TEXT NOT NULL DEFAULT '',
    servings REAL NOT NULL DEFAULT 1 CHECK(servings > 0),
    preparation_method TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS recipe_ingredients (
    id INTEGER PRIMARY KEY,
    recipe_id INTEGER NOT NULL
        REFERENCES recipes(id) ON DELETE CASCADE,
    food_id INTEGER NOT NULL
        REFERENCES foods(id),
    quantity REAL NOT NULL CHECK(quantity > 0),
    unit TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_recipes_owner
    ON recipes(user_id);

CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_recipe
    ON recipe_ingredients(recipe_id);

CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_food
    ON recipe_ingredients(food_id);

CREATE TABLE IF NOT EXISTS diet_plan_meals (
    id INTEGER PRIMARY KEY,
    diet_plan_id INTEGER NOT NULL
        REFERENCES diet_plans(id) ON DELETE CASCADE,
    meal_type TEXT NOT NULL,
    sort_order INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS diet_plan_foods (
    id INTEGER PRIMARY KEY,
    meal_id INTEGER NOT NULL
        REFERENCES diet_plan_meals(id) ON DELETE CASCADE,
    food_id INTEGER NOT NULL REFERENCES foods(id),
    quantity REAL NOT NULL CHECK(quantity > 0),
    unit TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    assessment_id INTEGER REFERENCES assessments(id),
    diet_plan_id INTEGER REFERENCES diet_plans(id),
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_patients_owner
    ON patients(user_id, archived_at);

CREATE INDEX IF NOT EXISTS idx_assessments_owner
    ON assessments(user_id, patient_id);

CREATE INDEX IF NOT EXISTS idx_plans_owner
    ON diet_plans(user_id, patient_id);

CREATE INDEX IF NOT EXISTS idx_exchange_groups_owner
    ON exchange_groups(user_id);

CREATE INDEX IF NOT EXISTS idx_exchange_items_group
    ON exchange_items(exchange_group_id);

CREATE INDEX IF NOT EXISTS idx_exchange_items_food
    ON exchange_items(food_id);

CREATE TABLE IF NOT EXISTS component_definitions (
    id INTEGER PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL,
    unit TEXT NOT NULL,
    basis TEXT NOT NULL,
    is_essential INTEGER NOT NULL DEFAULT 0,
    description TEXT NOT NULL DEFAULT '',
    source_name TEXT NOT NULL DEFAULT 'ICMR-NIN IFCT 2017',
    source_version TEXT NOT NULL DEFAULT 'IFCT 2017',
    source_table TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_component_definitions_category
    ON component_definitions(category);

CREATE INDEX IF NOT EXISTS idx_component_definitions_name
    ON component_definitions(name);

CREATE TABLE IF NOT EXISTS food_components (
    id INTEGER PRIMARY KEY,
    food_id INTEGER NOT NULL
        REFERENCES foods(id) ON DELETE CASCADE,
    component_id INTEGER NOT NULL
        REFERENCES component_definitions(id) ON DELETE CASCADE,
    value REAL,
    standard_deviation REAL,
    unit TEXT NOT NULL,
    basis TEXT NOT NULL,
    measurement_status TEXT NOT NULL DEFAULT 'reported',
    source_food_code TEXT NOT NULL DEFAULT '',
    source_reference TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    UNIQUE(food_id, component_id),
    CHECK (
        measurement_status IN (
            'reported',
            'below_detection_limit',
            'not_reported'
        )
    )
);

CREATE INDEX IF NOT EXISTS idx_food_components_food
    ON food_components(food_id);

CREATE INDEX IF NOT EXISTS idx_food_components_component
    ON food_components(component_id);

CREATE INDEX IF NOT EXISTS idx_food_components_source_code
    ON food_components(source_food_code);

CREATE INDEX IF NOT EXISTS idx_food_components_status
    ON food_components(measurement_status);

CREATE TABLE IF NOT EXISTS food_sources (
    id INTEGER PRIMARY KEY,
    food_id INTEGER NOT NULL UNIQUE
        REFERENCES foods(id) ON DELETE CASCADE,
    source_name TEXT NOT NULL,
    source_version TEXT NOT NULL,
    source_food_code TEXT NOT NULL,
    source_food_name TEXT NOT NULL,
    ifct_group_code TEXT NOT NULL DEFAULT '',
    ifct_group_name TEXT NOT NULL DEFAULT '',
    regions_count INTEGER,
    source_sequence INTEGER,
    source_reference TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    UNIQUE(source_name, source_version, source_food_code)
);

CREATE INDEX IF NOT EXISTS idx_food_sources_food
    ON food_sources(food_id);

CREATE INDEX IF NOT EXISTS idx_food_sources_code
    ON food_sources(source_food_code);

CREATE INDEX IF NOT EXISTS idx_food_sources_group
    ON food_sources(ifct_group_code);
"""


def connect(path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialise(path: str | Path) -> None:
    with connect(path) as connection:
        # Lightweight migration from the pre-V1 single-user patient prototype.
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }

        if "patients" in tables:
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(patients)")
            }

            if "user_id" not in columns:
                connection.execute(
                    "ALTER TABLE patients ADD COLUMN user_id INTEGER"
                )

            if "full_name" not in columns:
                connection.execute(
                    "ALTER TABLE patients ADD COLUMN full_name TEXT"
                )

                if "name" in columns:
                    connection.execute(
                        "UPDATE patients SET full_name = name "
                        "WHERE full_name IS NULL"
                    )

            if "archived_at" not in columns:
                connection.execute(
                    "ALTER TABLE patients ADD COLUMN archived_at TEXT"
                )

        # Migration for food classification fields.
        if "foods" in tables:
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(foods)")
            }

            if "food_type" not in columns:
                connection.execute(
                    "ALTER TABLE foods ADD COLUMN "
                    "food_type TEXT NOT NULL DEFAULT 'Vegetarian'"
                )

            if "meal_type" not in columns:
                connection.execute(
                    "ALTER TABLE foods ADD COLUMN "
                    "meal_type TEXT NOT NULL DEFAULT ''"
                )

        connection.executescript(SCHEMA)