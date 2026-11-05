import json
import os
import pandas as pd

from dataclasses import dataclass, asdict
from typing import Any


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