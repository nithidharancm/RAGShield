from pathlib import Path

import joblib
import pandas as pd

from sklearn.ensemble import IsolationForest
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.decomposition import TruncatedSVD


TRAIN_FILE = Path("ml/dataset/train.csv")
MODEL_FILE = Path("ml/models/ragshield_isolation_forest.pkl")


def train_isolation_forest():
    if not TRAIN_FILE.exists():
        raise FileNotFoundError(
            f"Training file not found: {TRAIN_FILE}"
        )

    data = pd.read_csv(TRAIN_FILE)

    if "text" not in data.columns:
        raise ValueError("Training dataset must contain a 'text' column.")

    # Isolation Forest is used here as an UNSUPERVISED anomaly detector.
    # We learn the normal/SAFE document distribution only.
    safe_data = data[
        data["label"].astype(str).str.upper() == "SAFE"
    ].copy()

    if len(safe_data) < 10:
        raise ValueError(
            "At least 10 SAFE documents are recommended for "
            "Isolation Forest training."
        )

    print("===== RAGShield Isolation Forest Training =====")
    print(f"SAFE training documents: {len(safe_data)}")

    pipeline = Pipeline([
        (
            "tfidf",
            TfidfVectorizer(
                lowercase=True,
                ngram_range=(1, 2),
                min_df=1
            )
        ),
        (
            "svd",
            TruncatedSVD(
                n_components=min(50, max(2, len(safe_data) - 1)),
                random_state=42
            )
        ),
        (
            "isolation_forest",
            IsolationForest(
                n_estimators=200,
                contamination="auto",
                random_state=42,
                n_jobs=-1
            )
        )
    ])

    pipeline.fit(safe_data["text"])

    MODEL_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    joblib.dump(pipeline, MODEL_FILE)

    print("Isolation Forest training completed!")
    print(f"Model saved to: {MODEL_FILE}")


if __name__ == "__main__":
    train_isolation_forest()
