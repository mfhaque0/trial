from pathlib import Path
import csv
import sqlite3
import re


DB_PATH = Path("instance/dietitian.sqlite3")
DATA_DIR = Path("data/ifct")

FOODS_MASTER = DATA_DIR / "foods_master.csv"
TABLE1 = DATA_DIR / "table1_proximate.csv"
TABLE11 = DATA_DIR / "table11_oligosaccharides_phytosterols_phytates_saponins.csv"
TABLE12_SAT = DATA_DIR / "table12_saturated_fatty_acids.csv"
TABLE12_UNSAT = DATA_DIR / "table12_unsaturated_fatty_acids.csv"


SOURCE_NAME = "ICMR-NIN IFCT 2017"
SOURCE_VERSION = "IFCT 2017"


def parse_value(value):
    """
    Convert CSV numeric value to float.

    Current extracted CSVs contain central values only.
    Blank cells are preserved as None.
    """
    if value is None:
        return None

    value = value.strip()

    if not value:
        return None

    if "±" in value:
        value = value.split("±", 1)[0]

    try:
        return float(value)
    except ValueError:
        return None


def load_csv(path):
    with path.open(
        encoding="utf-8",
        newline="",
    ) as handle:
        return list(csv.DictReader(handle))


def natural_code_key(code):
    match = re.match(r"^([A-Z]+)(\d+)$", code)
    if not match:
        return (code, 0)
    return (match.group(1), int(match.group(2)))


