from pathlib import Path

import joblib
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline


# --------------------------------------------------
# File locations
# --------------------------------------------------

TRAIN_FILE = Path("ml/dataset/train_v2.csv")
MODEL_FILE = Path("ml/models/ragshield_detector.pkl")


# --------------------------------------------------
# Load training data
# --------------------------------------------------

def load_training_data():
    if not TRAIN_FILE.exists():
        raise FileNotFoundError(
            f"Training file not found: {TRAIN_FILE}"
        )

    data = pd.read_csv(TRAIN_FILE)

    if "text" not in data.columns:
        raise ValueError(
            "Training dataset must contain a 'text' column."
        )

    if "label" not in data.columns:
        raise ValueError(
            "Training dataset must contain a 'label' column."
        )

    if data.empty:
        raise ValueError(
            "Training dataset is empty."
        )

    return data


# --------------------------------------------------
# Train the model
# --------------------------------------------------

def train_model():
    print()
    print("===== RAGShield ML Training =====")
    print()

    data = load_training_data()

    print(f"Training samples: {len(data)}")
    print()

    print("Label distribution:")

    print(
        data["label"].value_counts()
    )

    print()

    # --------------------------------------------------
    # TF-IDF + Logistic Regression
    # --------------------------------------------------

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

    # Train
    model.fit(
        data["text"],
        data["label"]
    )

    # Create models directory if necessary
    MODEL_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # Save trained model
    joblib.dump(
        model,
        MODEL_FILE
    )

    print("Training completed successfully!")
    print()
    print(f"Model saved to: {MODEL_FILE}")
    print()


# --------------------------------------------------
# Run
# --------------------------------------------------

if __name__ == "__main__":
    train_model()