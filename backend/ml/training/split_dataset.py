from pathlib import Path

import pandas as pd

from sklearn.model_selection import train_test_split


INPUT_FILE = Path("ml/dataset/ragshield_dataset.csv")
TRAIN_FILE = Path("ml/dataset/train.csv")
TEST_FILE = Path("ml/dataset/test.csv")

TEST_SIZE = 0.2
RANDOM_SEED = 42


def split_dataset():

    print()
    print("===== RAGShield Dataset Split =====")
    print()

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Dataset file not found: {INPUT_FILE}"
        )

    # Load the complete dataset
    data = pd.read_csv(INPUT_FILE)

    if "text" not in data.columns:
        raise ValueError(
            "Dataset must contain a 'text' column."
        )

    if "label" not in data.columns:
        raise ValueError(
            "Dataset must contain a 'label' column."
        )

    print(f"Total samples: {len(data)}")
    print()

    print("Original label distribution:")
    print(data["label"].value_counts())
    print()

    # Split the dataset while preserving
    # the SAFE/MALICIOUS class ratio.
    train_data, test_data = train_test_split(
        data,
        test_size=TEST_SIZE,
        random_state=RANDOM_SEED,
        stratify=data["label"]
    )

    # Save training data
    train_data.to_csv(
        TRAIN_FILE,
        index=False
    )

    # Save testing data
    test_data.to_csv(
        TEST_FILE,
        index=False
    )

    print("Training label distribution:")
    print(train_data["label"].value_counts())
    print()

    print("Testing label distribution:")
    print(test_data["label"].value_counts())
    print()

    print(f"Training samples: {len(train_data)}")
    print(f"Testing samples: {len(test_data)}")
    print()

    print(f"Training file: {TRAIN_FILE}")
    print(f"Testing file:  {TEST_FILE}")
    print()

    print("Dataset split completed successfully!")


if __name__ == "__main__":
    split_dataset()