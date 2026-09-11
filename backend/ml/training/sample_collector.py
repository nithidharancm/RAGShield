from pathlib import Path

import pandas as pd


# --------------------------------------------------
# File locations
# --------------------------------------------------

NEW_SAMPLES_FILE = Path(
    "ml/dataset/new_samples.csv"
)

BORDERLINE_FILE = Path(
    "ml/dataset/borderline_samples.csv"
)


# --------------------------------------------------
# ML confidence thresholds
# --------------------------------------------------

HIGH_CONFIDENCE = 0.90

BORDERLINE_CONFIDENCE = 0.60


# --------------------------------------------------
# Save a trusted ML training sample
# --------------------------------------------------

def save_training_sample(
    text: str,
    label: str,
    confidence: float,
    rule_signals: int = 0
):
    """
    Save a document as a provisional ML training sample.

    SAFE samples require high ML confidence.

    MALICIOUS samples can also use strong independent
    rule-based security signals.

    Uncertain examples are placed in the
    borderline dataset instead.
    """

    if not text:
        return False

    if label not in {
        "SAFE",
        "MALICIOUS"
    }:
        return False

    # --------------------------------------------------
    # SAFE training example
    # --------------------------------------------------

    if label == "SAFE":

        if confidence >= HIGH_CONFIDENCE:

            save_sample(
                text,
                label
            )

            print(
                "[RAGShield ML] "
                "High-confidence SAFE sample saved."
            )

            return True

        save_borderline_sample(
            text,
            label,
            confidence
        )

        print(
            "[RAGShield ML] "
            "SAFE sample placed in borderline dataset."
        )

        return False

    # --------------------------------------------------
    # MALICIOUS training example
    # --------------------------------------------------

    if label == "MALICIOUS":

        # Strong ML confidence
        if confidence >= HIGH_CONFIDENCE:

            save_sample(
                text,
                label
            )

            print(
                "[RAGShield ML] "
                "High-confidence MALICIOUS "
                "sample saved."
            )

            return True

        # ML + independent rule evidence
        if (
            confidence >= BORDERLINE_CONFIDENCE
            and rule_signals >= 1
        ):

            save_sample(
                text,
                label
            )

            print(
                "[RAGShield ML] "
                "MALICIOUS sample saved using "
                "ML + rule evidence."
            )

            return True

        # Otherwise borderline
        save_borderline_sample(
            text,
            label,
            confidence
        )

        print(
            "[RAGShield ML] "
            "MALICIOUS sample placed in "
            "borderline dataset."
        )

        return False

    return False


# --------------------------------------------------
# Save trusted sample
# --------------------------------------------------

def save_sample(
    text: str,
    label: str
):

    NEW_SAMPLES_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    new_sample = pd.DataFrame([
        {
            "text": text,
            "label": label
        }
    ])

    if NEW_SAMPLES_FILE.exists():

        new_sample.to_csv(
            NEW_SAMPLES_FILE,
            mode="a",
            header=False,
            index=False
        )

    else:

        new_sample.to_csv(
            NEW_SAMPLES_FILE,
            index=False
        )


# --------------------------------------------------
# Save borderline sample
# --------------------------------------------------

def save_borderline_sample(
    text: str,
    label: str,
    confidence: float
):

    BORDERLINE_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    new_sample = pd.DataFrame([
        {
            "text": text,
            "label": label,
            "confidence": confidence
        }
    ])

    if BORDERLINE_FILE.exists():

        new_sample.to_csv(
            BORDERLINE_FILE,
            mode="a",
            header=False,
            index=False
        )

    else:

        new_sample.to_csv(
            BORDERLINE_FILE,
            index=False
        )


# --------------------------------------------------
# Count trusted samples
# --------------------------------------------------

def count_new_samples():

    if not NEW_SAMPLES_FILE.exists():
        return 0

    data = pd.read_csv(
        NEW_SAMPLES_FILE
    )

    return len(data)


# --------------------------------------------------
# Count borderline samples
# --------------------------------------------------

def count_borderline_samples():

    if not BORDERLINE_FILE.exists():
        return 0

    data = pd.read_csv(
        BORDERLINE_FILE
    )

    return len(data)


# --------------------------------------------------
# Test
# --------------------------------------------------

if __name__ == "__main__":

    print(
        "Trusted new samples:",
        count_new_samples()
    )

    print(
        "Borderline samples:",
        count_borderline_samples()
    )