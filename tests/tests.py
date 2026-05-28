import pytest
import numpy as np
import pandas as pd
from ..bundle.scoring.isometric.scoring import ScoringConfig, MUnitQuestScoring

def test_spike_based_scoring():

    steps=[
        {
            "step": "remove_duplicates",
            "max_shift": 0.01,
            "tolerance": 0.001,
            "threshold": 0.3,
            "mode": "first"
        },
        {
            "step": "validate_prediction"
        }
]

    cfg = ScoringConfig(
        fsamp=2048,
        steps=steps,
        data=None,
        ground_truth="./testdata/example_reference.tsv",
        signal_metrics=False
    )

    prediction = "./testdata/example_prediction.tsv"
    scorer = MUnitQuestScoring(prediction=prediction, cfg=cfg)
    scorer.validate()
    scorer.get_score()

    assert np.isclose(scorer.score, 5.976824944609641), (
        "Your does not match the expected value"
    )

def test_signal_based_scoring():

    steps=[
        {
            "step": "remove_duplicates",
            "max_shift": 0.01,
            "tolerance": 0.001,
            "threshold": 0.3,
            "mode": "first"
        },
        {
            "step": "validate_prediction"
        },
            {
        "step": "fit_from_spikes"
        },
        {
            "step": "bad_source_detection",
            "quality_metric": "sil",
            "threshold": 0.9,
            "min_spikes": 10,
            "mode": "below"
        } 
]

    cfg = ScoringConfig(
        fsamp=2048,
        steps=steps,
        data="./testdata/example_emg.edf",
        ground_truth="./testdata/example_reference.tsv",
        signal_metrics=True
    )

    prediction = "./testdata/example_prediction.tsv"
    scorer = MUnitQuestScoring(prediction=prediction, cfg=cfg)
    scorer.validate()
    scorer.get_score()

    assert np.isclose(scorer.score, 11.060158277942975), (
        "Your does not match the expected value"
    )    

    