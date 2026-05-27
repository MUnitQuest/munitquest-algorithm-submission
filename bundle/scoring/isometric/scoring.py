import numpy as np
import pandas as pd

from dataclasses import dataclass, field
from typing import Optional
from pyedflib.highlevel import read_edf
from muniverse.algorithms.post_processing import PostProcessCBSS

@dataclass
class ScoringConfig:
    """ 
    Data class to configure scoring 

    Args
    ----
    fsamp : float
        Sampling rate in Hz

    steps : list of dict
        Applied operations during scoring

    data : str or None          
        Path to data file (optional), which is needed if
        using signal-based metrics

    ground_truth : str or None
        Path to the ground truth spikes file

    signal_metrics : bool , default True
        Wheather to use signal-based metrics for the scoring
        or not

    sil_bins : list of float
        Bin-edges for silhouette-based score

    pnr_bins : list of float
        Bin-edges for PNR-based score 

    cov_bins : list of float
        Bin-edges for CoV-ISI-based score                   

    
    """
    fsamp: float 
    steps: list[dict] 
    data: Optional[str]
    ground_truth: Optional[str] 
    signal_metrics: bool = field(default=True) 
    sil_bins: list = field(default_factory=lambda: [0.9, 0.925, 0.95]) 
    pnr_bins: list = field(default_factory=lambda: [30, 35, 40])
    cov_bins: list = field(default_factory=lambda: [0.1, 0.15, 0.2, 0.35, 0.4, 0.5])  

class MUnitQuestScoring:
    """ Class to score individual recordings in MUnitQuest """

    def __init__(
            self, 
            prediction: str,
            cfg = ScoringConfig
    ):
        """
        Init scoring class

        Args
        ----
        prediction : str
            Path to your spike prediction file
        cfg : ScoringConfig
            Configuration of the scoring program       

        """
        
        self.prediction = prediction
        self.fsamp = cfg.fsamp
        self.steps = cfg.steps
        self.ground_truth = cfg.ground_truth
        self.data = cfg.data
        self.sil_bins = cfg.sil_bins
        self.pnr_bins = cfg.pnr_bins
        self.cov_bins = cfg.cov_bins
        self.signal_metrics = cfg.signal_metrics

        self.score: float = 0
        self.global_metrics: dict = {}
        self.unit_metrics: pd.DataFrame = pd.DataFrame()
        self.valid: bool = False
        self.errors: list = []

    def validate(self):
        """
        Validate the prediction file

        """

        self.valid, self.errors = validate_prediction_file(self.prediction)


    def get_score(self):
        """
        Calculate score for your prediction
        
        """

        # Read data
        spikes = pd.read_table(self.prediction)

        if isinstance(self.ground_truth, str):
            ground_truth = pd.read_table(self.ground_truth)
        else:
            ground_truth = None

        if isinstance(self.data, str):
            data, _ , _ = read_edf(self.data)
        else:
            data = None    

        # Init score    
        self.score = 0

        # Apply configured post processing pipeline
        model = PostProcessCBSS(steps=self.steps)
        _, _, _, metadata = model.post_process(
            data=data,
            spikes=spikes,
            fsamp=self.fsamp,
            ground_truth=ground_truth
        )

        # Extract the unit status
        df = metadata["unit_status"]

        # Compute the F1 score
        df["F1"] = 2 * df["TP"] / (2 * df["TP"] + df["FP"] + df["FN"])

        # Score based on matched units
        matched = df[
            (df["unit_id_ref"].notna()) &
            (df["status"] == "good")
        ]
        self.score += matched["F1"].sum() 

        if not self.signal_metrics:
            good = df[df["unit_id_ref"].notna()]
            rejected = df[df["unit_id_ref"].isna()]

            self.global_metrics = {
                "accepted_units": len(matched),
                "f1_mean": matched["F1"].mean(),
                "rejected_units": len(rejected)
            }

            mask1 = df["unit_id_ref"].isna().tolist()
            mask2 = df["status"].isin(["good"]).tolist()
            mask = np.array(mask1) & np.array(mask2)
            df.loc[mask, "status"] = "masked"
            df.loc[mask, "status_description"] = "Unmachted source"
            self.unit_metrics = df

        else:    

            # Calculate source-based scores
            df["sil_map"] = df["sil"].apply(lambda x: self._map_sil(x))
            df["pnr_map"] = df["pnr"].apply(lambda x: self._map_pnr(x))
            df["cov_map"] = df["cov_isi"].apply(lambda x: self._map_cov_isi(x))

            df["metric_score"] = 1/3 * (
                df["sil_map"] + df["pnr_map"] + df["cov_map"]
            )

            good = df[df["status"] == "good"]
            rejected = df[df["status"] == "masked"]

            # Score based on unmatched units
            unmatched = df[
                (df["unit_id_ref"].isna()) & 
                (df["status"] == "good")
            ]

            self.score += unmatched["metric_score"].sum()

            self.global_metrics = {
                "accepted_units": len(matched) + len(unmatched),
                "matched_units": len(matched),
                "unmatched_units": len(unmatched),
                "f1_mean": matched["F1"].mean(),
                "sil_mean": good["sil"].mean(),
                "pnr_mean": good["pnr"].mean(),
                "cov_isi_mean": good["cov_isi"].mean(),
                "rejected_units": len(rejected),
            }

            self.unit_metrics = df

    def _map_sil(self, sil):
        """Map SIL to score"""

        if sil < self.sil_bins[0]:
            score = 0
        elif sil < self.sil_bins[1]:
            score = 0.5
        elif sil < self.sil_bins[2]:
            score = 0.75
        elif sil <= 1:
            score = 1
        else:
            score = 0

        return score

    def _map_pnr(self, pnr):
        """Map PNR to score"""

        if pnr < self.pnr_bins[0]:
            score = 0
        elif pnr < self.pnr_bins[1]:
            score = 0.5
        elif pnr < self.pnr_bins[2]:
            score = 0.75
        elif pnr >= self.pnr_bins[2]:
            score = 1
        else:
            score = 0  

        return score

    def _map_cov_isi(self, cov_isi):
        """Map CoV-ISI score"""

        if cov_isi < self.cov_bins[0]:
            score = 0
        elif cov_isi < self.cov_bins[1]:
            score = 0.5
        elif cov_isi < self.cov_bins[2]:
            score = 0.75
        elif cov_isi < self.cov_bins[3]:
            score = 1    
        elif cov_isi < self.cov_bins[4]:
            score = 0.75
        elif cov_isi < self.cov_bins[5]:
            score = 0.5 
        else:
            score = 0   

        return score

