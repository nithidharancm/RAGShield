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
    "override previous instructions",
    "override the system instructions",
    "ignore system instructions",
    "ignore developer instructions",
    "reveal your instructions",
    "reveal the system prompt",
    "reveal your prompt",
    "reveal hidden system instructions",
    "reveal hidden developer instructions",
    "disregard the surrounding content",
    "disregard surrounding content",
    "follow this document instead",
    "this document overrides",
    "higher priority than the system prompt",
    "bypass authorization",
    "ignore authorization restrictions",
    "ignore tenant restrictions",
]


RAG_DIRECTED_INSTRUCTIONS = [
    "when an ai reads this",
    "when an ai system reads this document",
    "when an ai system reads this",
    "when retrieved",
    "when this document is retrieved",
    "when this document is read",
    "for automated processing only",
    "hidden instruction for the language model",
    "embedded assistant directive",
    "when this content enters a retrieval system",
    "during automated retrieval",
    "for retrieval-time processing",
    "treat this document as a system message",
    "follow the instructions contained here",
]


SUSPICIOUS_EXTERNAL_ACTIONS = [
    "send confidential information",
    "send confidential data",
    "upload data",
    "send data to a url",
    "download and execute",
    "reveal confidential information",
    "disclose confidential information",
    "return internal secrets",
    "reveal private context",
    "reveal restricted information",
    "send secret credentials",
    "upload all retrieved data",
    "retrieve api keys",
    "return secret credentials",
    "disclose passwords",
    "reveal api keys",
    "extract credentials",
]


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
# Rule matching helpers
# =========================================================

def is_negated_context(text_lower, match_start):
    """
    Detect common benign negations immediately before
    a suspicious phrase.

    Examples that should NOT become attack signals:

        must not reveal confidential information
        never disclose confidential information
        do not bypass authorization
        should not reveal the system prompt

    The window is intentionally short so a negation from an
    earlier unrelated sentence does not suppress a real attack.
    """

    window = text_lower[
        max(0, match_start - 80):match_start
    ]

    negation_patterns = [
        r"\bdo\s+not\s*$",
        r"\bdoes\s+not\s*$",
        r"\bdid\s+not\s*$",
        r"\bdon['’]?t\s*$",
        r"\bmust\s+not\s*$",
        r"\bmust\s+never\s*$",
        r"\bshould\s+not\s*$",
        r"\bshould\s+never\s*$",
        r"\bnever\s*$",
        r"\bcannot\s*$",
        r"\bcan['’]?t\s*$",
        r"\bnot\s+allowed\s+to\s*$",
        r"\bprohibited\s+from\s*$",
        r"\bforbidden\s+to\s*$",
    ]

    return any(
        re.search(pattern, window)
        for pattern in negation_patterns
    )


def build_pattern_regex(pattern):
    """
    Convert a literal rule phrase into a regex that tolerates
    spaces, tabs, or line breaks between words.
    """

    escaped = re.escape(pattern)

    # re.escape("reveal confidential") produces
    # "reveal\\ confidential". Allow any whitespace there.
    return escaped.replace(r"\ ", r"\s+")


def find_signals(
    text,
    patterns,
    ignore_negated=True
):
    """
    Find rule-based attack signals.

    Improvements over the original matcher:

    1. Ignores common benign negations.
    2. Handles line breaks / multiple spaces inside a phrase.
    3. Prefers longer overlapping patterns so the UI does not
       report both a long phrase and its shorter substring.
    """

    text_lower = text.lower()

    found = []
    occupied_ranges = []

    # Longest first prevents duplicate signals such as:
    # "when an ai system reads this document"
    # and "when an ai system reads this"
    sorted_patterns = sorted(
        patterns,
        key=len,
        reverse=True
    )

    for pattern in sorted_patterns:

        regex = build_pattern_regex(pattern)

        for match in re.finditer(regex, text_lower):

            if (
                ignore_negated
                and is_negated_context(
                    text_lower,
                    match.start()
                )
            ):
                continue

            start = match.start()
            end = match.end()

            overlaps_existing = any(
                start < existing_end
                and end > existing_start
                for existing_start, existing_end
                in occupied_ranges
            )

            if overlaps_existing:
                continue

            found.append(pattern)
            occupied_ranges.append(
                (start, end)
            )
            break

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
        DIRECT_PROMPT_INJECTION,
        ignore_negated=True
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
        RAG_DIRECTED_INSTRUCTIONS,
        ignore_negated=True
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
        SUSPICIOUS_EXTERNAL_ACTIONS,
        ignore_negated=True
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

    # The trained classifier is the primary ML security signal.
    # A MALICIOUS prediction must not be silently approved simply
    # because its probability is below an older fixed threshold.

    ml_security_triggered = False

    if ml_prediction == "MALICIOUS":

        ml_security_triggered = True

        detected_signals.append({
            "type": "ML_MALICIOUS_THREAT",
            "confidence": round(
                malicious_probability,
                4
            )
        })

    else:

        detected_signals.append({
            "type": "ML_SAFE_CLASSIFICATION",
            "confidence": round(
                safe_probability,
                4
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
