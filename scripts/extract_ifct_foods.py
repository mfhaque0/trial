from pathlib import Path
import csv
import re


SOURCE_TEXT = Path("data/ifct/IFCT2017_16122024.txt")
FOODS_MASTER_CSV = Path("data/ifct/foods_master.csv")
OUTPUT_CSV = Path("data/ifct/table1_proximate.csv")


TABLE1_START_MARKER = "Table 1. PROXIMATE PRINCIPLES AND DIETARY FIBRE"
TABLE2_MARKER = "Table 2"


FOOD_CODE_RE = re.compile(r"^\s*([A-Z]\d{3})(?:\s+|$)")


def clean_text(value):
    return re.sub(r"\s+", " ", value).strip()


def parse_number(value):
    """
    Convert values such as:

        14.59
        14.59±0.40
        1490±10

    to the central reported value.

    Blank / non-numeric values become None.
    """

    if value is None:
        return None

    value = value.strip()

    if not value:
        return None

    # Remove statistical uncertainty.
    value = value.split("±", 1)[0].strip()

    try:
        return float(value)
    except ValueError:
        return None


def load_food_master():
    if not FOODS_MASTER_CSV.exists():
        raise SystemExit(
            f"Food master not found: {FOODS_MASTER_CSV}"
        )

    with FOODS_MASTER_CSV.open(
        encoding="utf-8",
        newline="",
    ) as handle:

        rows = list(csv.DictReader(handle))

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


def find_table1_range(lines):
    """
    Find the first Table 1 block.

    Table 1 starts at the main heading and ends immediately
    before the first actual nutrient Table 2.

    In the current IFCT text this should be approximately:

        Table 1 start: ~1991
        Table 2 start: 3696
    """

    start = None

    for index, line in enumerate(lines):
        if TABLE1_START_MARKER in line:
            start = index
            break

    if start is None:
        raise SystemExit(
            "Could not find Table 1 heading."
        )

    end = None

    for index in range(start + 1, len(lines)):
        line = lines[index].strip()

        # We want the actual nutrient table heading.
        if line == "Table 2":
            end = index
            break

    if end is None:
        raise SystemExit(
            "Could not find the end of Table 1 "
            "(the first 'Table 2' heading)."
        )

    return start, end


def extract_numeric_values(text):
    """
    Extract numeric values from a Table 1 food row.

    Handles:

        9.89
        9.89±0.40
        1490±10

    The central reported value is retained.
    """

    pattern = re.compile(
        r"""
        (?<![A-Za-z0-9])
        [-+]?
        (?:\d+(?:\.\d*)?|\.\d+)
        (?:±
            [-+]?
            (?:\d+(?:\.\d*)?|\.\d+)
        )?
        (?![A-Za-z0-9])
        """,
        re.VERBOSE,
    )

    values = []

    for match in pattern.finditer(text):
        values.append(parse_number(match.group(0)))

    return values


def extract_table1(food_master, lines, start, end):
    """
    Extract Table 1 records.

    Important design choice:

    We use the food master as the authoritative list of food codes
    and names. The PDF is used only for the Table 1 measurements.

    This prevents wrapped food names from corrupting the names.
    """

    expected_codes = set(food_master.keys())

    records = {}

    for index in range(start, end):

        raw_line = lines[index]

        match = FOOD_CODE_RE.match(raw_line)

        if not match:
            continue

        code = match.group(1)

        if code not in expected_codes:
            continue

        # Only use the current physical line for numeric data.
        #
        # Table 1 has the food code, region count and nutrient
        # measurements on the same physical line even when the
        # food name itself is wrapped across lines.

        remainder = raw_line[match.end():]

        values = extract_numeric_values(remainder)

        if not values:
            continue

        expected_regions = food_master[code]["regions_count"]

        # The first numeric value after the food code is the
        # number of regions.
        #
        # Find it by looking for a small integer.
        region_position = None

        for position, value in enumerate(values):
            if value is None:
                continue

            if int(value) == value and 1 <= int(value) <= 20:
                if int(value) == expected_regions:
                    region_position = position
                    break

        if region_position is None:
            continue

        nutrient_values = values[region_position + 1:]

        # Table 1 columns:
        #
        # WATER
        # PROTCNT
        # ASH
        # FATCE
        # FIBTG
        # FIBINS
        # FIBSOL
        # CHOAVLDF
        # ENERC
        #
        # Some foods have blank columns in the PDF. Because pdftotext
        # collapses blank layout columns, we handle the normal cases
        # conservatively rather than inventing values.

        if len(nutrient_values) < 5:
            continue

        # Store the available values in their observed order.
        #
        # For the standard Table 1 rows this is:
        #
        # water, protein, ash, fat, fibre_total,
        # fibre_insoluble, fibre_soluble, carbohydrate, energy
        #
        # For rows with omitted measurements, missing values remain
        # None where the layout can be determined later.

        record = {
            **food_master[code],

            "water": None,
            "protein": None,
            "ash": None,
            "fat": None,
            "fibre_total": None,
            "fibre_insoluble": None,
            "fibre_soluble": None,
            "carbohydrate": None,
            "energy_kj": None,
        }

        # Most Table 1 rows contain all 9 measurements.
        if len(nutrient_values) >= 9:
            (
                record["water"],
                record["protein"],
                record["ash"],
                record["fat"],
                record["fibre_total"],
                record["fibre_insoluble"],
                record["fibre_soluble"],
                record["carbohydrate"],
                record["energy_kj"],
            ) = nutrient_values[:9]

        else:
            # For rows with fewer reported measurements, preserve
            # what is available rather than fabricating values.
            #
            # The first four columns are consistently:
            # water, protein, ash, fat.
            #
            # The final reported number in these rows is generally
            # the energy value.

            if len(nutrient_values) >= 1:
                record["water"] = nutrient_values[0]

            if len(nutrient_values) >= 2:
                record["protein"] = nutrient_values[1]

            if len(nutrient_values) >= 3:
                record["ash"] = nutrient_values[2]

            if len(nutrient_values) >= 4:
                record["fat"] = nutrient_values[3]

            if len(nutrient_values) >= 5:
                record["energy_kj"] = nutrient_values[-1]

        records[code] = record

    return records


