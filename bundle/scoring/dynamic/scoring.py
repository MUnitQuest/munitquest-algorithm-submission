import json

print("Running scoring program for the dynamic challenge...")

placeholder: dict[str, float] = {
    "accuracy": 1.,
    "precision": 1.,
    "recall": 1.,
    "f1_score": 1.
}

with open("/app/output/scores.json", "w") as f:
    json.dump(placeholder, f, indent=4)