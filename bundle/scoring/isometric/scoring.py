import json

print("Running scoring program for the isometric challenge...")

placeholder: dict[str, float | int] = {
    "silhouette_score": 1.,
    "pnr": 30,
}

with open("/app/output/scores.json", "w") as f:
    json.dump(placeholder, f, indent=4)