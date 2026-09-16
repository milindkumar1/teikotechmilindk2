import sqlite3
from collections import defaultdict
from statistics import median

from scipy.stats import mannwhitneyu

from .queries import responder_subject_frequencies


METHOD = "Two-sided Mann-Whitney U on subject mean frequencies; BH-adjusted"


def _benjamini_hochberg(p_values: list[float]) -> list[float]:
    adjusted = [0.0] * len(p_values)
    order = sorted(range(len(p_values)), key=p_values.__getitem__)
    previous = 1.0
    for rank, index in reversed(list(enumerate(order, start=1))):
        value = min(previous, p_values[index] * len(p_values) / rank, 1.0)
        adjusted[index] = value
        previous = value
    return adjusted


def calculate_statistics(connection: sqlite3.Connection) -> list[dict[str, object]]:
    grouped: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: {"yes": [], "no": []}
    )
    for row in responder_subject_frequencies(connection):
        grouped[row["population"]][row["response"]].append(row["percentage"])

    results: list[dict[str, object]] = []
    for population in sorted(grouped):
        responders = grouped[population]["yes"]
        non_responders = grouped[population]["no"]
        if not responders or not non_responders:
            raise ValueError(f"Both response groups are required for {population}")
        test = mannwhitneyu(responders, non_responders, alternative="two-sided")
        responder_median = median(responders)
        non_responder_median = median(non_responders)
        results.append(
            {
                "population": population,
                "responder_n": len(responders),
                "non_responder_n": len(non_responders),
                "responder_median": responder_median,
                "non_responder_median": non_responder_median,
                "median_difference": responder_median - non_responder_median,
                "u_statistic": float(test.statistic),
                "p_value": float(test.pvalue),
                "rank_biserial": 2 * float(test.statistic) / (
                    len(responders) * len(non_responders)
                )
                - 1,
            }
        )

    adjusted = _benjamini_hochberg([float(row["p_value"]) for row in results])
    for row, adjusted_p_value in zip(results, adjusted, strict=True):
        row["adjusted_p_value"] = adjusted_p_value
        row["significant"] = adjusted_p_value < 0.05
        row["method"] = METHOD
    return results


def store_statistics(connection: sqlite3.Connection) -> list[dict[str, object]]:
    results = calculate_statistics(connection)
    connection.execute("DELETE FROM analysis_results")
    connection.executemany(
        """
        INSERT INTO analysis_results(
            population,
            responder_n,
            non_responder_n,
            responder_median,
            non_responder_median,
            median_difference,
            u_statistic,
            p_value,
            adjusted_p_value,
            rank_biserial,
            significant,
            method
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            (
                row["population"],
                row["responder_n"],
                row["non_responder_n"],
                row["responder_median"],
                row["non_responder_median"],
                row["median_difference"],
                row["u_statistic"],
                row["p_value"],
                row["adjusted_p_value"],
                row["rank_biserial"],
                int(row["significant"]),
                row["method"],
            )
            for row in results
        ),
    )
    connection.commit()
    return results

