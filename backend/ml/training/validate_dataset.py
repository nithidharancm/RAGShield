from pathlib import Path
import csv


DATASET_FILE = Path("ml/dataset/ragshield_dataset.csv")


def validate_dataset():
    if not DATASET_FILE.exists():
        print("ERROR: Dataset file was not found.")
        return

    with open(
        DATASET_FILE,
        "r",
        encoding="utf-8",
        newline=""
    ) as csv_file:

        reader = csv.DictReader(csv_file)
        rows = list(reader)

    print()
    print("===== RAGShield Dataset Validation =====")
    print()

    # Check number of rows
    print(f"Total samples: {len(rows)}")

    # Check required columns
    required_columns = {"text", "label"}

    if not required_columns.issubset(reader.fieldnames):
        print("ERROR: Dataset is missing required columns.")
        print(f"Found columns: {reader.fieldnames}")
        return

    print("Columns: OK")

    # Count labels
    safe_count = 0
    malicious_count = 0
    invalid_count = 0
    empty_count = 0

    for row in rows:
        text = row["text"].strip()
        label = row["label"].strip().upper()

        if not text:
            empty_count += 1

        if label == "SAFE":
            safe_count += 1

        elif label == "MALICIOUS":
            malicious_count += 1

        else:
            invalid_count += 1

    print(f"SAFE samples: {safe_count}")
    print(f"MALICIOUS samples: {malicious_count}")
    print(f"Empty samples: {empty_count}")
    print(f"Invalid labels: {invalid_count}")

    print()

    # Basic validation
    problems = []

    if len(rows) == 0:
        problems.append("Dataset contains no samples.")

    if safe_count == 0:
        problems.append("No SAFE samples found.")

    if malicious_count == 0:
        problems.append("No MALICIOUS samples found.")

    if empty_count > 0:
        problems.append("Some samples contain empty text.")

    if invalid_count > 0:
        problems.append("Some samples have invalid labels.")

    print("===== Validation Result =====")
    print()

    if problems:
        print("DATASET HAS PROBLEMS:")
        for problem in problems:
            print(f"- {problem}")
    else:
        print("DATASET VALIDATION PASSED!")
        print()
        print("The dataset is ready for the next preparation step.")


if __name__ == "__main__":
    validate_dataset()