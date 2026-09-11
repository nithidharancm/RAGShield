from pathlib import Path
import joblib

MODEL_FILE = Path(
    "ml/models/ragshield_isolation_forest.pkl"
)


def predict_anomaly(text):
    """
    Predict whether a document is unusual compared
    with the SAFE training corpus.
    """

    if not MODEL_FILE.exists():
        raise FileNotFoundError(
            f"Isolation Forest model not found: {MODEL_FILE}"
        )

    model = joblib.load(MODEL_FILE)

    prediction = model.predict([text])[0]

    decision_score = float(
        model.decision_function([text])[0]
    )

    return {
        "prediction": (
            "ANOMALY"
            if prediction == -1
            else "NORMAL"
        ),
        "is_anomaly": prediction == -1,
        "decision_score": decision_score
    }