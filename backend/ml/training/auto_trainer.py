from pathlib import Path

import joblib
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline


# --------------------------------------------------
# File locations
# --------------------------------------------------

TRAIN_FILE = Path(
    "ml/dataset/train.csv"
)

NEW_SAMPLES_FILE = Path(
    "ml/dataset/new_samples.csv"
)

MODEL_FILE = Path(
    "ml/models/ragshield_detector.pkl"
)

BACKUP_MODEL_FILE = Path(
    "ml/models/ragshield_detector_backup.pkl"
)


# --------------------------------------------------
# Automatic training settings
# --------------------------------------------------

MINIMUM_NEW_SAMPLES = 10

MINIMUM_ACCURACY = 0.80


# --------------------------------------------------
# Load original training data
# --------------------------------------------------

def load_training_data():

    if not TRAIN_FILE.exists():

        raise FileNotFoundError(
            f"Training file not found: {TRAIN_FILE}"
        )

    data = pd.read_csv(
        TRAIN_FILE
    )

    if "text" not in data.columns:

        raise ValueError(
            "Dataset must contain a 'text' column."
        )

    if "label" not in data.columns:

        raise ValueError(
            "Dataset must contain a 'label' column."
        )

    data = data.dropna(
        subset=[
            "text",
            "label"
        ]
    )

    data["text"] = (
        data["text"].astype(str)
    )

    data["label"] = (
        data["label"].astype(str)
    )

    if data.empty:

        raise ValueError(
            "Training dataset is empty."
        )

    return data


# --------------------------------------------------
# Load automatically collected samples
# --------------------------------------------------

def load_new_samples():

    if not NEW_SAMPLES_FILE.exists():

        return pd.DataFrame(
            columns=[
                "text",
                "label"
            ]
        )

    data = pd.read_csv(
        NEW_SAMPLES_FILE
    )

    if data.empty:

        return pd.DataFrame(
            columns=[
                "text",
                "label"
            ]
        )

    if "text" not in data.columns:

        raise ValueError(
            "New samples must contain "
            "a 'text' column."
        )

    if "label" not in data.columns:

        raise ValueError(
            "New samples must contain "
            "a 'label' column."
        )

    data = data.dropna(
        subset=[
            "text",
            "label"
        ]
    )

    data["text"] = (
        data["text"].astype(str)
    )

    data["label"] = (
        data["label"].astype(str)
    )

    return data


# --------------------------------------------------
# Combine training datasets
# --------------------------------------------------

def build_combined_dataset():

    original_data = (
        load_training_data()
    )

    new_data = (
        load_new_samples()
    )

    print(
        "[RAGShield ML] "
        f"Original samples: "
        f"{len(original_data)}"
    )

    print(
        "[RAGShield ML] "
        f"New samples: "
        f"{len(new_data)}"
    )

    if new_data.empty:

        return original_data

    # --------------------------------------------------
    # Combine datasets
    # --------------------------------------------------

    combined_data = pd.concat(
        [
            original_data,
            new_data
        ],
        ignore_index=True
    )

    # --------------------------------------------------
    # Remove duplicate text
    # --------------------------------------------------

    combined_data = (
        combined_data
        .drop_duplicates(
            subset=["text"]
        )
        .reset_index(drop=True)
    )

    print(
        "[RAGShield ML] "
        f"Combined samples: "
        f"{len(combined_data)}"
    )

    return combined_data


# --------------------------------------------------
# Build ML model
# --------------------------------------------------

def build_model():

    model = Pipeline([
        (
            "tfidf",
            TfidfVectorizer(
                lowercase=True,
                ngram_range=(1, 2),
                min_df=1
            )
        ),
        (
            "classifier",
            LogisticRegression(
                max_iter=1000,
                random_state=42
            )
        )
    ])

    return model


# --------------------------------------------------
# Check whether retraining is needed
# --------------------------------------------------

def should_retrain():

    new_data = (
        load_new_samples()
    )

    sample_count = len(
        new_data
    )

    print(
        "[RAGShield ML] "
        f"New samples available: "
        f"{sample_count}"
    )

    if sample_count < MINIMUM_NEW_SAMPLES:

        print(
            "[RAGShield ML] "
            f"Waiting for "
            f"{MINIMUM_NEW_SAMPLES} "
            "new samples before retraining."
        )

        return False

    return True


