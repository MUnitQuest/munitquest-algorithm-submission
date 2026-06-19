import pytest

from algorithm_scoring.score_recording import validate_prediction_file


def test_valid():
    valid_path: str = "tests/testdata/eventfiles/valid.tsv"

    valid, errors, _ = validate_prediction_file(valid_path)
    assert valid
    assert len(errors) == 0


def test_invalid_columns():
    path: str = "tests/testdata/eventfiles/invalid_missing_col.tsv"

    valid, errors, _ = validate_prediction_file(path)
    assert valid is False
    assert len(errors) == 1
    assert errors[0].get("code", "") == "MISSING_EVENT_COLUMN"
    
    message: str = errors[0].get("issueMessage", "")
    assert message == "Missing required columns: ['description', 'duration']"


def test_invalid_description():
    path: str = "tests/testdata/eventfiles/invalid_description.tsv"

    valid, errors, _ = validate_prediction_file(path)
    assert valid is False
    assert len(errors) == 1
    assert errors[0].get("code", "") == "MISSING_MU_SPIKE_EVENTS"


def test_invalid_onset():
    path_invalid_type: str = "tests/testdata/eventfiles/invalid_onset_type.tsv"

    valid, errors, _ = validate_prediction_file(path_invalid_type)
    assert valid is False
    assert len(errors) == 1
    assert errors[0].get("code", "") == "ONSET_MUST_BE_NUMERIC"

    path_invalid_entry: str = "tests/testdata/eventfiles/invalid_onset_entry.tsv"

    valid, errors, _ = validate_prediction_file(path_invalid_entry)
    assert valid is False
    assert len(errors) == 1
    assert errors[0].get("code", "") == "ONSET_NOT_LARGER_ZERO"

    message: str = errors[0].get("issueMessage", "")
    assert "Onset must be >= 0" in message
    assert "10" in message and "20" in message


def test_invalid_duration():
    path_invalid_entry: str = "tests/testdata/eventfiles/invalid_duration_entry.tsv"

    valid, errors, _ = validate_prediction_file(path_invalid_entry)
    assert valid is False
    assert len(errors) == 1
    assert errors[0].get("code", "") == "DURATION_NOT_ZERO"

    message: str = errors[0].get("issueMessage", "")
    assert "Duration for MU spikes must always be 0" in message
    assert "0" in message and "10" in message


def test_invalid_sample():
    path_invalid_type: str = "tests/testdata/eventfiles/invalid_sample_type.tsv"

    valid, errors, _ = validate_prediction_file(path_invalid_type)
    assert valid is False
    assert len(errors) == 1
    assert errors[0].get("code", "") == "SAMPLE_MUST_BE_INTEGER"

    path_invalid_entry: str = "tests/testdata/eventfiles/invalid_sample_entry.tsv"
    
    valid, errors, _ = validate_prediction_file(path_invalid_entry)
    assert valid is False
    assert len(errors) == 1
    assert errors[0].get("code", "") == "SAMPLE_NOT_LARGER_ZERO"

    message: str = errors[0].get("issueMessage", "")
    assert "Sample must be >= 0" in message
    assert "0" in message and "10" in message


def test_invalid_unitid():
    path_invalid_type: str = "tests/testdata/eventfiles/invalid_unitid_type.tsv"

    valid, errors, _ = validate_prediction_file(path_invalid_type)
    assert valid is False
    assert len(errors) == 1
    assert errors[0].get("code", "") == "ID_MUST_BE_INTEGER"

    path_invalid_entry: str = "tests/testdata/eventfiles/invalid_unitid_entry.tsv"
    
    valid, errors, _ = validate_prediction_file(path_invalid_entry)
    assert valid is False
    assert len(errors) == 1
    assert errors[0].get("code", "") == "UNIT_ID_NOT_LARGER_ZERO"

    message: str = errors[0].get("issueMessage", "")
    assert "unit_id must be >= 0" in message
    assert "0" in message and "10" in message


# skip for now
@pytest.mark.skip
def test_invalid_format():
    path: str = "tests/testdata/eventfiles/invalid.tsv"

    valid, errors, _ = validate_prediction_file(path)
    assert valid is False
    assert len(errors) == 1


def test_mixed():
    path: str = "tests/testdata/eventfiles/invalid_mixed.tsv"

    valid, errors, _ = validate_prediction_file(path)
    assert valid is False
    assert len(errors) == 4

    codes: list[str] = [error.get("code") for error in errors]
    assert all(
        [
            code in codes for code in [
                "ONSET_NOT_LARGER_ZERO", "DURATION_NOT_ZERO", "UNIT_ID_NOT_LARGER_ZERO", "SAMPLE_MUST_BE_INTEGER"
            ]
        ]
    )
