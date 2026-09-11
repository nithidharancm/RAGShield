from pathlib import Path
import joblib

MODEL_FILE = Path("ml/models/ragshield_detector.pkl")
BASE = Path("ml_training_extra")

model = joblib.load(MODEL_FILE)

for category in ["safe", "malicious"]:
    print(f"\n===== ML {category.upper()} TESTS =====\n")
    for file_path in sorted((BASE / category).glob("*.txt")):
        text = file_path.read_text(encoding="utf-8")
        prediction = model.predict([text])[0]
        probabilities = model.predict_proba([text])[0]
        probability_map = dict(zip(model.classes_, probabilities))

        print(file_path.name)
        print(f"  prediction: {prediction}")
        print(f"  SAFE: {probability_map.get('SAFE', 0):.2%}")
        print(
            f"  MALICIOUS: "
            f"{probability_map.get('MALICIOUS', 0):.2%}"
        )
        print()