def component_definitions():
    """
    All components represented by the four extracted IFCT tables.
    """

    definitions = []

    # ------------------------------------------------------------
    # TABLE 1 - PROXIMATE PRINCIPLES
    # ------------------------------------------------------------

    table1 = [
        ("WATER", "Water", "proximate", "g", "per_100g", 0,
         "Water content."),
        ("PROTCNT", "Protein", "proximate", "g", "per_100g", 1,
         "Protein content."),
        ("ASH", "Ash", "proximate", "g", "per_100g", 0,
         "Total ash."),
        ("FATCE", "Fat", "proximate", "g", "per_100g", 1,
         "Total fat."),
        ("FIBTG", "Total dietary fibre", "dietary_fibre", "g", "per_100g", 1,
         "Total dietary fibre."),
        ("FIBINS", "Insoluble dietary fibre", "dietary_fibre", "g", "per_100g", 0,
         "Insoluble dietary fibre."),
        ("FIBSOL", "Soluble dietary fibre", "dietary_fibre", "g", "per_100g", 0,
         "Soluble dietary fibre."),
        ("CHOAVLDF", "Available carbohydrate", "carbohydrate", "g", "per_100g", 1,
         "Available carbohydrate."),
        ("ENERC", "Energy", "energy", "kJ", "per_100g", 1,
         "Energy value."),
    ]

    for row in table1:
        definitions.append(row)

    # ------------------------------------------------------------
    # TABLE 11
    # ------------------------------------------------------------

    table11 = [
        ("RAFS", "Raffinose", "oligosaccharide", "g", "per_100g", 0,
         "Raffinose."),
        ("STAS", "Stachyose", "oligosaccharide", "g", "per_100g", 0,
         "Stachyose."),
        ("VERS", "Verbascose", "oligosaccharide", "g", "per_100g", 0,
         "Verbascose."),
        ("AJUG", "Ajugose", "oligosaccharide", "g", "per_100g", 0,
         "Ajugose."),
        ("CAMT", "Campesterol", "phytosterol", "mg", "per_100g", 0,
         "Campesterol."),
        ("STGSTR", "Stigmasterol", "phytosterol", "mg", "per_100g", 0,
         "Stigmasterol."),
        ("BETA_SIT", "Beta-sitosterol", "phytosterol", "mg", "per_100g", 0,
         "Beta-sitosterol."),
        ("PHYTAC", "Phytate", "phytate", "mg", "per_100g", 0,
         "Phytate."),
        ("SAPONIN", "Total saponin", "saponin", "g", "per_100g", 0,
         "Total saponin."),
    ]

    for row in table11:
        definitions.append(row)

    # ------------------------------------------------------------
    # TABLE 12 - SATURATED FATTY ACIDS
    # ------------------------------------------------------------

    saturated = [
        ("F4D0", "Butyric acid", "fatty_acid", "g", "per_100g", 0,
         "Butyric acid (C4:0)."),
        ("F6D0", "Caproic acid", "fatty_acid", "g", "per_100g", 0,
         "Caproic acid (C6:0)."),
        ("F8D0", "Caprylic acid", "fatty_acid", "g", "per_100g", 0,
         "Caprylic acid (C8:0)."),
        ("F10D0", "Capric acid", "fatty_acid", "g", "per_100g", 0,
         "Capric acid (C10:0)."),
        ("F12D0", "Lauric acid", "fatty_acid", "g", "per_100g", 0,
         "Lauric acid (C12:0)."),
        ("F14D0", "Myristic acid", "fatty_acid", "g", "per_100g", 0,
         "Myristic acid (C14:0)."),
        ("F16D0", "Palmitic acid", "fatty_acid", "g", "per_100g", 0,
         "Palmitic acid (C16:0)."),
        ("F18D0", "Stearic acid", "fatty_acid", "g", "per_100g", 0,
         "Stearic acid (C18:0)."),
        ("F20D0", "Arachidic acid", "fatty_acid", "g", "per_100g", 0,
         "Arachidic acid (C20:0)."),
        ("F22D0", "Behenic acid", "fatty_acid", "g", "per_100g", 0,
         "Behenic acid (C22:0)."),
        ("F24D0", "Lignoceric acid", "fatty_acid", "g", "per_100g", 0,
         "Lignoceric acid (C24:0)."),
    ]

    for row in saturated:
        definitions.append(row)

    # ------------------------------------------------------------
    # TABLE 12 - UNSATURATED FATTY ACIDS / TOTALS
    # ------------------------------------------------------------

    unsaturated = [
        ("F14D1", "Myristoleic acid", "fatty_acid", "g", "per_100g", 0,
         "Myristoleic acid."),
        ("F16D1", "Palmitoleic acid", "fatty_acid", "g", "per_100g", 0,
         "Palmitoleic acid."),
        ("F18D1TN9", "Elaidic acid", "fatty_acid", "g", "per_100g", 0,
         "Elaidic acid."),
        ("F18D1N9", "Oleic acid", "fatty_acid", "g", "per_100g", 1,
         "Oleic acid."),
        ("F20D1N9", "Eicosenoic acid", "fatty_acid", "g", "per_100g", 0,
         "Eicosenoic acid."),
        ("F22D1N9", "Erucic acid", "fatty_acid", "g", "per_100g", 0,
         "Erucic acid."),
        ("F18D2N6", "Linoleic acid", "fatty_acid", "g", "per_100g", 1,
         "Linoleic acid."),
        ("F18D3N3", "Alpha-linolenic acid", "fatty_acid", "g", "per_100g", 1,
         "Alpha-linolenic acid."),
        ("FASAT", "Total saturated fatty acids", "fatty_acid_total", "g", "per_100g", 1,
         "Total saturated fatty acids."),
        ("FAMS", "Total monounsaturated fatty acids", "fatty_acid_total", "g", "per_100g", 1,
         "Total monounsaturated fatty acids."),
        ("FAPU", "Total polyunsaturated fatty acids", "fatty_acid_total", "g", "per_100g", 1,
         "Total polyunsaturated fatty acids."),
    ]

    for row in unsaturated:
        definitions.append(row)

    return definitions


def ensure_component_definitions(db):
    definitions = component_definitions()

    for (
        code,
        name,
        category,
        unit,
        basis,
        essential,
        description,
    ) in definitions:

        db.execute(
            """
            INSERT INTO component_definitions(
                code,
                name,
                category,
                unit,
                basis,
                is_essential,
                description,
                source_name,
                source_version,
                source_table
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(code) DO UPDATE SET
                name=excluded.name,
                category=excluded.category,
                unit=excluded.unit,
                basis=excluded.basis,
                is_essential=excluded.is_essential,
                description=excluded.description,
                source_name=excluded.source_name,
                source_version=excluded.source_version,
                source_table=excluded.source_table
            """,
            (
                code,
                name,
                category,
                unit,
                basis,
                essential,
                description,
                SOURCE_NAME,
                SOURCE_VERSION,
                "",
            ),
        )

    return len(definitions)


def load_food_master():
    rows = load_csv(FOODS_MASTER)

    foods = {}

    for row in rows:
        code = row["source_food_code"].strip()

        foods[code] = {
            "source_sequence": int(row["source_sequence"]),
            "source_food_code": code,
            "source_food_name": row["source_food_name"].strip(),
            "ifct_group_code": row["ifct_group_code"].strip(),
            "ifct_group_name": row["ifct_group_name"].strip(),
            "regions_count": int(row["regions_count"]),
        }

    return foods


