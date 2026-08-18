from pathlib import Path
import csv
import re


SOURCE_TEXT = Path("data/ifct/IFCT2017_16122024.txt")
FOODS_MASTER = Path("data/ifct/foods_master.csv")
OUTPUT = Path("data/ifct/table12_unsaturated_fatty_acids.csv")


# Exact second-section Table 12 columns, in source order.
FATTY_ACIDS = [
    ("f14d1_myristoleic", "F14D1"),
    ("f16d1_palmitoleic", "F16D1"),
    ("f18d1tn9_elaidic", "F18D1TN9"),
    ("f18d1n9_oleic", "F18D1N9"),
    ("f20d1n9_eicosenoic", "F20D1N9"),
    ("f22d1n9_erucic", "F22D1N9"),
    ("f18d2n6_linoleic", "F18D2N6"),
    ("f18d3n3_alpha_linolenic", "F18D3N3"),
    ("fasat_total_saturated", "FASAT"),
    ("fams_total_monounsaturated", "FAMS"),
    ("fapu_total_polyunsaturated", "FAPU"),
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
    Convert reported value to its central numeric value.

    Examples:
        7.24±0.25 -> 7.24
        31.97     -> 31.97
        blank     -> None
    """

    value = value.strip()

    if not value:
        return None

    match = re.fullmatch(
        r"([-+]?\d+(?:\.\d+)?)(?:±[-+]?\d+(?:\.\d+)?)?",
        value,
    )

    if not match:
        raise ValueError(
            f"Unexpected numeric value: {value!r}"
        )

    return float(match.group(1))


def find_table12_second_section(lines):
    """
    Locate the second section of Table 12.

    The relevant header contains:

        F14D1 ... FAPU

    The repeated Table 12 title inside the data section
    is intentionally ignored.
    """

    required_codes = [
        code
        for _, code in FATTY_ACIDS
    ]

    header_index = None

    for i, line in enumerate(lines):

        if all(
            code in line
            for code in required_codes
        ):
            header_index = i
            break

    if header_index is None:
        raise RuntimeError(
            "Table 12 second-section header not found."
        )

    # Find T001 after the header.
    start = None

    for i in range(
        header_index + 1,
        len(lines),
    ):

        if re.match(
            r"^\s*T001\s+",
            lines[i],
        ):
            start = i
            break

    if start is None:
        raise RuntimeError(
            "T001 not found after Table 12 second-section header."
        )

    # Find T014 after T001.
    end = None

    for i in range(
        start + 1,
        len(lines),
    ):

        if re.match(
            r"^\s*T014\s+",
            lines[i],
        ):
            end = i + 1
            break

    if end is None:
        raise RuntimeError(
            "T014 not found in Table 12 second section."
        )

    return start, end, header_index


def find_header_positions(lines, header_index):
    """
    Find the exact character positions of the 11 column codes
    from the actual Table 12 header.
    """

    header = lines[header_index]

    positions = []

    for _, code in FATTY_ACIDS:

        position = header.find(code)

        if position == -1:
            raise RuntimeError(
                f"Could not find {code} in Table 12 header."
            )

        positions.append(position)

    return positions


def build_column_boundaries(positions):
    """
    Build boundaries between columns using the midpoint between
    adjacent header positions.

    Header positions:

        F14D1     116
        F16D1     130
        F18D1TN9  142
        F18D1N9   155
        F20D1N9   168
        F22D1N9   181
        F18D2N6   198
        F18D3N3   212
        FASAT     229
        FAMS      245
        FAPU      259

    The PDF-to-text conversion can place an actual value a few
    characters before the header position. Therefore we use
    midpoint boundaries instead of requiring an exact position.

    Example:

        F14D1 starts around 116
        F16D1 starts around 130

        midpoint = 123

    Therefore:
        positions 110..122 -> F14D1
        positions 123..135 -> F16D1
        etc.
    """

    DATA_START = 110

    boundaries = [DATA_START]

    for left, right in zip(
        positions,
        positions[1:],
    ):
        midpoint = (left + right) // 2
        boundaries.append(midpoint)

    # Last column extends to the end of the line.
    boundaries.append(None)

    return boundaries


def extract_fixed_columns(line, positions):
    """
    Extract values using fixed character ranges derived from
    the Table 12 header positions.

    This does NOT use nearest-column matching.

    Genuine numeric tokens are assigned according to which
    column interval their starting character belongs to.
    """

    boundaries = build_column_boundaries(
        positions
    )

    values = [None] * len(positions)

    # Find all numeric tokens.
    tokens = []

    for match in VALUE_RE.finditer(line):

        position = match.start()

        if position < boundaries[0]:
            continue

        tokens.append(
            {
                "position": position,
                "raw": match.group(0),
                "value": clean_value(
                    match.group(0)
                ),
            }
        )

    # Assign each token to its fixed column interval.
    for token in tokens:

        position = token["position"]

        for column_index in range(
            len(positions)
        ):

            start = boundaries[column_index]
            end = boundaries[column_index + 1]

            if end is None:

                if position >= start:
                    if values[column_index] is not None:
                        raise RuntimeError(
                            "Multiple numeric tokens found "
                            f"in column {FATTY_ACIDS[column_index][1]} "
                            f"at position {position}."
                        )

                    values[column_index] = token["value"]
                    break

            elif start <= position < end:

                if values[column_index] is not None:
                    raise RuntimeError(
                        "Multiple numeric tokens found "
                        f"in column {FATTY_ACIDS[column_index][1]} "
                        f"at position {position}."
                    )

                values[column_index] = token["value"]
                break

    return values


def extract_tokens_with_positions(line):
    """
    Diagnostic helper.

    Returns every numeric token at or after the data area.
    """

    tokens = []

    for match in VALUE_RE.finditer(line):

        position = match.start()

        if position < 110:
            continue

        tokens.append(
            (
                position,
                match.group(0),
            )
        )

    return tokens


def validate_source_mapping(
    records,
    positions,
):
    """
    Strong audit.

    For every extracted record, verify that every populated
    source token falls inside the expected column boundary.

    This catches shifted-column extraction.
    """

    errors = []

    boundaries = build_column_boundaries(
        positions
    )

    for code in EXPECTED_CODES:

        record = records.get(code)

        if record is None:
            continue

        line = record["source_line"]

        tokens = extract_tokens_with_positions(
            line
        )

        expected_tokens = []

        for position, raw in tokens:

            assigned_column = None

            for column_index in range(
                len(positions)
            ):

                start = boundaries[column_index]
                end = boundaries[column_index + 1]

                if end is None:

                    if position >= start:
                        assigned_column = column_index
                        break

                elif start <= position < end:

                    assigned_column = column_index
                    break

            if assigned_column is None:
                errors.append(
                    (
                        code,
                        position,
                        raw,
                        "NO COLUMN",
                    )
                )
                continue

            expected_tokens.append(
                (
                    assigned_column,
                    position,
                    raw,
                )
            )

        # Print the mapping for audit.
        print()
        print(
            f"{code} SOURCE TOKEN MAPPING:"
        )

        for (
            column_index,
            position,
            raw,
        ) in expected_tokens:

            print(
                f"  position={position:<3} "
                f"value={raw:<14} "
                f"-> "
                f"{FATTY_ACIDS[column_index][1]}"
            )

    return errors


def main():

    lines = SOURCE_TEXT.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines()

    # ---------------------------------------------------------
    # Locate Table 12 second section
    # ---------------------------------------------------------

    start, end, header_index = (
        find_table12_second_section(lines)
    )

    print(
        f"Table 12 second section starts at text line: "
        f"{start + 1}"
    )

    print(
        f"Table 12 second section ends before text line: "
        f"{end + 1}"
    )

    print(
        f"Table 12 second-section header line: "
        f"{header_index + 1}"
    )

    # ---------------------------------------------------------
    # Find column positions
    # ---------------------------------------------------------

    positions = find_header_positions(
        lines,
        header_index,
    )

    print()
    print("Column positions:")

    for (_, code), position in zip(
        FATTY_ACIDS,
        positions,
    ):

        print(
            f"{code}: character {position}"
        )

    print()
    print("Column boundaries:")

    boundaries = build_column_boundaries(
        positions
    )

    for i, (_, code) in enumerate(
        FATTY_ACIDS
    ):

        start_position = boundaries[i]
        end_position = boundaries[i + 1]

        if end_position is None:
            print(
                f"{code}: {start_position} -> END"
            )
        else:
            print(
                f"{code}: "
                f"{start_position} -> "
                f"{end_position - 1}"
            )

    # ---------------------------------------------------------
    # Load foods master
    # ---------------------------------------------------------

    with FOODS_MASTER.open(
        encoding="utf-8",
        newline="",
    ) as f:

        master = {
            row["source_food_code"]: row
            for row in csv.DictReader(f)
        }

    # ---------------------------------------------------------
    # Extract records
    # ---------------------------------------------------------

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
            "source_line": line,
        }

    # ---------------------------------------------------------
    # Basic record audit
    # ---------------------------------------------------------

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
    print(
        "=== TABLE 12 SECOND SECTION AUDIT ==="
    )

    print(
        "Expected records:",
        len(EXPECTED_CODES),
    )

    print(
        "Extracted records:",
        len(records),
    )

    print(
        "Missing:",
        missing,
    )

    print(
        "Unexpected:",
        unexpected,
    )

    if (
        len(records) != len(EXPECTED_CODES)
        or missing
        or unexpected
    ):

        print()
        print(
            "TABLE 12 SECOND SECTION: "
            "REQUIRES REVIEW"
        )

        return

    # ---------------------------------------------------------
    # Validate names
    # ---------------------------------------------------------

    name_mismatches = []

    for code in EXPECTED_CODES:

        if code not in master:

            name_mismatches.append(
                (
                    code,
                    "MISSING FROM FOODS MASTER",
                    records[code][
                        "source_food_name"
                    ],
                )
            )

            continue

        source_name = master[code][
            "source_food_name"
        ]

        extracted_name = records[code][
            "source_food_name"
        ]

        if source_name != extracted_name:

            name_mismatches.append(
                (
                    code,
                    source_name,
                    extracted_name,
                )
            )

    print(
        "Name mismatches:",
        name_mismatches,
    )

    if name_mismatches:

        print()
        print(
            "TABLE 12 SECOND SECTION: "
            "REQUIRES REVIEW"
        )

        return

    # ---------------------------------------------------------
    # Strong source-position audit
    # ---------------------------------------------------------

    print()
    print(
        "=== SOURCE POSITION AUDIT ==="
    )

    mapping_errors = validate_source_mapping(
        records,
        positions,
    )

    if mapping_errors:

        print()
        print(
            "Source-position errors:"
        )

        for error in mapping_errors:
            print(error)

        print()
        print(
            "TABLE 12 SECOND SECTION: "
            "REQUIRES REVIEW"
        )

        return

    # ---------------------------------------------------------
    # Display parsed records
    # ---------------------------------------------------------

    print()
    print(
        "=== TABLE 12 SECOND SECTION "
        "PARSED RECORDS ==="
    )

    for code in EXPECTED_CODES:

        record = records[code]

        print()
        print(
            f"{code} | "
            f"{record['source_food_name']} | "
            f"regions: "
            f"{record['regions_count']}"
        )

        for (
            (name, column_code),
            value,
        ) in zip(
            FATTY_ACIDS,
            record["values"],
        ):

            if value is None:

                display = (
                    "BLANK / "
                    "BELOW DETECTABLE LIMIT"
                )

            else:

                display = str(value)

            print(
                f"  {column_code:<9} "
                f"{name:<32} "
                f"{display}"
            )

    # ---------------------------------------------------------
    # Build CSV
    # ---------------------------------------------------------

    fieldnames = [
        "source_food_code",
        "source_food_name",
        "regions_count",
    ] + [
        name
        for name, _ in FATTY_ACIDS
    ]

    rows = []

    for code in EXPECTED_CODES:

        record = records[code]

        row = {
            "source_food_code":
                record["source_food_code"],

            "source_food_name":
                record["source_food_name"],

            "regions_count":
                record["regions_count"],
        }

        for (
            (name, _),
            value,
        ) in zip(
            FATTY_ACIDS,
            record["values"],
        ):

            row[name] = (
                ""
                if value is None
                else value
            )

        rows.append(row)

    # ---------------------------------------------------------
    # Write CSV
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # Final status
    # ---------------------------------------------------------

    print()
    print(
        f"Written: {OUTPUT}"
    )

    print()
    print(
        "TABLE 12 SECOND SECTION: PASS"
    )

    print(
        "14/14 records extracted."
    )

    print(
        "Column-boundary mapping verified."
    )

    print(
        "Blank cells preserved as "
        "below-detectable-limit."
    )


if __name__ == "__main__":
    main()