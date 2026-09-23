from pathlib import Path

import joblib
import pandas as pd

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix
)


# --------------------------------------------------
# File locations
# --------------------------------------------------

TEST_FILE = Path("ml/dataset/test_v2.csv")
MODEL_FILE = Path("ml/models/ragshield_detector.pkl")


# --------------------------------------------------
# Load test data
# --------------------------------------------------

def load_test_data():

    if not TEST_FILE.exists():
        raise FileNotFoundError(
            f"Test file not found: {TEST_FILE}"
        )

    data = pd.read_csv(TEST_FILE)

    if "text" not in data.columns:
        raise ValueError(
            "Test dataset must contain a 'text' column."
        )

    if "label" not in data.columns:
        raise ValueError(
            "Test dataset must contain a 'label' column."
        )

    return data


# --------------------------------------------------
# Evaluate model
# --------------------------------------------------

def evaluate_model():

    print()
    print("===== RAGShield ML Evaluation =====")
    print()

    if not MODEL_FILE.exists():
        raise FileNotFoundError(
            f"Model not found: {MODEL_FILE}"
        )

    model = joblib.load(MODEL_FILE)

    data = load_test_data()

    X_test = data["text"]
    y_test = data["label"]

    print(f"Testing samples: {len(data)}")
    print()

    # Make predictions
    predictions = model.predict(X_test)

    # --------------------------------------------------
    # Metrics
    # --------------------------------------------------

    accuracy = accuracy_score(
        y_test,
        predictions
    )

    print("Accuracy:")
    print(f"{accuracy:.2%}")
    print()

    print("Classification Report:")
    print(
        classification_report(
            y_test,
            predictions,
            zero_division=0
        )
    )

    print("Confusion Matrix:")

    matrix = confusion_matrix(
        y_test,
        predictions,
        labels=[
            "SAFE",
            "MALICIOUS"
        ]
    )

    print(matrix)
    print()

    # --------------------------------------------------
    # Individual predictions
    # --------------------------------------------------

    print("===== Individual Predictions =====")
    print()

    for index, row in data.iterrows():

        text = row["text"]
        actual = row["label"]
        predicted = predictions[index]

        print(f"Sample {index + 1}")
        print(f"Actual:    {actual}")
        print(f"Predicted: {predicted}")

        if actual == predicted:
            print("Result:    CORRECT")
        else:
            print("Result:    INCORRECT")

        print()

        # Show the document when prediction is wrong
        if actual != predicted:
            print("----- INCORRECT SAMPLE TEXT -----")
            print(text)
            print("----- END INCORRECT SAMPLE -----")
            print()

        print("-" * 60)
        print()


if __name__ == "__main__":
    evaluate_model()