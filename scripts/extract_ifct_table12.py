from pathlib import Path
import csv
import re


SOURCE_TEXT = Path("data/ifct/IFCT2017_16122024.txt")
FOODS_MASTER = Path("data/ifct/foods_master.csv")
OUTPUT = Path("data/ifct/table12_fatty_acids.csv")


# Exact Table 12 columns, in source order.
FATTY_ACIDS = [
    ("f4d0_butyric", "F4D0"),
    ("f6d0_caproic", "F6D0"),
    ("f8d0_caprylic", "F8D0"),
    ("f10d0_capric", "F10D0"),
    ("f12d0_lauric", "F12D0"),
    ("f14d0_myristic", "F14D0"),
    ("f16d0_palmitic", "F16D0"),
    ("f18d0_stearic", "F18D0"),
    ("f20d0_arachidic", "F20D0"),
    ("f22d0_behenic", "F22D0"),
    ("f24d0_lignoceric", "F24D0"),
]


EXPECTED_CODES = [f"T{i:03d}" for i in range(1, 15)]


CODE_RE = re.compile(
    r"^\s*(T\d{3})\s+(.+?)\s+(\d+)(.*)$"
)

VALUE_RE = re.compile(
    r"[-+]?\d+(?:\.\d+)?(?:±[-+]?\d+(?:\.\d+)?)?"
)


def clean_value(value):
    """
    Convert the reported value to its central numeric value.

    Examples:
        2.76±0.37 -> 2.76
        12.94     -> 12.94
        blank     -> None
    """
    value = value.strip()

    if not value:
        return None

    match = re.match(
        r"^([-+]?\d+(?:\.\d+)?)(?:±[-+]?\d+(?:\.\d+)?)?$",
        value,
    )

    if not match:
        raise ValueError(f"Unexpected numeric value: {value!r}")

    return float(match.group(1))


def find_table12(lines):
    start = None
    end = None

    for i, line in enumerate(lines):
        if "Table 12. FATTY ACID PROFILE OF EDIBLE OILS AND FATS" in line:
            start = i
            break

    if start is None:
        raise RuntimeError("Table 12 start not found.")

    for i in range(start + 1, len(lines)):
        if (
            "Table 12. Fatty acid profile of edible oils and fats"
            in lines[i]
        ):
            end = i
            break

    if end is None:
        raise RuntimeError("Table 12 end not found.")

    return start, end


def find_header_positions(lines, start):
    """
    Find the exact character positions of F4D0 ... F24D0
    from the Table 12 header line.
    """

    header_index = None

    for i in range(start, min(start + 30, len(lines))):
        line = lines[i]

        if (
            "F4D0" in line
            and "F6D0" in line
            and "F24D0" in line
        ):
            header_index = i
            break

    if header_index is None:
        raise RuntimeError("Table 12 fatty-acid header not found.")

    header = lines[header_index]

    positions = []

    for _, code in FATTY_ACIDS:
        pos = header.find(code)

        if pos == -1:
            raise RuntimeError(
                f"Could not find {code} in Table 12 header."
            )

        positions.append(pos)

    return header_index, positions


def extract_fixed_columns(line, positions):
    """
    Map numeric values to the Table 12 columns using the
    actual horizontal position of each value.

    The PDF-to-text conversion places values slightly to the
    left of their header positions, so direct slicing from
    header positions is not reliable.

    A value is assigned to the nearest Table 12 column position.
    Blank columns remain None.
    """

    values = [None] * len(positions)

    # Find all actual numeric values on the data row.
    matches = list(VALUE_RE.finditer(line))

    for match in matches:
        start_pos = match.start()
        token = match.group(0)

        # Ignore the food-code digits and region count.
        if start_pos < positions[0]:
            continue

        # Find nearest Table 12 column.
        column_index = min(
            range(len(positions)),
            key=lambda i: abs(positions[i] - start_pos)
        )

        # Protect against accidentally assigning a value
        # that is too far away from a column.
        distance = abs(
            positions[column_index] - start_pos
        )

        if distance > 8:
            continue

        value = clean_value(token)

        if values[column_index] is not None:
            raise ValueError(
                f"Multiple values mapped to the same column "
                f"at position {start_pos}: {token}"
            )

        values[column_index] = value

    return values