# --------------------------------------------------
# Train new model
# --------------------------------------------------

def train_new_model():

    print()
    print(
        "===== RAGShield Automatic ML Training ====="
    )
    print()

    data = (
        build_combined_dataset()
    )

    print(
        "[RAGShield ML] "
        f"Training with "
        f"{len(data)} samples."
    )

    print()

    print(
        "[RAGShield ML] Label distribution:"
    )

    print(
        data["label"].value_counts()
    )

    print()

    # --------------------------------------------------
    # Build model
    # --------------------------------------------------

    model = build_model()

    # --------------------------------------------------
    # Train
    # --------------------------------------------------

    model.fit(
        data["text"],
        data["label"]
    )

    print(
        "[RAGShield ML] "
        "New model trained successfully."
    )

    return model


# --------------------------------------------------
# Evaluate model
# --------------------------------------------------

def evaluate_model(model):

    data = (
        build_combined_dataset()
    )

    predictions = (
        model.predict(
            data["text"]
        )
    )

    correct = (
        predictions == data["label"]
    ).sum()

    accuracy = (
        correct / len(data)
    )

    print(
        "[RAGShield ML] "
        f"Combined training accuracy: "
        f"{accuracy:.2%}"
    )

    return accuracy


# --------------------------------------------------
# Backup current model
# --------------------------------------------------

def backup_current_model():

    if not MODEL_FILE.exists():

        print(
            "[RAGShield ML] "
            "No previous model to backup."
        )

        return

    current_model = joblib.load(
        MODEL_FILE
    )

    joblib.dump(
        current_model,
        BACKUP_MODEL_FILE
    )

    print(
        "[RAGShield ML] "
        f"Previous model backed up to: "
        f"{BACKUP_MODEL_FILE}"
    )


# --------------------------------------------------
# Activate new model
# --------------------------------------------------

def activate_model(model):

    MODEL_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    backup_current_model()

    joblib.dump(
        model,
        MODEL_FILE
    )

    print(
        "[RAGShield ML] "
        "New model activated."
    )


# --------------------------------------------------
# Clear processed samples
# --------------------------------------------------

def clear_new_samples():

    if not NEW_SAMPLES_FILE.exists():

        return

    NEW_SAMPLES_FILE.unlink()

    print(
        "[RAGShield ML] "
        "Processed training samples cleared."
    )


# --------------------------------------------------
# Automatic retraining
# --------------------------------------------------

def auto_retrain():

    print()
    print(
        "===== RAGShield Auto Trainer ====="
    )
    print()

    # --------------------------------------------------
    # Check sample count
    # --------------------------------------------------

    if not should_retrain():

        print(
            "[RAGShield ML] "
            "Retraining not required."
        )

        return {
            "retrained": False,
            "activated": False,
            "reason": (
                "Not enough new samples."
            )
        }

    # --------------------------------------------------
    # Train
    # --------------------------------------------------

    new_model = (
        train_new_model()
    )

    # --------------------------------------------------
    # Evaluate
    # --------------------------------------------------

    accuracy = (
        evaluate_model(
            new_model
        )
    )

    # --------------------------------------------------
    # Safety check
    # --------------------------------------------------

    if accuracy < MINIMUM_ACCURACY:

        print(
            "[RAGShield ML] "
            "New model rejected."
        )

        print(
            "[RAGShield ML] "
            f"Accuracy {accuracy:.2%} "
            f"is below required "
            f"{MINIMUM_ACCURACY:.2%}."
        )

        return {
            "retrained": True,
            "activated": False,
            "accuracy": accuracy,
            "reason": (
                "Model failed quality check."
            )
        }

    # --------------------------------------------------
    # Activate
    # --------------------------------------------------

    activate_model(
        new_model
    )

    # --------------------------------------------------
    # Remove samples that were consumed
    # --------------------------------------------------

    clear_new_samples()

    print()
    print(
        "===== Automatic Training Complete ====="
    )
    print()

    return {
        "retrained": True,
        "activated": True,
        "accuracy": accuracy
    }


# --------------------------------------------------
# Run manually
# --------------------------------------------------

if __name__ == "__main__":

    result = auto_retrain()

    print()
    print("Result:")
    print(result)