def import_foods(db, foods):
    """
    Import IFCT foods as system foods.

    Existing user-owned foods are never modified.
    """

    imported = 0
    existing = 0

    for code, food in foods.items():

        row = db.execute(
            """
            SELECT id
            FROM foods
            WHERE user_id IS NULL
              AND name = ?
            LIMIT 1
            """,
            (food["source_food_name"],),
        ).fetchone()

        if row:
            food_id = row["id"]
            existing += 1
        else:
            cursor = db.execute(
                """
                INSERT INTO foods(
                    user_id,
                    name,
                    category,
                    serving_size,
                    unit,
                    calories,
                    protein,
                    carbohydrates,
                    fat,
                    fiber,
                    is_demo,
                    created_at
                )
                VALUES (
                    NULL,
                    ?,
                    ?,
                    '100 g',
                    'g',
                    0,
                    0,
                    0,
                    0,
                    0,
                    1,
                    datetime('now')
                )
                """,
                (
                    food["source_food_name"],
                    food["ifct_group_name"],
                ),
            )

            food_id = cursor.lastrowid
            imported += 1

        db.execute(
            """
            INSERT INTO food_sources(
                food_id,
                source_name,
                source_version,
                source_food_code,
                source_food_name,
                ifct_group_code,
                ifct_group_name,
                regions_count,
                source_sequence,
                source_reference,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(food_id) DO UPDATE SET
                source_name=excluded.source_name,
                source_version=excluded.source_version,
                source_food_code=excluded.source_food_code,
                source_food_name=excluded.source_food_name,
                ifct_group_code=excluded.ifct_group_code,
                ifct_group_name=excluded.ifct_group_name,
                regions_count=excluded.regions_count,
                source_sequence=excluded.source_sequence,
                source_reference=excluded.source_reference
            """,
            (
                food_id,
                SOURCE_NAME,
                SOURCE_VERSION,
                code,
                food["source_food_name"],
                food["ifct_group_code"],
                food["ifct_group_name"],
                food["regions_count"],
                food["source_sequence"],
                f"IFCT 2017 food code {code}",
            ),
        )

    return imported, existing


def get_food_id_map(db):
    rows = db.execute(
        """
        SELECT
            fs.source_food_code,
            fs.food_id
        FROM food_sources fs
        WHERE fs.source_name = ?
          AND fs.source_version = ?
        """,
        (SOURCE_NAME, SOURCE_VERSION),
    ).fetchall()

    return {
        row["source_food_code"]: row["food_id"]
        for row in rows
    }


def get_component_id_map(db):
    rows = db.execute(
        """
        SELECT code, id
        FROM component_definitions
        """
    ).fetchall()

    return {
        row["code"]: row["id"]
        for row in rows
    }


def insert_component(
    db,
    food_id,
    component_id,
    value,
    unit,
    source_food_code,
    source_reference,
):
    if value is None:
        status = "below_detection_limit"
    else:
        status = "reported"

    db.execute(
        """
        INSERT INTO food_components(
            food_id,
            component_id,
            value,
            standard_deviation,
            unit,
            basis,
            measurement_status,
            source_food_code,
            source_reference,
            created_at
        )
        VALUES (?, ?, ?, NULL, ?, 'per_100g', ?, ?, ?, datetime('now'))
        ON CONFLICT(food_id, component_id) DO UPDATE SET
            value=excluded.value,
            standard_deviation=excluded.standard_deviation,
            unit=excluded.unit,
            basis=excluded.basis,
            measurement_status=excluded.measurement_status,
            source_food_code=excluded.source_food_code,
            source_reference=excluded.source_reference
        """,
        (
            food_id,
            component_id,
            value,
            unit,
            status,
            source_food_code,
            source_reference,
        ),
    )


def import_table(
    db,
    path,
    component_columns,
    component_ids,
    food_ids,
    unit,
    table_name,
):
    rows = load_csv(path)

    records = 0
    values = 0
    blanks = 0
    missing_foods = []

    for row in rows:
        code = row["source_food_code"].strip()

        if code not in food_ids:
            missing_foods.append(code)
            continue

        food_id = food_ids[code]

        for column, component_code in component_columns.items():

            value = parse_value(row.get(column))

            if value is None:
                blanks += 1
            else:
                values += 1

            insert_component(
                db=db,
                food_id=food_id,
                component_id=component_ids[component_code],
                value=value,
                unit=unit,
                source_food_code=code,
                source_reference=(
                    f"{SOURCE_NAME}; "
                    f"{SOURCE_VERSION}; "
                    f"{table_name}"
                ),
            )

        records += 1

    if missing_foods:
        raise RuntimeError(
            f"{table_name}: missing food codes: "
            f"{sorted(set(missing_foods), key=natural_code_key)}"
        )

    return records, values, blanks