def validate(food_master, records):
    expected = set(food_master.keys())
    actual = set(records.keys())

    missing = sorted(
        expected - actual,
        key=lambda code: (code[0], int(code[1:]))
    )

    unexpected = sorted(
        actual - expected,
        key=lambda code: (code[0], int(code[1:]))
    )

    print()
    print("Food master count:", len(expected))
    print("Table 1 records extracted:", len(actual))

    print()

    if missing:
        print("Missing from Table 1:")
        print(missing)
    else:
        print("Missing from Table 1: NONE")

    print()

    if unexpected:
        print("Unexpected Table 1 codes:")
        print(unexpected)
    else:
        print("Unexpected Table 1 codes: NONE")

    return missing, unexpected


def write_csv(records):
    OUTPUT_CSV.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    ordered = sorted(
        records.values(),
        key=lambda row: row["source_sequence"],
    )

    fieldnames = [
        "source_sequence",
        "source_food_code",
        "source_food_name",
        "ifct_group_code",
        "ifct_group_name",
        "regions_count",
        "water",
        "protein",
        "ash",
        "fat",
        "fibre_total",
        "fibre_insoluble",
        "fibre_soluble",
        "carbohydrate",
        "energy_kj",
    ]

    with OUTPUT_CSV.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(ordered)

    return ordered


def print_samples(records):
    ordered = sorted(
        records.values(),
        key=lambda row: row["source_sequence"],
    )

    print()
    print("First 5 Table 1 records:")

    for row in ordered[:5]:
        print(
            row["source_food_code"],
            "| protein:", row["protein"],
            "| fat:", row["fat"],
            "| carbohydrate:", row["carbohydrate"],
            "| energy kJ:", row["energy_kj"],
        )

    targets = [
        "A001",
        "A002",
        "A003",
        "C005",
        "C006",
        "D004",
        "D005",
        "I001",
        "K001",
        "L001",
        "M001",
        "N001",
        "O001",
        "P001",
        "Q001",
        "R001",
        "S001",
    ]

    print()
    print("Selected records:")

    for code in targets:
        row = records.get(code)

        if row is None:
            print(code, "| NOT EXTRACTED")
            continue

        print(
            code,
            "| water:", row["water"],
            "| protein:", row["protein"],
            "| fat:", row["fat"],
            "| fibre:", row["fibre_total"],
            "| carbohydrate:", row["carbohydrate"],
            "| energy:", row["energy_kj"],
        )


def main():
    if not SOURCE_TEXT.exists():
        raise SystemExit(
            f"Source text not found: {SOURCE_TEXT}"
        )

    food_master = load_food_master()

    lines = SOURCE_TEXT.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines()

    start, end = find_table1_range(lines)

    print("Table 1 starts at text line:", start + 1)
    print("Table 1 ends before text line:", end + 1)

    records = extract_table1(
        food_master,
        lines,
        start,
        end,
    )

    missing, unexpected = validate(
        food_master,
        records,
    )

    ordered = write_csv(records)

    print()
    print("Written:", OUTPUT_CSV)

    print_samples(records)

    print()
    print("=== TABLE 1 EXTRACTION AUDIT ===")

    if missing:
        print(
            "STATUS: REVIEW REQUIRED"
        )
        print(
            "Missing records:",
            len(missing),
        )
    elif unexpected:
        print(
            "STATUS: REVIEW REQUIRED"
        )
        print(
            "Unexpected records:",
            len(unexpected),
        )
    else:
        print(
            "STATUS: PASS"
        )
        print(
            "All 542 food codes were extracted."
        )

    print()
    print(
        "Output records:",
        len(ordered),
    )


if __name__ == "__main__":
    main()