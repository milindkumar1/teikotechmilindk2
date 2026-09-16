import csv
from pathlib import Path

from .database import connect, initialize_schema
from .paths import DATABASE_PATH, DATA_PATH


POPULATIONS = ("b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte")
CSV_COLUMNS = (
    "project",
    "subject",
    "condition",
    "age",
    "sex",
    "treatment",
    "response",
    "sample",
    "sample_type",
    "time_from_treatment_start",
    *POPULATIONS,
)


def _parse_non_negative(value: str, field: str, row_number: int) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise ValueError(f"Row {row_number}: {field} must be an integer") from error
    if parsed < 0:
        raise ValueError(f"Row {row_number}: {field} cannot be negative")
    return parsed


def _read_rows(csv_path: Path) -> list[dict[str, object]]:
    with csv_path.open(newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        if tuple(reader.fieldnames or ()) != CSV_COLUMNS:
            raise ValueError(
                f"Unexpected CSV columns. Expected {CSV_COLUMNS}, received {reader.fieldnames}"
            )

        rows: list[dict[str, object]] = []
        seen_samples: set[str] = set()
        for row_number, raw in enumerate(reader, start=2):
            if raw["sample"] in seen_samples:
                raise ValueError(f"Row {row_number}: duplicate sample {raw['sample']}")
            seen_samples.add(raw["sample"])

            response = raw["response"] or None
            if response not in {None, "yes", "no"}:
                raise ValueError(f"Row {row_number}: invalid response {response}")
            if raw["sex"] not in {"M", "F"}:
                raise ValueError(f"Row {row_number}: invalid sex {raw['sex']}")

            rows.append(
                {
                    "project": raw["project"],
                    "subject": raw["subject"],
                    "condition": raw["condition"],
                    "age": _parse_non_negative(raw["age"], "age", row_number),
                    "sex": raw["sex"],
                    "treatment": raw["treatment"],
                    "response": response,
                    "sample": raw["sample"],
                    "sample_type": raw["sample_type"],
                    "time": _parse_non_negative(
                        raw["time_from_treatment_start"],
                        "time_from_treatment_start",
                        row_number,
                    ),
                    "counts": {
                        population: _parse_non_negative(raw[population], population, row_number)
                        for population in POPULATIONS
                    },
                }
            )
    return rows


def _subject_rows(rows: list[dict[str, object]]) -> dict[str, tuple[object, ...]]:
    subjects: dict[str, tuple[object, ...]] = {}
    for row in rows:
        values = (
            row["project"],
            row["condition"],
            row["age"],
            row["sex"],
            row["treatment"],
            row["response"],
        )
        subject = str(row["subject"])
        if subject in subjects and subjects[subject] != values:
            raise ValueError(f"Inconsistent metadata for subject {subject}")
        subjects[subject] = values
    return subjects


def load_database(
    csv_path: Path = DATA_PATH,
    database_path: Path = DATABASE_PATH,
) -> tuple[int, int]:
    if not csv_path.is_file():
        raise FileNotFoundError(f"Data file not found: {csv_path}")

    rows = _read_rows(csv_path)
    subjects = _subject_rows(rows)
    temporary_path = database_path.with_suffix(f"{database_path.suffix}.tmp")
    temporary_path.unlink(missing_ok=True)

    try:
        with connect(temporary_path) as connection:
            initialize_schema(connection)
            projects = sorted({str(row["project"]) for row in rows})
            connection.executemany(
                "INSERT INTO projects(name) VALUES (?)",
                ((project,) for project in projects),
            )
            project_ids = {
                row["name"]: row["project_id"]
                for row in connection.execute("SELECT project_id, name FROM projects")
            }
            connection.executemany(
                "INSERT INTO populations(population) VALUES (?)",
                ((population,) for population in POPULATIONS),
            )
            connection.executemany(
                """
                INSERT INTO subjects(
                    subject, project_id, condition, age, sex, treatment, response
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    (subject, project_ids[values[0]], *values[1:])
                    for subject, values in sorted(subjects.items())
                ),
            )
            connection.executemany(
                """
                INSERT INTO samples(sample, subject, sample_type, time_from_treatment_start)
                VALUES (?, ?, ?, ?)
                """,
                (
                    (row["sample"], row["subject"], row["sample_type"], row["time"])
                    for row in rows
                ),
            )
            connection.executemany(
                "INSERT INTO cell_counts(sample, population, count) VALUES (?, ?, ?)",
                (
                    (row["sample"], population, row["counts"][population])
                    for row in rows
                    for population in POPULATIONS
                ),
            )
        temporary_path.replace(database_path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise

    return len(rows), len(subjects)