def update_basic_food_values(db, food_ids):
    """
    Populate the existing foods table's basic nutrition fields
    from Table 1 where available.

    Energy is converted from kJ to kcal because the foods table
    stores calories.
    """

    rows = load_csv(TABLE1)

    updated = 0

    for row in rows:
        code = row["source_food_code"].strip()

        if code not in food_ids:
            continue

        energy_kj = parse_value(row.get("energy_kj"))
        protein = parse_value(row.get("protein"))
        carbohydrate = parse_value(row.get("carbohydrate"))
        fat = parse_value(row.get("fat"))
        fibre = parse_value(row.get("fibre"))

        calories = (
            energy_kj / 4.184
            if energy_kj is not None
            else 0
        )

        db.execute(
            """
            UPDATE foods
            SET
                calories=?,
                protein=?,
                carbohydrates=?,
                fat=?,
                fiber=?
            WHERE id=?
              AND user_id IS NULL
            """,
            (
                calories,
                protein or 0,
                carbohydrate or 0,
                fat or 0,
                fibre or 0,
                food_ids[code],
            ),
        )

        updated += 1

    return updated


def audit(db, expected_foods):
    system_foods = db.execute(
        """
        SELECT COUNT(*)
        FROM foods
        WHERE user_id IS NULL
        """
    ).fetchone()[0]

    sources = db.execute(
        """
        SELECT COUNT(*)
        FROM food_sources
        WHERE source_name=? AND source_version=?
        """,
        (SOURCE_NAME, SOURCE_VERSION),
    ).fetchone()[0]

    components = db.execute(
        """
        SELECT COUNT(*)
        FROM component_definitions
        """
    ).fetchone()[0]

    food_components = db.execute(
        """
        SELECT COUNT(*)
        FROM food_components
        """
    ).fetchone()[0]

    print()
    print("=== IFCT IMPORT AUDIT ===")
    print(f"Expected IFCT foods:       {expected_foods}")
    print(f"System foods:              {system_foods}")
    print(f"IFCT food sources:         {sources}")
    print(f"Component definitions:     {components}")
    print(f"Food component records:    {food_components}")

    if system_foods != expected_foods:
        raise RuntimeError(
            f"Food count mismatch: expected {expected_foods}, "
            f"got {system_foods}"
        )

    if sources != expected_foods:
        raise RuntimeError(
            f"Food-source count mismatch: expected {expected_foods}, "
            f"got {sources}"
        )

    if food_components == 0:
        raise RuntimeError("No food component records were imported.")

    print()
    print("IFCT IMPORT: PASS")


