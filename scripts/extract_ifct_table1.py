from pathlib import Path
import csv
import re


SOURCE_TEXT = Path("data/ifct/IFCT2017_16122024.txt")
FOODS_MASTER = Path("data/ifct/foods_master.csv")
OUTPUT_CSV = Path("data/ifct/table1_proximate.csv")


TABLE1_START = 1991
TABLE1_END = 3764


FOOD_CODE_RE = re.compile(
    r"^\s*([A-Z]\d{3})\s+(.*)$"
)


NUMBER_RE = re.compile(
    r"[-+]?\d+(?:\.\d+)?(?:±[-+]?\d+(?:\.\d+)?)?"
)


def clean_text(value):
    return re.sub(r"\s+", " ", value).strip()


def to_float(value):
    """
    Convert:

        14.59
        14.59±0.40

    to:

        14.59
    """

    if value is None:
        return None

    value = value.strip()

    if "±" in value:
        value = value.split("±", 1)[0]

    try:
        return float(value)
    except ValueError:
        return None


def parse_numeric_values(line):
    """
    Extract all numeric tokens from a Table 1 data line.
    """

    return NUMBER_RE.findall(line)


def parse_table1_values(line):
    """
    Parse a Table 1 nutritional row.

    Supported layouts:

    Standard:
        regions
        water
        protein
        ash
        fat
        total fibre
        insoluble fibre
        soluble fibre
        carbohydrate
        energy

    = 9 values after regions.

    Reduced:
        regions
        water
        protein
        ash
        fat
        carbohydrate
        energy

    = 6 values after regions.

    Meat/fish style:
        regions
        water
        protein
        ash
        fat
        energy

    = 5 values after regions.
    """

    values = parse_numeric_values(line)

    if not values:
        return None

    try:
        regions = int(values[0])
    except ValueError:
        return None

    if not 1 <= regions <= 20:
        return None

    values = values[1:]

    # ------------------------------------------------------------
    # STANDARD TABLE 1
    # ------------------------------------------------------------

    if len(values) >= 9:
        return {
            "regions_count": regions,
            "water": to_float(values[0]),
            "protein": to_float(values[1]),
            "ash": to_float(values[2]),
            "fat": to_float(values[3]),
            "fibre": to_float(values[4]),
            "fibre_insoluble": to_float(values[5]),
            "fibre_soluble": to_float(values[6]),
            "carbohydrate": to_float(values[7]),
            "energy_kj": to_float(values[8]),
        }

    # ------------------------------------------------------------
    # REDUCED TABLE
    # ------------------------------------------------------------

    if len(values) == 6:
        return {
            "regions_count": regions,
            "water": to_float(values[0]),
            "protein": to_float(values[1]),
            "ash": to_float(values[2]),
            "fat": to_float(values[3]),
            "fibre": None,
            "fibre_insoluble": None,
            "fibre_soluble": None,
            "carbohydrate": to_float(values[4]),
            "energy_kj": to_float(values[5]),
        }

    # ------------------------------------------------------------
    # MEAT / FISH STYLE
    # ------------------------------------------------------------

    if len(values) == 5:
        return {
            "regions_count": regions,
            "water": to_float(values[0]),
            "protein": to_float(values[1]),
            "ash": to_float(values[2]),
            "fat": to_float(values[3]),
            "fibre": None,
            "fibre_insoluble": None,
            "fibre_soluble": None,
            "carbohydrate": None,
            "energy_kj": to_float(values[4]),
        }

    return None


def looks_like_numeric_row(line):
    """
    Check whether a line contains a plausible Table 1 numeric
    sequence.

    We don't require the line to BEGIN with the region count,
    because normal rows contain:

        FOOD CODE + FOOD NAME + numeric values
    """

    values = parse_numeric_values(line)

    if len(values) < 6:
        return False

    for value in values:
        try:
            n = int(value)
        except ValueError:
            continue

        if 1 <= n <= 20:
            return True

    return False


