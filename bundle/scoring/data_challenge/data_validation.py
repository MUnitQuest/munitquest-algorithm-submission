import json

placeholder: dict[str, float] = {
    "valid": 1.
}

with open("/app/output/scores.json", "w") as f:
    json.dump(placeholder, f, indent=4)