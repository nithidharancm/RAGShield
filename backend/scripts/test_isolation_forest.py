from pathlib import Path

from ingestion.isolation_detector import predict_anomaly


BASE = Path("test_documents")

for category in ["safe", "borderline", "malicious"]:
    folder = BASE / category

    if not folder.exists():
        print(f"Skipping missing folder: {folder}")
        continue

    print()
    print(f"===== ISOLATION FOREST: {category.upper()} =====")
    print()

    for file_path in sorted(folder.glob("*.txt")):
        text = file_path.read_text(
            encoding="utf-8"
        )

        result = predict_anomaly(text)

        print(file_path.name)
        print(f"  prediction: {result['prediction']}")
        print(f"  anomaly: {result['is_anomaly']}")
        print(f"  decision score: {result['decision_score']:.6f}")
        print()