def find_numeric_part(line):
    """
    Find the beginning of the nutritional numeric section.

    Example:

        A003  Bajra (...)  6  8.97±0.60  10.96±0.26 ...

    returns:

        6  8.97±0.60  10.96±0.26 ...
    """

    values = parse_numeric_values(line)

    if not values:
        return None

    match = re.search(
        r"(?<![\d.])"
        r"(\d{1,2})"
        r"(?=\s+[-+]?\d+(?:\.\d+)?(?:±[-+]?\d+(?:\.\d+)?)?)",
        line,
    )

    if not match:
        return None

    return line[match.start():]


def make_record(code, parsed, master):
    """
    Build a normalized Table 1 record.
    """

    return {
        "source_food_code": code,
        "source_food_name": master[code]["source_food_name"],
        **parsed,
    }


def is_ignorable_table_header(line):
    """
    Detect repeated Table 1 header lines.
    """

    cleaned = clean_text(line)

    if not cleaned:
        return True

    if "Table 1. Proximate Principles" in line:
        return True

    if "Food Code" in line:
        return True

    if "Food Name" in line:
        return True

    if "Moisture" in line:
        return True

    if "WATER" in line:
        return True

    if "PROTCNT" in line:
        return True

    if "ENERC" in line:
        return True

    if "No. of" in line:
        return True

    return False


def find_preceding_numeric_row(section, code_index):
    """
    Special handling for records where the numeric row appears
    BEFORE the food-code/name line.

    This happens in IFCT Table 1 for records such as:

        O004 ...
              4  68.40±1.00 ...

        Table 1. Proximate Principles...
        O005 Goat, tongue

    The numeric row belongs to O005.

    Same structure occurs for O049.

    We deliberately keep this backward search limited to the
    known affected records so that unrelated table structures
    are not accidentally reassigned.
    """

    for j in range(
        code_index - 1,
        max(-1, code_index - 15),
        -1,
    ):
        previous_line = section[j]

        if not previous_line.strip():
            continue

        # If another food code is encountered before a numeric row,
        # stop searching.
        previous_code = FOOD_CODE_RE.match(previous_line)

        if previous_code:
            break

        if is_ignorable_table_header(previous_line):
            continue

        if not looks_like_numeric_row(previous_line):
            continue

        parsed = parse_table1_values(previous_line)

        if parsed:
            return parsed

    return None


def extract_table1(lines, master):
    records = {}

    # Convert text line numbers to Python indexes.
    section_start = TABLE1_START - 1
    section_end = TABLE1_END - 1

    section = lines[section_start:section_end]

    i = 0

    while i < len(section):

        line = section[i]

        match = FOOD_CODE_RE.match(line)

        if not match:
            i += 1
            continue

        code = match.group(1)
        remainder = match.group(2)

        # Only process codes from foods_master.csv.
        if code not in master:
            i += 1
            continue

        # --------------------------------------------------------
        # CASE 1
        #
        # Normal row:
        #
        # A003  Bajra (...)  6  8.97±0.60 ...
        # --------------------------------------------------------

        numeric_part = find_numeric_part(remainder)

        if numeric_part:

            parsed = parse_table1_values(numeric_part)

            if parsed:
                records[code] = make_record(
                    code,
                    parsed,
                    master,
                )

                i += 1
                continue

        # --------------------------------------------------------
        # CASE 2
        #
        # Wrapped row:
        #
        # O005  Goat, tongue
        #
        #              4  68.40±1.00 ...
        #
        # Search forward for the numeric row.
        # --------------------------------------------------------

        found = False

        for j in range(
            i + 1,
            min(i + 12, len(section)),
        ):

            next_line = section[j]

            if not next_line.strip():
                continue

            # Another food code means this record did not
            # have a continuation row.
            next_code = FOOD_CODE_RE.match(next_line)

            if next_code:
                break

            if is_ignorable_table_header(next_line):
                continue

            if not looks_like_numeric_row(next_line):
                continue

            parsed = parse_table1_values(next_line)

            if parsed:

                records[code] = make_record(
                    code,
                    parsed,
                    master,
                )

                found = True
                break

        if found:
            i += 1
            continue

        # --------------------------------------------------------
        # CASE 3
        #
        # SPECIAL PRECEDING-DATA ROW
        #
        # The IFCT PDF has two records where the numeric row occurs
        # immediately BEFORE the repeated Table 1 header and the
        # food code/name appears AFTER that header:
        #
        # O005 | Goat, tongue
        # O049 | Pork, chops
        #
        # Therefore search backward only for these known records.
        # --------------------------------------------------------

        if code in {"O005", "O049"}:

            parsed = find_preceding_numeric_row(
                section,
                i,
            )

            if parsed:
                records[code] = make_record(
                    code,
                    parsed,
                    master,
                )

        i += 1

    return records


