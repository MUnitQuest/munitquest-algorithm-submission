import pytest
import json

from algorithm_scoring.score_recording import validate_prediction_log


def test_valid():
    prediction: str = "tests/testdata/prediction_logs/valid_events.tsv"

    valid, errors, warnings = validate_prediction_log(prediction=prediction)
    print(errors)
    assert valid is True
    assert len(errors) == 0
    assert len(warnings) == 0


def test_missing_file():
    prediction: str = "tests/testdata/prediction_logs/missing_log_events.tsv"

    valid, errors, warnings = validate_prediction_log(prediction=prediction)
    assert valid is False
    assert len(errors) == 1
    assert errors[0]["code"] == "MISSING_LOGFILE_FOR_PREDICTION"


def test_missing_key():
    prediction: str = "tests/testdata/prediction_logs/invalid_missing_key_events.tsv"

    valid, errors, warnings = validate_prediction_log(prediction=prediction)
    print(errors)
    assert valid is False
    assert len(errors) == 2

    assert errors[0].get("code", "") == "MISSING_LOG_REQUIREMENT"

    message: str = errors[0].get("issueMessage", "")
    assert "Execution" in message and "Environment" in message and not "RandomKey" in message

    assert errors[1].get("code", "") == "INVALID_LOG_SCHEMA"


def test_invalid_generatedby():
    prediction: str = "tests/testdata/prediction_logs/invalid_generatedby_events.tsv"

    valid, errors, warnings = validate_prediction_log(prediction=prediction)
    assert valid is False
    assert len(errors) == 4
    assert len(warnings) == 2

    expected_err_codes = [
        "MISSING_LOG_REQUIREMENT",
        "INVALID_DATATYPE_LOGFILE",
        "EMPTY_LOG_REQUIREMENT"
    ]
    assert all(
        [err_code["code"] in expected_err_codes for err_code in errors]
    )

    expected_warn_codes = [
        "EMPTY_LOG_REQUIREMENT",
    ]
    assert all(
        [warn_code["code"] in expected_warn_codes for warn_code in warnings]
    )


def test_invalid_duration():
    prediction: str = "tests/testdata/prediction_logs/invalid_duration_events.tsv"

    valid, errors, warnings = validate_prediction_log(prediction=prediction)
    assert valid is False
    assert len(errors) == 1
    assert errors[0].get("code", "") == "INVALID_RUNTIME_ENTRY"
    assert errors[0].get("issueMessage", "") == "Runtime must be > 0."


def test_invalid_environment():
    prediction: str = "tests/testdata/prediction_logs/invalid_env_events.tsv"

    valid, errors, warnings = validate_prediction_log(prediction=prediction)
    assert valid is False
    assert len(errors) == 1
    expected_errs: list[str] = [
        "MISSING_LOG_REQUIREMENT",
    ]

    assert all(
        [err_code["code"] in expected_errs for err_code in errors]
    )
    assert "Environment" in errors[0].get("issueMessage", "")


def test_complete_logfile():
    prediction: str = "tests/testdata/prediction_logs/invalid_multi_events.tsv"

    valid, errors, warnings = validate_prediction_log(prediction=prediction)
    print(errors)
    print(warnings)
    assert valid is False
    assert len(errors) == 5
    assert len(warnings) == 2
    