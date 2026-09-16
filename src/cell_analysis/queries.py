import sqlite3
from typing import Any


def _rows(cursor: sqlite3.Cursor) -> list[dict[str, Any]]:
    return [dict(row) for row in cursor.fetchall()]


def frequency_overview(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    return _rows(
        connection.execute(
            """
            SELECT
                frequencies.sample,
                frequencies.total_count,
                frequencies.population,
                frequencies.count,
                frequencies.percentage,
                subjects.project_id,
                projects.name AS project,
                subjects.subject,
                subjects.condition,
                subjects.treatment,
                subjects.response,
                subjects.sex,
                samples.sample_type,
                samples.time_from_treatment_start
            FROM sample_cell_frequencies AS frequencies
            JOIN samples USING (sample)
            JOIN subjects USING (subject)
            JOIN projects USING (project_id)
            ORDER BY frequencies.sample, frequencies.population
            """
        )
    )


def responder_subject_frequencies(
    connection: sqlite3.Connection,
) -> list[dict[str, Any]]:
    return _rows(
        connection.execute(
            """
            SELECT
                subjects.subject,
                subjects.response,
                frequencies.population,
                AVG(frequencies.percentage) AS percentage
            FROM sample_cell_frequencies AS frequencies
            JOIN samples USING (sample)
            JOIN subjects USING (subject)
            WHERE subjects.condition = 'melanoma'
              AND subjects.treatment = 'miraclib'
              AND samples.sample_type = 'PBMC'
              AND subjects.response IN ('yes', 'no')
            GROUP BY subjects.subject, subjects.response, frequencies.population
            ORDER BY frequencies.population, subjects.response, subjects.subject
            """
        )
    )


def analysis_results(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    return _rows(
        connection.execute(
            """
            SELECT *
            FROM analysis_results
            ORDER BY population
            """
        )
    )


def baseline_samples(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    return _rows(
        connection.execute(
            """
            SELECT
                samples.sample,
                subjects.subject,
                projects.name AS project,
                subjects.response,
                subjects.sex,
                subjects.age
            FROM samples
            JOIN subjects USING (subject)
            JOIN projects USING (project_id)
            WHERE subjects.condition = 'melanoma'
              AND subjects.treatment = 'miraclib'
              AND samples.sample_type = 'PBMC'
              AND samples.time_from_treatment_start = 0
            ORDER BY projects.name, subjects.subject
            """
        )
    )


def baseline_project_counts(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    return _rows(
        connection.execute(
            """
            SELECT projects.name AS project, COUNT(*) AS sample_count
            FROM samples
            JOIN subjects USING (subject)
            JOIN projects USING (project_id)
            WHERE subjects.condition = 'melanoma'
              AND subjects.treatment = 'miraclib'
              AND samples.sample_type = 'PBMC'
              AND samples.time_from_treatment_start = 0
            GROUP BY projects.name
            ORDER BY projects.name
            """
        )
    )


def baseline_subject_counts(
    connection: sqlite3.Connection, field: str
) -> list[dict[str, Any]]:
    if field not in {"response", "sex"}:
        raise ValueError("field must be response or sex")
    return _rows(
        connection.execute(
            f"""
            SELECT subjects.{field} AS category,
                   COUNT(DISTINCT subjects.subject) AS subject_count
            FROM samples
            JOIN subjects USING (subject)
            WHERE subjects.condition = 'melanoma'
              AND subjects.treatment = 'miraclib'
              AND samples.sample_type = 'PBMC'
              AND samples.time_from_treatment_start = 0
            GROUP BY subjects.{field}
            ORDER BY subjects.{field}
            """
        )
    )


def male_responder_baseline_b_cell_average(connection: sqlite3.Connection) -> float:
    row = connection.execute(
        """
        SELECT AVG(cell_counts.count) AS average_b_cell_count
        FROM cell_counts
        JOIN samples USING (sample)
        JOIN subjects USING (subject)
        WHERE cell_counts.population = 'b_cell'
          AND subjects.condition = 'melanoma'
          AND subjects.sex = 'M'
          AND subjects.response = 'yes'
          AND samples.time_from_treatment_start = 0
        """
    ).fetchone()
    if row is None or row["average_b_cell_count"] is None:
        raise ValueError("No samples matched the B-cell average query")
    return float(row["average_b_cell_count"])

