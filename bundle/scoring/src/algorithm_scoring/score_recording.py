"""

Funcionality for the scoring of the MUnitQuest algorithm Challenges.

"""

import numpy as np
import pandas as pd
import json
import os

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Union, Any, Literal
from pyedflib.highlevel import read_edf
from muniverse.algorithms.post_processing import PostProcessCBSS
from muniverse.algorithms.core import est_spike_times
from muniverse.evaluation.evaluate import match_spike_trains, max_xcorr, bin_spikes

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


@dataclass
class ValidationItem:
    """ 
    Data class to configure errors and warnings 

    Args
    ----
    code : str
        code of the warning, error
    
    severity : str
        error or warning
    
    location : str
        file the error/warning occured in
    
    origin : str
        to adhere to validator from data challenge.
        Only resolves to MUnitQuest Custom Validator
    
    issueMessage : str
        detailed description of the error/warning

    """
    code: str
    location: str
    issueMessage: str
    severity: str = "error"
    origin: str = "MUnitQuest Custom Validator"

    def itemize(self):
        return asdict(self)


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

    def get_score(self, threshold: float = 0.5, mode: Literal["dynamic", "isometric"] = "isometric", **kwargs):
        """
        Calculate score for your prediction.

        Args
        ----
        threshold : float, default 0.5
            Threshold for scoring on F1
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
        
        matched["F1_weight"] = matched["F1"].apply(lambda x: 1 if x > threshold else 0)
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
            # isometric case
            if mode == "isometric":
                # Reject unmatched units below a SIL threshold
                df.loc[
                    (df["sil"] < 0.85) &
                    (df["unit_id_ref"].isna()), 
                    "status"
                ] = "masked"
                df.loc[
                    (df["sil"] < 0.85) &
                    (df["unit_id_ref"].isna()), 
                    "status_description"
                ] = "Unmatched source below a SIL threshold of 0.85"  

                # Reject unmatched units with less than 10 spikes
                df["n_pred_spikes"] = df["TP"] + df["FP"] 
                df.loc[
                    (df["n_pred_spikes"] < 10) &
                    (df["unit_id_ref"].isna()), 
                    "status"
                ] = "masked"
                df.loc[
                    (df["n_pred_spikes"] < 10) &
                    (df["unit_id_ref"].isna()), 
                    "status_description"
                ] = "Unmtached source with less than 10 spikes"  

                # Calculate source-based scores
                df["sil_map"] = df["sil"].apply(lambda x: self._map_sil(x))
                df["pnr_map"] = df["pnr"].apply(lambda x: self._map_pnr(x))
                df["cod_map"] = df["cod_isi"].apply(lambda x: self._map_cod_isi(x))

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
                df["F1_model"] = 0.
                
                # get unmatched unit ids
                unmatched: pd.DataFrame = df[
                    (df["unit_id_ref"].isna()) & 
                    (df["status"] == "good")
                ]
                unmatched["output_unit_id"] = unmatched["output_unit_id"].astype(int)
                
                # for each unmatched unit
                unit_ids: list[int] = unmatched["unit_id"].tolist()
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

                    f1_model: float = 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) > 0 else 0
                    f1_model = 0 if f1_model <= threshold else f1_model
                    df.loc[df["unit_id"] == unit_id, "F1_model"] = f1_model
                    df.loc[df["unit_id"] == unit_id, "status"] = "good" if f1_model > threshold else "masked"
                    df.loc[df["unit_id"] == unit_id, "status_description"] = "n/a" if f1_model > threshold else f"Unmatched source below a quality threshold of {threshold}"
                
                # update metrics
                self.score += df["F1_model"].sum()

                rejected: pd.DataFrame = df[df["status"] == "masked"]
                unmatched: pd.DataFrame = df[
                    (df["unit_id_ref"].isna()) & 
                    (df["status"] == "good")
                ]

                self.global_metrics = {
                    "accepted_units": len(matched) + len(unmatched),
                    "matched_units": len(matched),
                    "unmatched_units": len(unmatched),
                    "f1_mean": matched["F1_weighted"].loc[matched["F1_weighted"] > 0].mean(),
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


def validate_prediction_file(
    file: str,
) -> tuple[bool, list[dict], list[dict]]:
    """
    Validate a BIDS-like motor unit events table.

    Required columns:
    - onset       : float >= 0
    - duration    : must be 0
    - sample      : integer
    - unit_id     : integer
    - event_type  : must include columns with the label "motor-unit-spike"

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
    errors: list[dict] = []
    warnings: list[dict] = []  # template for raising warnings

    # Define required column names
    required_columns = {
        "onset",
        "duration",
        "sample",
        "unit_id",
        "event_type",
    }

    # Load the file
    try:
        df = pd.read_table(file)
    except Exception as e:
        errors.append(
            ValidationItem(
                code="UNREADABLE_EVENTS_TSV_FORMAT",
                location=file,
                issueMessage=f"Error when reading {file}. Please validate file format. Error message: {e}"
            ).itemize()
        )
        return False, errors, warnings

    # Check if required columns are present
    missing = required_columns - set(df.columns)

    if missing:
        errors.append(
            ValidationItem(
                code="MISSING_EVENT_COLUMN",
                location=file,
                issueMessage=f"Missing required columns: {sorted(missing)}"
            ).itemize()
        )

        # Cannot continue safely
        return False, errors, warnings


    # Check if the file includes motor unit spike events
    mu_df = df[df["event_type"] == "motor-unit-spike"]

    if len(mu_df) == 0:
        errors.append(
            ValidationItem(
                code="MISSING_MU_SPIKE_EVENTS",
                location=file,
                issueMessage="motor-unit-spike missing in event_type column"
            ).itemize()
        )
        return False, errors, warnings

    # Check if all onset values are numeric values and larger than zero
    if not pd.api.types.is_numeric_dtype(mu_df["onset"]):
        errors.append(
            ValidationItem(
                code="ONSET_MUST_BE_NUMERIC",
                location=file,
                issueMessage="Onset must be numeric"
            ).itemize()
        )
    else:
        invalid = mu_df["onset"] < 0

        if invalid.any():
            bad_idx = mu_df.index[invalid].tolist()
            errors.append(
                ValidationItem(
                    code="ONSET_NOT_LARGER_ZERO",
                    location=file,
                    issueMessage=f"Onset must be >= 0, invalid rows: {bad_idx}"
                ).itemize()
            )

    # Check if the duration of all motor unit spikes is zero
    invalid = mu_df["duration"] != 0

    if invalid.any():
        bad_idx = mu_df.index[invalid].tolist()
        errors.append(
            ValidationItem(
                code="DURATION_NOT_ZERO",
                location=file,
                issueMessage=f"Duration for MU spikes must always be 0, invalid rows: {bad_idx}"
            ).itemize()
        )

    # Check if the sample columns contains only integers
    if not pd.api.types.is_integer_dtype(mu_df["sample"]):
        errors.append(
            ValidationItem(
                code="SAMPLE_MUST_BE_INTEGER",
                location=file,
                issueMessage="Sample must be of type Integer"
            ).itemize()
        )
    else:
        invalid: pd.Series[bool] = mu_df["sample"] < 0
        if invalid.any():
            bad_idx = mu_df.index[invalid].tolist()
            errors.append(
                ValidationItem(
                    code="SAMPLE_NOT_LARGER_ZERO",
                    location=file,
                    issueMessage=f"Sample must be >= 0, invalid_rows: {bad_idx}"
                ).itemize()
            )

    # Check if the unit_id is always an integer
    if not pd.api.types.is_integer_dtype(mu_df["unit_id"]):
        errors.append(
            ValidationItem(
                code="ID_MUST_BE_INTEGER",
                location=file,
                issueMessage="Unit ID must be of type Integer"
            ).itemize()
        )
    else:
        invalid: pd.Series[bool] = mu_df["unit_id"] < 0
        if invalid.any():
            bad_idx = mu_df.index[invalid].tolist()
            errors.append(
                ValidationItem(
                    code="UNIT_ID_NOT_LARGER_ZERO",
                    location=file,
                    issueMessage=f"unit_id must be >= 0, invalid_rows: {bad_idx}"
                ).itemize()
            )

    # Final validation
    is_valid = len(errors) == 0

    return is_valid, errors, warnings


