from pathlib import Path

import pytest

from src.cell_analysis.database import connect
from src.cell_analysis.loader import load_database
from src.cell_analysis.paths import DATA_PATH
from src.cell_analysis.queries import (
    baseline_project_counts,
    baseline_samples,
    baseline_subject_counts,
    male_responder_baseline_b_cell_average,
)
from src.cell_analysis.statistics import store_statistics


@pytest.fixture(scope="module")
def database_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("database") / "test.db"
    load_database(DATA_PATH, path)
    return path


def test_schema_counts(database_path: Path) -> None:
    with connect(database_path) as connection:
        expected = {
            "projects": 3,
            "subjects": 3_500,
            "samples": 10_500,
            "populations": 5,
            "cell_counts": 52_500,
            "sample_cell_frequencies": 52_500,
        }
        for table, count in expected.items():
            actual = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            assert actual == count


def test_frequency_view(database_path: Path) -> None:
    with connect(database_path) as connection:
        invalid_totals = connection.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT sample
                FROM sample_cell_frequencies
                GROUP BY sample
                HAVING ABS(SUM(percentage) - 100.0) > 0.000001
            )
            """
        ).fetchone()[0]
        row = connection.execute(
            """
            SELECT sample, total_count, population, count, percentage
            FROM sample_cell_frequencies
            LIMIT 1
            """
        ).fetchone()
    assert invalid_totals == 0
    assert set(row.keys()) == {
        "sample",
        "total_count",
        "population",
        "count",
        "percentage",
    }


def test_baseline_subset(database_path: Path) -> None:
    with connect(database_path) as connection:
        assert len(baseline_samples(connection)) == 656
        assert baseline_project_counts(connection) == [
            {"project": "prj1", "sample_count": 384},
            {"project": "prj3", "sample_count": 272},
        ]
        assert baseline_subject_counts(connection, "response") == [
            {"category": "no", "subject_count": 325},
            {"category": "yes", "subject_count": 331},
        ]
        assert baseline_subject_counts(connection, "sex") == [
            {"category": "F", "subject_count": 312},
            {"category": "M", "subject_count": 344},
        ]


def test_b_cell_average(database_path: Path) -> None:
    with connect(database_path) as connection:
        average = male_responder_baseline_b_cell_average(connection)
    assert average == pytest.approx(10_206.15, abs=0.005)


def test_statistical_analysis(database_path: Path) -> None:
    with connect(database_path) as connection:
        results = store_statistics(connection)
        stored_count = connection.execute(
            "SELECT COUNT(*) FROM analysis_results"
        ).fetchone()[0]
    assert len(results) == 5
    assert stored_count == 5
    assert all(row["responder_n"] == 331 for row in results)
    assert all(row["non_responder_n"] == 325 for row in results)
    assert all(0 <= row["adjusted_p_value"] <= 1 for row in results)
