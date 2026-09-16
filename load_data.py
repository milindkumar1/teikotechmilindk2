from src.cell_analysis.loader import load_database
from src.cell_analysis.paths import DATABASE_PATH


def main() -> None:
    sample_count, subject_count = load_database()
    print(
        f"Created {DATABASE_PATH.name} with "
        f"{sample_count:,} samples from {subject_count:,} subjects."
    )


if __name__ == "__main__":
    main()
