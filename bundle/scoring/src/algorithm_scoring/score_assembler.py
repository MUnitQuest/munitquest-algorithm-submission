"""
This module orechstrates the scoring of submissions by
collecting and validating submitted event-files, running the
scoring function on each collected recording before exporting 
tracked and aggregated results to the leaderboard and a html-report.
"""


import os
import json
import numpy as np
import pandas as pd

from algorithm_scoring.score_recording import MUnitQuestScoring, ScoringConfig
from algorithm_scoring.report import AlgorithmSubmissionReport


class MUnitQuestAlgorithmChallengeOrchestrator:
    """ wraps individual recordings/scorings, name debateable ;) """

    def __init__(self, prediction_path: str, ground_truth_path: str):
        """
        Init for scoring orchestration

        Args:
            prediction_path (str): directory of submitted predictions
            ground_truth_path (str): directory of ground truth labels
        """
        self.prediction_path = prediction_path
        self.ground_truth_path = ground_truth_path

        self.errors: list[dict] = []
        self.warnings: list[dict] = []

        self.results: dict[str, dict[float]] = {}  # keeps track of each scoring result
        self.unit_metrics: dict[str, pd.DataFrame]

        self.reporter: AlgorithmSubmissionReport = AlgorithmSubmissionReport()
    
    @property
    def metrics(self) -> dict:
        """
        Aggregates to individual metrics to global score for leaderboard export

        Raises:
            NotImplementedError: _description_
        """
        raise NotImplementedError
    
    def _to_json(self, data: dict, path: str) -> None:
        """
        Helper function to save data as json file
        Args:
            data (dict): data to save
            path (str): path to write data to
        """
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    
    def generate_report(self):
        raise NotImplementedError
    
    def export(self, path: str) -> None:
        """
        Exports the leaderboard-effective, aggregated results

        Args:
            path (str): filepath that must be scores.json
        """
        filename: str = path.split("/")[-1]
        if filename != "scores.json":
            path = path.replace(filename, "scores.json")
        
        self._to_json(self.metrics, path)

        return None

    @staticmethod
    def _score_signal_based(prediction: str, ground_truth: str, recording: str) -> tuple[dict, list, pd.DataFrame]:
        """
        Signal based scoring in the case of incomplete labels. Therefore,
        the submitted event-table is directlyevaluated against the recording.

        Args:
            prediction (str): filepath of events.tsv
            ground_truth (str): filepath of the ground truth (incomplete)
            recording (str): filepath of recording (edf, bdf, edf+, bdf+)

        Returns:
            tuple[dict, list, pd.DataFrame]: metrics of the scorer, list of validation errors,
                and a DataFrame containing detailed information on each Motor Unit.
        """
        steps: list[dict] = [
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

        cfg: ScoringConfig = ScoringConfig(
            fsamp=2048,
            steps=steps,
            data=recording,
            ground_truth=ground_truth,
            signal_metrics=True
        )

        scorer: MUnitQuestScoring = MUnitQuestScoring(prediction=prediction, cfg=cfg)
        scorer.validate()
        scorer.get_score()
        
        return scorer.metrics, scorer.errors, scorer.unit_metrics
    
    @staticmethod
    def _score_spike_trains(prediction: str, ground_truth: str) -> tuple[dict, list, pd.DataFrame]:
        """
        We absolutely know all the spike trains and MUs (synthetic data).
        Hence, we can directly evaluate the event-files.

        Args:
            prediction (str): filepath of predicted events.tsv
            ground_truth (str): filepath of the ground truth events.tsv

        Returns:
            tuple[dict, list, pd.DataFrame]: metrics of the scorer, list of validation errors,
                and a DataFrame containing detailed information on each Motor Unit.
        """
        steps: list[dict] = [
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

        cfg: ScoringConfig = ScoringConfig(
            fsamp=2048,
            steps=steps,
            data=None,
            ground_truth=ground_truth,
            signal_metrics=False
        )

        scorer: MUnitQuestScoring = MUnitQuestScoring(prediction=prediction, cfg=cfg)
        scorer.validate()
        scorer.get_score()
        
        return scorer.metrics, scorer.errors, scorer.unit_metrics

    def run(self) -> None:
        for label_file in os.listdir(self.ground_truth_path):
            ground_truth: str = os.path.join(self.ground_truth_path, label_file)

            # TODO
            # assumes predictions and label files are named equally
            prediction: str = os.path.join(self.prediction_path, label_file)
            # check if there exists an according prediction
            if not os.path.exists(prediction):
                self.warnings.append("TODO")
                continue

            # check if signal-based recording required
            # TODO
            signal_based: bool = False
            recording: str = ""

            if signal_based:
                metrics, errors, unit_metrics = self._score_signal_based(
                    prediction=prediction,
                    ground_truth=ground_truth,
                    recording=recording
                )
            else:
                metrics, errors, unit_metrics = self._score_spike_trains(
                    prediction=prediction,
                    ground_truth=ground_truth
                )
            
            self.results[prediction] = metrics
            self.unit_metrics[prediction] = unit_metrics
            # TODO
            self.warnings += errors
        
        return None