def main():
    lines = SOURCE_TEXT.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines()

    start, end = find_table12(lines)

    print(f"Table 12 starts at text line: {start + 1}")
    print(f"Table 12 ends before text line: {end + 1}")

    header_index, positions = find_header_positions(
        lines,
        start,
    )

    print(f"Table 12 header line: {header_index + 1}")

    print()
    print("Column positions:")

    for (_, code), position in zip(
        FATTY_ACIDS,
        positions,
    ):
        print(f"{code}: character {position}")

    with FOODS_MASTER.open(
        encoding="utf-8",
        newline="",
    ) as f:
        master = {
            row["source_food_code"]: row
            for row in csv.DictReader(f)
        }

    records = {}

    for line in lines[start:end]:
        match = CODE_RE.match(line)

        if not match:
            continue

        code = match.group(1)

        if code not in EXPECTED_CODES:
            continue

        name = match.group(2).strip()
        regions = int(match.group(3))

        values = extract_fixed_columns(
            line,
            positions,
        )

        records[code] = {
            "source_food_code": code,
            "source_food_name": name,
            "regions_count": regions,
            "values": values,
        }

    print()
    print("=== TABLE 12 PARSED RECORDS ===")

    for code in EXPECTED_CODES:
        record = records.get(code)

        if record is None:
            print(f"{code} | NOT FOUND")
            continue

        print()
        print(
            f"{code} | {record['source_food_name']} "
            f"| regions: {record['regions_count']}"
        )

        for (name, column_code), value in zip(
            FATTY_ACIDS,
            record["values"],
        ):
            display = "BLANK / BELOW DETECTABLE LIMIT"

            if value is not None:
                display = str(value)

            print(
                f"  {column_code:<5} "
                f"{name:<22} {display}"
            )

    missing = [
        code
        for code in EXPECTED_CODES
        if code not in records
    ]

    unexpected = [
        code
        for code in records
        if code not in EXPECTED_CODES
    ]

    print()
    print("=== TABLE 12 AUDIT ===")
    print("Expected records:", len(EXPECTED_CODES))
    print("Extracted records:", len(records))
    print("Missing:", missing)
    print("Unexpected:", unexpected)

    if len(records) != 14:
        print()
        print("TABLE 12 EXTRACTION: REQUIRES REVIEW")
        return

    # Validate the source names against foods_master.csv.
    name_mismatches = []

    for code in EXPECTED_CODES:
        source_name = master[code]["source_food_name"]
        extracted_name = records[code]["source_food_name"]

        if source_name != extracted_name:
            name_mismatches.append(
                (code, source_name, extracted_name)
            )

    print("Name mismatches:", name_mismatches)

    if name_mismatches:
        print()
        print("TABLE 12 EXTRACTION: REQUIRES REVIEW")
        return

    fieldnames = [
        "source_food_code",
        "source_food_name",
        "regions_count",
    ] + [name for name, _ in FATTY_ACIDS]

    rows = []

    for code in EXPECTED_CODES:
        record = records[code]

        row = {
            "source_food_code": code,
            "source_food_name": record["source_food_name"],
            "regions_count": record["regions_count"],
        }

        for (name, _), value in zip(
            FATTY_ACIDS,
            record["values"],
        ):
            row[name] = (
                ""
                if value is None
                else value
            )

        rows.append(row)

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(rows)

    print()
    print(f"Written: {OUTPUT}")
    print()
    print("TABLE 12 EXTRACTION: PASS")
    print("14/14 records extracted.")
    print("Blank cells preserved as below-detectable-limit.")


if __name__ == "__main__":
    main()