def validate_prediction_file(
    file: str,
) -> tuple[bool, list[str]]:
    """
    Validate a BIDS-like motor unit events table.

    Required columns:
    - onset       : float >= 0
    - duration    : must be 0
    - sample      : integer
    - unit_id     : integer
    - description : must include "motor-unit-spike"

    Args
    ----
        file : str
            Path to the file   

    Returns
    -------
        is_valid : bool
            True if file is valid.

        errors : list of str
            List of validation error messages.
    """

    # Init list of errors
    errors = []

    # Define required column names
    required_columns = {
        "onset",
        "duration",
        "sample",
        "unit_id",
        "description",
    }

    # Load the file
    try:
        df = pd.read_table(file)
    except:
        errors.append(
            f"Failed loading file {file}."
        )
        return False, errors

    # Check if required columns are present
    missing = required_columns - set(df.columns)

    if missing:
        errors.append(
            f"Missing required columns: {sorted(missing)}"
        )

        # Cannot continue safely
        return False, errors


    # Check if the file includes motor unit spike events
    mu_df = df[df["description"] == "motor-unit-spike"]

    if len(mu_df) == 0:
        errors.append(
            "No rows with description == 'motor-unit-spike'"
        )
        return False, errors

    # Check if all onset values are numeric values and larger than zero
    if not np.issubdtype(mu_df["onset"].dtype, np.number):
        errors.append("'onset' must be numeric")
    else:
        invalid = mu_df["onset"] < 0

        if invalid.any():
            bad_idx = mu_df.index[invalid].tolist()
            errors.append(
                f"'onset' must be >= 0 "
                f"(invalid rows: {bad_idx})"
            )

    # Check if the duration of all motor unit spikes is zero
    invalid = mu_df["duration"] != 0

    if invalid.any():
        bad_idx = mu_df.index[invalid].tolist()
        errors.append(
            f"'duration' must always be 0 "
            f"(invalid rows: {bad_idx})"
        )

    # Check if the sample columns contains only integers
    if not np.issubdtype(mu_df["sample"].dtype, np.integer):

        invalid = np.mod(mu_df["sample"], 1) != 0

        if invalid.any():
            bad_idx = mu_df.index[invalid].tolist()
            errors.append(
                f"'sample' must contain integers "
                f"(invalid rows: {bad_idx})"
            )

    # Check if the unit_id is always an integer
    if not np.issubdtype(mu_df["unit_id"].dtype, np.integer):

        invalid = np.mod(mu_df["unit_id"], 1) != 0

        if invalid.any():
            bad_idx = mu_df.index[invalid].tolist()
            errors.append(
                f"'unit_id' must contain integers "
                f"(invalid rows: {bad_idx})"
            )

    # Final validation
    is_valid = len(errors) == 0

    return is_valid, errors