from pathlib import Path
import csv
import re


SOURCE_TEXT = Path("data/ifct/IFCT2017_16122024.txt")
FOODS_MASTER = Path("data/ifct/foods_master.csv")
OUTPUT = Path("data/ifct/table12_saturated_fatty_acids.csv")


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


EXPECTED_CODES = [
    f"T{i:03d}"
    for i in range(1, 15)
]


CODE_RE = re.compile(
    r"^\s*(T\d{3})\s+(.+?)\s+(\d+)(.*)$"
)


VALUE_RE = re.compile(
    r"[-+]?\d+(?:\.\d+)?(?:±[-+]?\d+(?:\.\d+)?)?"
)


def clean_value(value):
    value = value.strip()

    if not value:
        return None

    match = re.match(
        r"^([-+]?\d+(?:\.\d+)?)(?:±[-+]?\d+(?:\.\d+)?)?$",
        value,
    )

    if not match:
        raise ValueError(
            f"Unexpected numeric value: {value!r}"
        )

    return float(match.group(1))


def find_table12_saturated_section(lines):

    header_index = None

    required_codes = [
        code
        for _, code in FATTY_ACIDS
    ]

    for i, line in enumerate(lines):

        if all(
            code in line
            for code in required_codes
        ):
            header_index = i
            break

    if header_index is None:
        raise RuntimeError(
            "Table 12 saturated-fatty-acid header not found."
        )

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
            "T001 not found after Table 12 saturated header."
        )

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
            "T014 not found in Table 12 saturated section."
        )

    return start, end, header_index


def find_header_positions(lines, header_index):

    header = lines[header_index]

    positions = []

    for _, code in FATTY_ACIDS:

        pos = header.find(code)

        if pos == -1:
            raise RuntimeError(
                f"Could not find {code} in Table 12 header."
            )

        positions.append(pos)

    return positions


def extract_fixed_columns(line, positions):

    values = []

    for i, start_pos in enumerate(positions):

        if i + 1 < len(positions):
            end_pos = positions[i + 1]
        else:
            end_pos = len(line)

        raw = line[start_pos:end_pos].strip()

        match = VALUE_RE.search(raw)

        if match:
            values.append(
                clean_value(match.group(0))
            )
        else:
            values.append(None)

    return values


def main():

    lines = SOURCE_TEXT.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines()

    start, end, header_index = (
        find_table12_saturated_section(lines)
    )

    print(
        f"Table 12 saturated section starts at text line: "
        f"{start + 1}"
    )

    print(
        f"Table 12 saturated section ends before text line: "
        f"{end + 1}"
    )

    print(
        f"Table 12 saturated header line: "
        f"{header_index + 1}"
    )

    positions = find_header_positions(
        lines,
        header_index,
    )

    print()
    print("=== HEADER POSITIONS ===")

    for (_, code), position in zip(
        FATTY_ACIDS,
        positions,
    ):
        print(
            f"{code:<6} character {position}"
        )

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
    print("=== TABLE 12 SATURATED PARSED RECORDS ===")

    for code in EXPECTED_CODES:

        record = records.get(code)

        if record is None:
            print(
                f"{code} | NOT FOUND"
            )
            continue

        print()
        print(
            f"{code} | "
            f"{record['source_food_name']} | "
            f"regions: {record['regions_count']}"
        )

        for (
            name,
            column_code,
        ), value in zip(
            FATTY_ACIDS,
            record["values"],
        ):

            display = (
                "BLANK / BELOW DETECTABLE LIMIT"
                if value is None
                else str(value)
            )

            print(
                f"  {column_code:<6} "
                f"{name:<28} "
                f"{display}"
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
    print("=== TABLE 12 SATURATED AUDIT ===")

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

    if len(records) != 14:

        print()
        print(
            "TABLE 12 SATURATED EXTRACTION: "
            "REQUIRES REVIEW"
        )

        return

    name_mismatches = []

    for code in EXPECTED_CODES:

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
            "TABLE 12 SATURATED EXTRACTION: "
            "REQUIRES REVIEW"
        )

        return

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
            name,
            _
        ), value in zip(
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
    print(
        f"Written: {OUTPUT}"
    )

    print()
    print(
        "TABLE 12 SATURATED EXTRACTION: PASS"
    )

    print(
        "14/14 records extracted."
    )

    print(
        "Blank cells preserved as "
        "below-detectable-limit."
    )


if __name__ == "__main__":
    main()