def validate_prediction_log(
        logfile: str,
        schema: dict={
            "GeneratedBy": {
                "Name": {
                    "required": True,
                    "type": str
                },
                "Description": {
                    "required": True,
                    "type": str
                },
                "CodeURL": {
                    "required": True,
                    "type": str
                },
                "License": {
                    "required": True,
                    "type": str
                },
                "Version": {
                    "required": False,
                    "type": str | None
                },
                "Container": {
                    "required": False,
                    "type": str | None
                }
            },
            "RuntimeEnvironment": dict,
            "Execution": dict
        }
    ) -> tuple[bool, list[dict], list[dict]]:
    """
    Checks existence and required contents of the logfile
    accompanying each prediction. That logfile is searched for by
    naming conventions.

    Args:
        prediction (str): path to prediction,
        schema (dict): schema for the validator to follow
    
    Returns:
        tuple[bool, list[dict], list[dict]]: valid indicator, errors and warnings
    """
    errors: list[dict] = []
    warnings: list[dict] = []

    if not os.path.exists(logfile):
        prediction_path: str = logfile.replace("log.json", "events.tsv")
        errors.append(
            ValidationItem(
                code="MISSING_LOGFILE_FOR_PREDICTION",
                location=prediction_path,
                issueMessage=f"Logfile missing for prediction: {prediction_path}. Please provide a logfile {logfile}"
            ).itemize()
        )

        return False, errors, warnings
    
    with open(logfile, "r", encoding="utf-8") as f:
        try:
            prediction_log: dict = json.load(f)
        except Exception as e:
            errors.append(
                ValidationItem(
                    code="LOGFILE_NOT_READABLE",
                    location=logfile,
                    issueMessage=f"could not read {logfile}: {e}"
                ).itemize()
            )
            return False, errors, warnings

        # top-level keys
        missing = schema.keys() - prediction_log.keys()
        if len(missing) > 0:
            errors.append(
                ValidationItem(
                    code="MISSING_LOG_REQUIREMENT",
                    location=logfile,
                    issueMessage=f"Missing required keys for logfile {logfile}: {missing}"
                ).itemize()
            )

        for key, data in prediction_log.items():
            # different cases for data being a list or another dict
            if key == "GeneratedBy":
                if not isinstance(data, list):
                    errors.append(
                        ValidationItem(
                            code="INVALID_LOG_SCHEMA",
                            location=logfile,
                            issueMessage=f"Content for {key} must be list"
                        ).itemize()
                    )
                elif not len(data) > 0:
                    errors.append(
                        ValidationItem(
                            code="EMPTY_LOG_REQUIREMENT",
                            location=logfile,
                            issueMessage=f"No entries for {key}"
                        ).itemize()
                    )
                else:
                    for i in range(len(data)):
                        generated_by: dict = data[i]
                        for k, v in schema[key].items():
                            if not k in generated_by.keys():
                                if schema[key][k]["required"]:
                                    errors.append(
                                        ValidationItem(
                                            code="MISSING_LOG_REQUIREMENT",
                                            location=logfile,
                                            issueMessage=f"Please provide {k} in logfile for {key} at index {i}"
                                        ).itemize()
                                    )
                                else:
                                    warnings.append(
                                        ValidationItem(
                                            code="MISSING_LOG_REQUIREMENT",
                                            location=logfile,
                                            issueMessage=f"It is recommended to provide {k} in logfile for {key} at index {i}",
                                            severity="warning"
                                        ).itemize()
                                    )
                            elif not isinstance(generated_by[k], v["type"]):
                                errors.append(
                                    ValidationItem(
                                        code="INVALID_DATATYPE_LOGFILE",
                                        location=logfile,
                                        issueMessage=f"Data type of {k} is expected to be {v["type"]} for {key} at index {i}"
                                    ).itemize()
                                )
                            elif generated_by[k] in ["", "n/a", None]:
                                # code url is allowed to be empty
                                required: bool = schema[key][k]["required"]
                                if required:
                                    errors.append(
                                        ValidationItem(
                                            code="EMPTY_LOG_REQUIREMENT",
                                            location=logfile,
                                            issueMessage=f"Value for {k} required, but empty or not provided, for {key} at index {i}",
                                        ).itemize()
                                    )
                                else:
                                    warnings.append(
                                        ValidationItem(
                                            code="EMPTY_LOG_REQUIREMENT",
                                            location=logfile,
                                            issueMessage=f"Value for {k} is empty or not provided, for {key} at index {i}",
                                            severity="warning"
                                        ).itemize()
                                    )                    
            
            elif key == "Execution":
                if not isinstance(data, schema[key]):
                    errors.append(
                        ValidationItem(
                            code="INVALID_DATATYPE_LOGFILE",
                            location=logfile,
                            issueMessage=f"Data type of {key} is expected to be {schema[key]["type"]}"
                        ).itemize()
                    )
                elif not "Runtime" in data.keys():
                    errors.append(
                        ValidationItem(
                            code="MISSING_LOG_REQUIREMENT",
                            location=logfile,
                            issueMessage=f"Runtime: float needs to be specified in {key}"
                        )
                    )
                else:
                    runtime: Any = data["Runtime"]
                    if not isinstance(runtime, float):
                        errors.append(
                            ValidationItem(
                                code="INVALID_DATATYPE_LOGFILE",
                                location=logfile,
                                issueMessage=f"Data type of Runtime is expected to be float"
                            ).itemize()
                        )
                    elif not runtime > 0.:
                        errors.append(
                            ValidationItem(
                                code="INVALID_RUNTIME_ENTRY",
                                location=logfile,
                                issueMessage=f"Runtime must be > 0."
                            ).itemize()
                        )

    valid: bool = len(errors) == 0

    return valid, errors, warnings
