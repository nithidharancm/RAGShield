from pathlib import Path
import csv


# Location of our sample dataset
DATASET_FOLDER = Path("ml/dataset")

# Output CSV file
OUTPUT_FILE = DATASET_FOLDER / "ragshield_dataset.csv"


def read_documents(folder_name, label):
    """
    Read all TXT files from a dataset folder
    and assign the specified label.
    """

    folder = DATASET_FOLDER / folder_name

    documents = []

    for file_path in folder.glob("*.txt"):
        try:
            text = file_path.read_text(
                encoding="utf-8",
                errors="replace"
            ).strip()

            if text:
                documents.append({
                    "text": text,
                    "label": label
                })

        except Exception as error:
            print(f"Could not read {file_path}: {error}")

    return documents


def create_dataset():
    """
    Combine safe, malicious and borderline documents
    into one CSV dataset.
    """

    dataset = []

    # Safe documents
    dataset.extend(
        read_documents(
            "safe",
            "SAFE"
        )
    )

    # Malicious documents
    dataset.extend(
        read_documents(
            "malicious",
            "MALICIOUS"
        )
    )

    # Borderline documents are legitimate policy language,
    # so they are also labeled SAFE.
    dataset.extend(
        read_documents(
            "borderline",
            "SAFE"
        )
    )

    # Write the dataset to CSV
    with open(
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8"
    ) as csv_file:

        writer = csv.DictWriter(
            csv_file,
            fieldnames=["text", "label"]
        )

        writer.writeheader()

        for row in dataset:
            writer.writerow(row)

    print()
    print("Dataset created successfully!")
    print()
    print(f"Location: {OUTPUT_FILE}")
    print(f"Total documents: {len(dataset)}")

    safe_count = sum(
        1 for row in dataset
        if row["label"] == "SAFE"
    )

    malicious_count = sum(
        1 for row in dataset
        if row["label"] == "MALICIOUS"
    )

    print(f"SAFE documents: {safe_count}")
    print(f"MALICIOUS documents: {malicious_count}")


if __name__ == "__main__":
    create_dataset()