def main():
    if not DB_PATH.exists():
        raise SystemExit(
            f"Database not found: {DB_PATH}"
        )

    required_files = [
        FOODS_MASTER,
        TABLE1,
        TABLE11,
        TABLE12_SAT,
        TABLE12_UNSAT,
    ]

    for path in required_files:
        if not path.exists():
            raise SystemExit(
                f"Required file not found: {path}"
            )

    foods = load_food_master()

    print("IFCT foods in master:", len(foods))

    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")

    try:
        # Make sure the schema exists.
        from app.models.database import SCHEMA
        db.executescript(SCHEMA)

        # --------------------------------------------------------
        # 1. Component definitions
        # --------------------------------------------------------

        definition_count = ensure_component_definitions(db)

        print(
            "Component definitions prepared:",
            definition_count,
        )

        # --------------------------------------------------------
        # 2. IFCT foods + sources
        # --------------------------------------------------------

        imported, existing = import_foods(db, foods)

        print("New system foods imported:", imported)
        print("Existing system foods reused:", existing)

        # --------------------------------------------------------
        # 3. Maps
        # --------------------------------------------------------

        food_ids = get_food_id_map(db)
        component_ids = get_component_id_map(db)

        # --------------------------------------------------------
        # 4. Table 1
        # --------------------------------------------------------

        table1_columns = {
            "water": "WATER",
            "protein": "PROTCNT",
            "ash": "ASH",
            "fat": "FATCE",
            "fibre": "FIBTG",
            "fibre_insoluble": "FIBINS",
            "fibre_soluble": "FIBSOL",
            "carbohydrate": "CHOAVLDF",
            "energy_kj": "ENERC",
        }

        records, values, blanks = import_table(
            db,
            TABLE1,
            table1_columns,
            component_ids,
            food_ids,
            "g",
            "Table 1 - Proximate Principles",
        )

        print(
            f"Table 1: {records} foods, "
            f"{values} reported values, "
            f"{blanks} below-detection blanks"
        )

        # --------------------------------------------------------
        # 5. Table 11
        # --------------------------------------------------------

        table11_columns = {
            "raffinose": "RAFS",
            "stachyose": "STAS",
            "verbascose": "VERS",
            "ajugose": "AJUG",
            "campesterol": "CAMT",
            "stigmasterol": "STGSTR",
            "beta_sitosterol": "BETA_SIT",
            "phytate": "PHYTAC",
            "total_saponin": "SAPONIN",
        }

        records, values, blanks = import_table(
            db,
            TABLE11,
            table11_columns,
            component_ids,
            food_ids,
            "g",
            "Table 11 - Oligosaccharides, Phytosterols, Phytates and Saponins",
        )

        print(
            f"Table 11: {records} foods, "
            f"{values} reported values, "
            f"{blanks} below-detection blanks"
        )

        # Correct units for Table 11 phytosterols/phytate.
        for component_code in (
            "CAMT",
            "STGSTR",
            "BETA_SIT",
            "PHYTAC",
        ):
            db.execute(
                """
                UPDATE food_components
                SET unit='mg'
                WHERE component_id=(
                    SELECT id
                    FROM component_definitions
                    WHERE code=?
                )
                """,
                (component_code,),
            )

        # --------------------------------------------------------
        # 6. Table 12 saturated
        # --------------------------------------------------------

        table12_sat_columns = {
            "f4d0_butyric": "F4D0",
            "f6d0_caproic": "F6D0",
            "f8d0_caprylic": "F8D0",
            "f10d0_capric": "F10D0",
            "f12d0_lauric": "F12D0",
            "f14d0_myristic": "F14D0",
            "f16d0_palmitic": "F16D0",
            "f18d0_stearic": "F18D0",
            "f20d0_arachidic": "F20D0",
            "f22d0_behenic": "F22D0",
            "f24d0_lignoceric": "F24D0",
        }

        records, values, blanks = import_table(
            db,
            TABLE12_SAT,
            table12_sat_columns,
            component_ids,
            food_ids,
            "g",
            "Table 12 - Saturated Fatty Acids",
        )

        print(
            f"Table 12 saturated: {records} foods, "
            f"{values} reported values, "
            f"{blanks} below-detection blanks"
        )

        # --------------------------------------------------------
        # 7. Table 12 unsaturated
        # --------------------------------------------------------

        table12_unsat_columns = {
            "f14d1_myristoleic": "F14D1",
            "f16d1_palmitoleic": "F16D1",
            "f18d1tn9_elaidic": "F18D1TN9",
            "f18d1n9_oleic": "F18D1N9",
            "f20d1n9_eicosenoic": "F20D1N9",
            "f22d1n9_erucic": "F22D1N9",
            "f18d2n6_linoleic": "F18D2N6",
            "f18d3n3_alpha_linolenic": "F18D3N3",
            "fasat_total_saturated": "FASAT",
            "fams_total_monounsaturated": "FAMS",
            "fapu_total_polyunsaturated": "FAPU",
        }

        records, values, blanks = import_table(
            db,
            TABLE12_UNSAT,
            table12_unsat_columns,
            component_ids,
            food_ids,
            "g",
            "Table 12 - Unsaturated Fatty Acids",
        )

        print(
            f"Table 12 unsaturated: {records} foods, "
            f"{values} reported values, "
            f"{blanks} below-detection blanks"
        )

        # --------------------------------------------------------
        # 8. Basic food-library nutrition
        # --------------------------------------------------------

        updated = update_basic_food_values(
            db,
            food_ids,
        )

        print(
            "Basic food nutrition rows updated:",
            updated,
        )

        # --------------------------------------------------------
        # 9. Final audit
        # --------------------------------------------------------

        audit(
            db,
            len(foods),
        )

        db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
