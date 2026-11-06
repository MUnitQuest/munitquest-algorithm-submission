"""

Funcionality for the scoring of the MUnitQuest algorithm Challenges.

"""

import numpy as np
import pandas as pd
pd.options.mode.chained_assignment = None

from dataclasses import dataclass, field
from typing import Optional, Union, Any, Literal
from pyedflib.highlevel import read_edf
from muniverse.algorithms.post_processing import PostProcessCBSS
from muniverse.algorithms.core import est_spike_times
from muniverse.evaluation.evaluate import match_spike_trains, max_xcorr, bin_spikes

from .validate import validate_prediction_file, validate_prediction_log

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
    # TODO lower bound on bins .85 sil, 28 pnr
    sil_bins: list = field(default_factory=lambda: [0.85, 0.925, 0.95])
    pnr_bins: list = field(default_factory=lambda: [28, 33.9, 37.1])
    cod_bins: list = field(default_factory=lambda: [0.05, 0.197, 0.372, 0.730])


class MUnitQuestScoring:
    """ 
    Class to score individual recordings in MUnitQuest 
    
    
    """

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
        self.cod_bins = cfg.cod_bins
        self.signal_metrics = cfg.signal_metrics

        self.score: float = 0
        self.global_metrics: dict = {}
        self.unit_metrics: pd.DataFrame = pd.DataFrame()
        self.valid: bool = False
        self.errors: list = []
        self.warnings: list = []
    
    @property
    def metrics(self):
        metrics: dict[str, float | int] = {
            "score": self.score,
            **self.global_metrics
        }
        
        return metrics

    def validate(self):
        """
        Validate the prediction file

        """
        valid_tsv, errors_tsv, warnings_tsv = validate_prediction_file(self.prediction)

        logfile: str = self.prediction.replace("events.tsv", "log.json")
        valid_json, errors_json, warnings_json = validate_prediction_log(logfile)
        
        self.valid = valid_tsv and valid_json
        self.errors += errors_tsv + errors_json
        self.warnings += warnings_tsv + warnings_json

    def get_score(
            self,
            threshold: float = 0.5,
            min_n_spikes: int = 25,
            mode: Literal["dynamic", "isometric"] = "isometric",
            **kwargs
        ):
        """
        Calculate score for your prediction.

        Args
        ----
        threshold : float, default 0.5
            Threshold for scoring on F1/Fbeta
        min_n_spikes : int, default 25
            A predicted unit has to exhibit at least min_n_spikes within the scoring window
        mode : Literal["dynamic", "isometric"], default "isometric"
            Scoring mode
        """

        # Read data
        spikes = pd.read_table(self.prediction)

        # Make sure to only score "motor-unit-spike" events
        spikes = spikes[
            spikes["event_type"] == "motor-unit-spike"
        ]

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
        _, sources, _, metadata = model.post_process(
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
        
        matched["F1_weight"] = (matched["F1"] > threshold).astype(int)
        matched["F1_weighted"] = matched["F1_weight"] * matched["F1"]
        matched_f1_sum: float = np.sum(matched["F1_weighted"])
        self.score += matched_f1_sum

        if not self.signal_metrics:
            good = df[df["unit_id_ref"].notna()]
            rejected = df[df["unit_id_ref"].isna()]

            self.global_metrics = {
                "accepted_units": len(matched),
                "f1_mean": matched["F1_weighted"].loc[matched["F1_weighted"] > 0].mean(),
                "rejected_units": len(rejected)
            }

            mask1 = df["unit_id_ref"].isna().tolist()
            mask2 = df["status"].isin(["good"]).tolist()
            mask = np.array(mask1) & np.array(mask2)
            df.loc[mask, "status"] = "masked"
            df.loc[mask, "status_description"] = "Unmachted source"
            self.unit_metrics = df

        else:
            # Reject unmatched units below a SIL threshold
            df.loc[
                (df["sil"] < self.sil_bins[0]) &
                (df["unit_id_ref"].isna()), 
                "status"
            ] = "masked"
            df.loc[
                (df["sil"] < self.sil_bins[0]) &
                (df["unit_id_ref"].isna()), 
                "status_description"
            ] = f"Unmatched source below a SIL threshold of {self.sil_bins[0]}"  

            # Reject unmatched units with less than min_n_spikes spikes
            df["n_pred_spikes"] = df["TP"] + df["FP"] 
            df.loc[
                (df["n_pred_spikes"] < min_n_spikes) &
                (df["unit_id_ref"].isna()), 
                "status"
            ] = "masked"
            df.loc[
                (df["n_pred_spikes"] < min_n_spikes) &
                (df["unit_id_ref"].isna()), 
                "status_description"
            ] = f"Unmtached source with less than {min_n_spikes} spikes"  

            # Calculate source-based scores
            df["sil_map"] = df["sil"].apply(lambda x: self._map_sil(x))
            df["pnr_map"] = df["pnr"].apply(lambda x: self._map_pnr(x))
            df["cod_map"] = df["cod_isi"].apply(lambda x: self._map_cod_isi(x))
            
            # isometric case
            if mode == "isometric":
                
                df["metric_score"] = 1/3 * (
                    df["sil_map"] + df["pnr_map"] + df["cod_map"]
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
                    "f1_mean": matched["F1_weighted"].loc[matched["F1_weighted"] > 0].mean(),
                    "sil_mean": good["sil"].mean(),
                    "pnr_mean": good["pnr"].mean(),
                    "cod_isi_mean": good["cod_isi"].mean(),
                    "rejected_units": len(rejected),
                }

                self.unit_metrics = df
            
            # dynamic case
            elif mode == "dynamic":
                # limit prediction to scoring window
                t_start: float = kwargs.get("t_start", 0.)
                t_end: float = kwargs.get("t_end", spikes["onset"].max() + .1)
                spikes_predicted: pd.DataFrame = spikes[
                    (spikes["onset"] > t_start) &
                    (spikes["onset"] < t_end)
                ]
                # initialize F1-related metrics
                df["TP_model"] = 0
                df["FN_model"] = 0
                df["FP_model"] = 0
                df["Recall_model"] = 0.0
                
                # get unmatched unit ids
                unit_ids: list[int] = df.loc[
                    (df["unit_id_ref"].isna()) & 
                    (df["status"] == "good"),
                    "unit_id"
                ].to_list()
                # unmatched["output_unit_id"] = unmatched["output_unit_id"].astype(int)
                
                # for each unmatched unit
                # unit_ids: list[int] = unmatched["unit_id"].tolist()
                for unit_id in unit_ids:
                    
                    spike_times_predicted: np.ndarray = spikes_predicted["onset"].loc[
                        spikes_predicted["unit_id"] == unit_id
                    ].to_numpy()
                    
                    # estimate spike times
                    source_index: int = int(df[df["unit_id"] == unit_id]["output_unit_id"].values[0])
                    source: np.ndarray = sources[source_index, :]
                    
                    spike_times_estimated, _ = est_spike_times(
                        source=source,
                        fsamp=self.fsamp,
                    )

                    spike_times_estimated = spike_times_estimated[
                        (spike_times_estimated > t_start * self.fsamp) &
                        (spike_times_estimated < t_end * self.fsamp)
                    ]

                    spike_train_predicted: np.ndarray = bin_spikes(
                        spike_times=spike_times_predicted,
                        fsamp=self.fsamp,
                        t_start=t_start,
                        t_end=t_end
                    )

                    spike_train_ref: np.ndarray = bin_spikes(
                        spike_times=spike_times_estimated / self.fsamp,
                        fsamp=self.fsamp,
                        t_start=t_start,
                        t_end=t_end
                    )

                    # shift
                    _, shift = max_xcorr(
                        spike_train_predicted,
                        spike_train_ref,
                        max_shift=int(0.1 * self.fsamp)
                    )

                    # match spike trains
                    tp, fp, fn = match_spike_trains(
                        spike_train_predicted,
                        spike_train_ref,
                        shift=shift,
                        fsamp=self.fsamp
                    )

                    # between estimated spike times and predicted spike times
                    df.loc[df["unit_id"] == unit_id, "TP_model"] = tp
                    df.loc[df["unit_id"] == unit_id, "FP_model"] = fp
                    df.loc[df["unit_id"] == unit_id, "FN_model"] = fn
                    
                    recall_model: float = tp / (tp + fn) if (tp + fn) > 0 else 0
                    recall_model = 0 if recall_model <= threshold else recall_model
                    df.loc[df["unit_id"] == unit_id, "Recall_model"] = recall_model
                    df.loc[df["unit_id"] == unit_id, "status"] = "good" if recall_model > 0 else "masked"
                    df.loc[df["unit_id"] == unit_id, "status_description"] = "n/a" if recall_model > 0 else f"Unmatched source below a quality threshold of {threshold}"

                df["metric_score"] = 1/3 * (
                    df["sil_map"] + df["pnr_map"] + df["cod_map"]
                ) * df["Recall_model"]

                # Score based on unmatched units
                unmatched = df[
                    (df["unit_id_ref"].isna()) & 
                    (df["status"] == "good")
                ]

                self.score += unmatched["metric_score"].sum()

                rejected: pd.DataFrame = df[df["status"] == "masked"]
                good = df[df["status"] == "good"]

                unmatched: pd.DataFrame = df[
                    (df["unit_id_ref"].isna()) & 
                    (df["status"] == "good")
                ]

                self.global_metrics = {
                    "accepted_units": len(matched) + len(unmatched),
                    "matched_units": len(matched),
                    "unmatched_units": len(unmatched),
                    "f1_mean": matched["F1_weighted"].loc[matched["F1_weighted"] > 0].mean(),
                    "recall_mean": unmatched["Recall_model"].loc[unmatched["Recall_model"] > 0].mean(),
                    "sil_mean": good["sil"].mean(),
                    "pnr_mean": good["pnr"].mean(),
                    "cod_isi_mean": good["cod_isi"].mean(),
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

    def _map_cod_isi(self, cod_isi):
        """Map CoV-ISI score"""

        if cod_isi < self.cod_bins[0]:
            score = 0
        elif cod_isi < self.cod_bins[1]:
            score = 1
        elif cod_isi < self.cod_bins[2]:
            score = 0.75
        elif cod_isi < self.cod_bins[3]:
            score = 0.5   
        else:
            score = 0   

        return score