def validate(records, master):

    master_codes = set(master.keys())
    table_codes = set(records.keys())

    missing = sorted(
        master_codes - table_codes,
        key=lambda code: (
            code[0],
            int(code[1:]),
        ),
    )

    unexpected = sorted(
        table_codes - master_codes,
        key=lambda code: (
            code[0],
            int(code[1:]),
        ),
    )

    return missing, unexpected


def write_csv(records):

    OUTPUT_CSV.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "source_food_code",
        "source_food_name",
        "regions_count",
        "water",
        "protein",
        "ash",
        "fat",
        "fibre",
        "fibre_insoluble",
        "fibre_soluble",
        "carbohydrate",
        "energy_kj",
    ]

    ordered = sorted(
        records.values(),
        key=lambda row: (
            row["source_food_code"][0],
            int(row["source_food_code"][1:]),
        ),
    )

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


def print_selected(records):

    targets = [
        "A001",
        "A002",
        "A003",
        "C005",
        "C006",
        "D004",
        "D005",
        "E033",
        "I001",
        "K001",
        "L001",
        "M001",
        "N001",
        "O001",
        "O004",
        "O005",
        "O048",
        "O049",
        "P001",
        "Q001",
        "R001",
        "S001",
        "T001",
    ]

    print("\nSelected records:")

    for code in targets:

        record = records.get(code)

        if record is None:

            print(
                f"{code} | NOT FOUND"
            )

            continue

        print(
            f"{code} | "
            f"water: {record['water']} | "
            f"protein: {record['protein']} | "
            f"ash: {record['ash']} | "
            f"fat: {record['fat']} | "
            f"fibre: {record['fibre']} | "
            f"carbohydrate: {record['carbohydrate']} | "
            f"energy: {record['energy_kj']}"
        )


def main():

    if not SOURCE_TEXT.exists():
        raise SystemExit(
            f"Source text not found: {SOURCE_TEXT}"
        )

    if not FOODS_MASTER.exists():
        raise SystemExit(
            f"Food master not found: {FOODS_MASTER}"
        )

    lines = SOURCE_TEXT.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines()

    with FOODS_MASTER.open(
        encoding="utf-8",
        newline="",
    ) as handle:

        master_rows = list(
            csv.DictReader(handle)
        )

    master = {
        row["source_food_code"]: row
        for row in master_rows
    }

    print(
        f"Table 1 starts at text line: {TABLE1_START}"
    )

    print(
        f"Table 1 ends before text line: {TABLE1_END}"
    )

    print(
        f"\nFood master count: {len(master)}"
    )

    records = extract_table1(
        lines,
        master,
    )

    missing, unexpected = validate(
        records,
        master,
    )

    print(
        f"Table 1 records extracted: {len(records)}"
    )

    print(
        "\nMissing from Table 1:",
        missing,
    )

    print(
        "Unexpected Table 1 codes:",
        unexpected,
    )

    ordered = write_csv(records)

    print(
        f"\nWritten: {OUTPUT_CSV}"
    )

    print_selected(records)

    print("\nSpecial wrapped-record checks:")

    for code in ["O005", "O049"]:

        record = records.get(code)

        if record:

            print(
                f"{code} | "
                f"{record['source_food_name']} | "
                f"regions: {record['regions_count']}"
            )

        else:

            print(
                f"{code} | NOT FOUND"
            )

    print("\n=== TABLE 1 EXTRACTION STATUS ===")

    if unexpected:

        print(
            "FAIL: Unexpected food codes found."
        )

    elif (
        "O005" not in missing
        and "O049" not in missing
    ):

        print(
            "BASE TABLE 1 EXTRACTION: PASS"
        )

        print(
            "O005/O049 wrapped records: PASS"
        )

        print(
            "T001-T014 remain reserved for separate handling."
        )

    else:

        print(
            "TABLE 1 EXTRACTION: REQUIRES REVIEW"
        )


if __name__ == "__main__":
    main()