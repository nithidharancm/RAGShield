from pathlib import Path
import joblib


# Location of our trained ML model
MODEL_FILE = Path("ml/models/ragshield_detector.pkl")


def predict_document(text):
    """
    Use the trained RAGShield ML model
    to classify a document as SAFE or MALICIOUS.
    """

    # Make sure the trained model exists
    if not MODEL_FILE.exists():
        raise FileNotFoundError(
            f"ML model not found: {MODEL_FILE}"
        )

    # Load the trained model
    model = joblib.load(MODEL_FILE)

    # Predict the document
    prediction = model.predict([text])[0]

    # Get probability for each class
    probabilities = model.predict_proba([text])[0]
    classes = model.classes_

    probability_map = dict(
        zip(classes, probabilities)
    )

    return {
        "prediction": prediction,
        "safe_probability": float(
            probability_map.get("SAFE", 0)
        ),
        "malicious_probability": float(
            probability_map.get("MALICIOUS", 0)
        )
    }