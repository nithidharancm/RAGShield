from pathlib import Path
from ingestion.scanner import scan_document

BASE = Path("test_documents")

for category in ["safe", "borderline", "malicious"]:
    print(f"\n===== {category.upper()} DOCUMENTS =====\n")
    for file_path in sorted((BASE / category).glob("*.txt")):
        text = file_path.read_text(encoding="utf-8")
        result = scan_document(text)
        print(file_path.name)
        print(f"  status: {result['status']}")
        print(f"  risk_score: {result['risk_score']}")
        print(f"  ml_prediction: {result['ml_prediction']}")
        print(f"  malicious_probability: "
              f"{result['ml_malicious_probability']:.2%}")
        print()
