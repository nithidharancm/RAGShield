import re

from ingestion.ml_detector import predict_document
from ml.training.sample_collector import save_training_sample


# =========================================================
# Rule-based security patterns
# =========================================================

DIRECT_PROMPT_INJECTION = [
    "ignore previous instructions",
    "ignore all instructions",
    "forget previous instructions",
    "forget everything you were previously instructed",
    "system message",
    "system prompt",
    "system-level instruction",
    "developer message",
    "developer instructions",
    "reveal your instructions",
    "reveal the system prompt",
    "reveal your prompt",
    "hidden system instructions",
    "hidden developer instructions",
]


RAG_DIRECTED_INSTRUCTIONS = [
    "when an ai reads this",
    "when retrieved",
    "when this document is retrieved",
    "when this document is read",
    "assistant should",
    "assistant must",
    "llm should",
    "llm must",
    "ai should",
    "ai must",
    "follow the instructions contained here",
]


SUSPICIOUS_EXTERNAL_ACTIONS = [
    "send confidential information",
    "upload data",
    "send data to a url",
    "download and execute",
]


# =========================================================
# ML security thresholds
# =========================================================

HIGH_CONFIDENCE = 0.90
MEDIUM_CONFIDENCE = 0.60


# =========================================================
# Corpus anomaly placeholder
# =========================================================

def calculate_corpus_anomaly_score(text):
    """
    Placeholder for corpus anomaly detection.

    Future version can use embeddings to compare
    this document against the existing corpus.
    """

    return 0


# =========================================================
# Find rule-based signals
# =========================================================

def find_signals(text, patterns):

    text_lower = text.lower()

    found = []

    for pattern in patterns:

        if re.search(
            re.escape(pattern),
            text_lower
        ):

            found.append(pattern)

    return found


# =========================================================
# Collect ML training sample
# =========================================================

def collect_ml_training_sample(
    text,
    ml_prediction,
    safe_probability,
    malicious_probability,
    rule_signals
):
    """
    Save a document as a provisional ML training example.

    SAFE examples require high ML confidence.

    MALICIOUS examples can also be trusted when
    independent rule-based security signals agree.

    Uncertain examples are placed in the
    borderline dataset.
    """

    if ml_prediction == "SAFE":

        confidence = safe_probability

    elif ml_prediction == "MALICIOUS":

        confidence = malicious_probability

    else:

        return False

    return save_training_sample(
        text=text,
        label=ml_prediction,
        confidence=confidence,
        rule_signals=rule_signals
    )


# =========================================================
# Main document scanner
# =========================================================

