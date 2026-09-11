from ingestion.isolation_detector import predict_anomaly


def calculate_corpus_anomaly_score(text):
    """
    Convert the Isolation Forest result into a conservative
    RAGShield risk contribution.

    IMPORTANT:
    Isolation Forest should be treated as one security signal,
    not as proof that a document is malicious.
    """

    result = predict_anomaly(text)

    if result["is_anomaly"]:
        # Conservative contribution.
        # Rule-based and supervised ML signals can still
        # provide the stronger final security decision.
        return 30

    return 0
