import json

import numpy as np
import pandas as pd
from muniverse.algorithms.post_processing import PostProcessCBSS

print("Running scoring program for the isometric challenge...")

placeholder: dict[str, float | int] = {
    "silhouette_score": 1.,
    "pnr": 30,
}

with open("/app/output/scores.json", "w") as f:
    json.dump(placeholder, f, indent=4)

def score_recording(
        prediction: pd.DataFrame,
        ground_truth: pd.DataFrame,
        fsamp: float,
        data: np.ndarray | None,
        steps: list[dict]
) -> float:
    """ 
    Scoring function for the isometric task
    
    """

    # Init score    
    score = 0

    # Apply configured post processing pipeline
    model = PostProcessCBSS(steps=steps)
    _, _, _, metadata = model.post_process(
        data=data,
        spikes=prediction,
        fsamp=fsamp,
        ground_truth=ground_truth
    )

    # Extract the unit status
    df = metadata["unit_status"]

    # Compute the F1 score
    df["F1"] = 2 * df["TP"] / (2 * df["TP"] + df["FP"] + df["FN"])

    # Calculate 
    df["sil_map"] = df["sil"].apply(lambda x: map_sil(x))
    df["pnr_map"] = df["pnr"].apply(lambda x: map_pnr(x))
    df["cov_map"] = df["cov_isi"].apply(lambda x: map_cov_isi(x))

    df["metric_score"] = 1/3 * (
        df["sil_map"] + df["pnr_map"] + df["cov_map"]
    )

    # Score based on matched units
    matched = df[
        (df["unit_id_ref"].notna()) &
        (df["status"] == "good")
    ]
    score += matched["F1"].sum() 

    # Score based on unmatched units
    unmatched = df[
        (df["unit_id_ref"].isna()) & 
        (df["status"] == "good")
    ]
    score += unmatched["metric_score"].sum()

    return score, df    

def map_sil(sil, th=[0.9, 0.925, 0.95]):
    """Map SIL to score"""

    if sil >= th[0] and sil < th[1]:
        score = 0.5
    elif sil >= th[1] and sil < th[2]:
        score = 0.75
    elif sil >= th[2] and sil <= 1:
        score = 1
    else:
        score = 0

    return score

def map_pnr(pnr, th=[30, 35, 40]):
    """Map PNR to score"""

    if pnr >= th[0] and pnr < th[1]:
        score = 0.5
    elif pnr >= th[1] and pnr < th[2]:
        score = 0.75
    elif pnr >= th[2]:
        score = 1
    else:
        score = 0  

    return score

def map_cov_isi(cov_isi, th=[0.1, 0.15, 0.2, 0.35, 0.4, 0.5]):
    """Map CoV-ISI score"""

    if cov_isi < th[0]:
        score = 0
    elif cov_isi < th[1]:
        score = 0.5
    elif cov_isi < th[2]:
        score = 0.75
    elif cov_isi < th[3]:
        score = 1    
    elif cov_isi < th[4]:
        score = 0.75
    elif cov_isi < th[5]:
        score = 0.5 
    else:
        score = 0   

    return score 