def scan_document(text):
    """
    Perform RAGShield ingestion security scanning.

    Security layers:

    1. Rule-based security detection
    2. ML-based poisoning detection
    3. Corpus anomaly detection placeholder
    4. Controlled ML sample collection

    The final decision uses multiple signals.
    """

    detected_signals = []

    risk_score = 0

    # =====================================================
    # 1. DIRECT PROMPT INJECTION
    # =====================================================

    direct_signals = find_signals(
        text,
        DIRECT_PROMPT_INJECTION
    )

    for signal in direct_signals:

        detected_signals.append({
            "type": "DIRECT_PROMPT_INJECTION",
            "signal": signal
        })

        risk_score += 60

    # =====================================================
    # 2. RAG-DIRECTED INSTRUCTIONS
    # =====================================================

    rag_signals = find_signals(
        text,
        RAG_DIRECTED_INSTRUCTIONS
    )

    for signal in rag_signals:

        detected_signals.append({
            "type": "RAG_DIRECTED_INSTRUCTION",
            "signal": signal
        })

        risk_score += 30

    # =====================================================
    # 3. SUSPICIOUS EXTERNAL ACTIONS
    # =====================================================

    external_signals = find_signals(
        text,
        SUSPICIOUS_EXTERNAL_ACTIONS
    )

    for signal in external_signals:

        detected_signals.append({
            "type": "SUSPICIOUS_EXTERNAL_ACTION",
            "signal": signal
        })

        risk_score += 50

    # =====================================================
    # 4. ML POISONING DETECTION
    # =====================================================

    ml_result = predict_document(text)

    ml_prediction = ml_result["prediction"]

    safe_probability = ml_result[
        "safe_probability"
    ]

    malicious_probability = ml_result[
        "malicious_probability"
    ]

    detected_signals.append({
        "type": "ML_CLASSIFICATION",
        "prediction": ml_prediction,
        "safe_probability": round(
            safe_probability,
            4
        ),
        "malicious_probability": round(
            malicious_probability,
            4
        )
    })

    # =====================================================
    # 5. COUNT INDEPENDENT RULE SIGNALS
    # =====================================================

    rule_signal_count = (
        len(direct_signals)
        + len(rag_signals)
        + len(external_signals)
    )

    # =====================================================
    # 6. ML SECURITY DECISION
    # =====================================================

    ml_security_triggered = False

    # -----------------------------------------------------
    # High-confidence malicious ML prediction
    # -----------------------------------------------------

    if (
        ml_prediction == "MALICIOUS"
        and malicious_probability >= HIGH_CONFIDENCE
    ):

        ml_security_triggered = True

        detected_signals.append({
            "type": "HIGH_CONFIDENCE_ML_THREAT",
            "confidence": round(
                malicious_probability,
                4
            )
        })

    # -----------------------------------------------------
    # Medium-confidence ML + independent rule evidence
    # -----------------------------------------------------

    elif (
        ml_prediction == "MALICIOUS"
        and malicious_probability >= MEDIUM_CONFIDENCE
        and rule_signal_count >= 1
    ):

        ml_security_triggered = True

        detected_signals.append({
            "type": "ML_PLUS_RULE_THREAT",
            "confidence": round(
                malicious_probability,
                4
            ),
            "rule_signals": rule_signal_count
        })

    # -----------------------------------------------------
    # Low-confidence ML prediction
    # -----------------------------------------------------

    elif (
        ml_prediction == "MALICIOUS"
        and malicious_probability < MEDIUM_CONFIDENCE
        and rule_signal_count == 0
    ):

        detected_signals.append({
            "type": "LOW_CONFIDENCE_ML_WARNING",
            "confidence": round(
                malicious_probability,
                4
            ),
            "message": (
                "ML prediction is uncertain and "
                "has no independent rule evidence."
            )
        })

    # =====================================================
    # 7. APPLY ML SECURITY SCORE
    # =====================================================

    if ml_security_triggered:

        risk_score += 60

    # =====================================================
    # 8. COLLECT ML TRAINING SAMPLE
    # =====================================================

    training_sample_saved = (
        collect_ml_training_sample(
            text=text,
            ml_prediction=ml_prediction,
            safe_probability=safe_probability,
            malicious_probability=malicious_probability,
            rule_signals=rule_signal_count
        )
    )

    # =====================================================
    # 9. CORPUS ANOMALY
    # =====================================================

    anomaly_score = (
        calculate_corpus_anomaly_score(text)
    )

    if anomaly_score > 0:

        detected_signals.append({
            "type": "CORPUS_ANOMALY",
            "signal": (
                f"Anomaly score: "
                f"{anomaly_score}"
            )
        })

        risk_score += anomaly_score

    # =====================================================
    # 10. LIMIT RISK SCORE
    # =====================================================

    risk_score = min(
        risk_score,
        100
    )

    # =====================================================
    # 11. FINAL SECURITY DECISION
    # =====================================================

    if risk_score >= 60:

        status = "QUARANTINED"

    else:

        status = "APPROVED"

    # =====================================================
    # 12. RETURN RESULT
    # =====================================================

    return {

        "risk_score": risk_score,

        "detected_signals": detected_signals,

        "status": status,

        "ml_prediction": ml_prediction,

        "ml_malicious_probability":
            malicious_probability,

        "ml_safe_probability":
            safe_probability,

        "training_sample_saved":
            training_sample_saved
    }