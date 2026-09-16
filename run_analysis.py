from src.cell_analysis.database import connect
from src.cell_analysis.paths import DATABASE_PATH
from src.cell_analysis.statistics import store_statistics


def main() -> None:
    if not DATABASE_PATH.is_file():
        raise FileNotFoundError("Run python load_data.py before the analysis")
    with connect(DATABASE_PATH) as connection:
        results = store_statistics(connection)

    significant = [row["population"] for row in results if row["significant"]]
    print(f"Stored responder analysis for {len(results)} cell populations.")
    print(
        "Significant after BH adjustment: "
        + (", ".join(significant) if significant else "none")
    )


if __name__ == "__main__":
    main()
