"""
This module orechstrates the scoring of submissions by
collecting and validating submitted event-files, running the
scoring function on each collected recording before exporting 
tracked and aggregated results to the leaderboard and a html-report.
"""


import os
import json
import time
import numpy as np
import pandas as pd

from functools import wraps
from typing import Any

from algorithm_scoring.score_recording import MUnitQuestScoring, ScoringConfig, ValidationItem
from algorithm_scoring.report import AlgorithmSubmissionReport


def timer(description: str):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start: float = time.perf_counter()
            result: Any = func(*args, **kwargs)
            elapsed: float = time.perf_counter() - start
            print(f"{description}: {elapsed:.2f} seconds")
            return result
        return wrapper
    return decorator


class MUnitQuestAlgorithmChallengeOrchestrator:
    """ wraps individual recordings/scorings, name debateable ;) """

    def __init__(self, prediction_path: str, data_path: str, mode: str):
        """
        Init for scoring orchestration

        Args:
            prediction_path (str): directory of submitted predictions
            ground_truth_path (str): directory of ground truth labels
            mode (str): inidicates isometric or dynamic scoring
        """
        self.prediction_path = prediction_path
        self.ground_truth_path = data_path + f"groundtruth-{mode}"
        self.mode = mode

        self.recording_path: str = data_path

        self.errors: list[dict] = []
        self.warnings: list[dict] = []

        self.results: dict[str, dict[float]] = {}  # keeps track of each scoring result
        self.unit_metrics: dict[str, pd.DataFrame] = {}

        self.reporter: AlgorithmSubmissionReport | None = None
        self.book: pd.DataFrame = pd.read_csv("bookkeeping.csv")
    
    @property
    def metrics(self) -> dict:
        """
        Aggregates to individual metrics to global score for leaderboard export
        """
        # pandas is a nice option as it handles missing data automatically
        # filenames will be index, that's why mean works
        metric_df: pd.DataFrame = pd.DataFrame.from_dict(self.results, orient="index")
        if not self.valid:
            for col in metric_df.columns:
                metric_df[col] = 0.
        universal_metrics: dict = metric_df.mean().to_dict()

        return universal_metrics
    
    @property
    def valid(self):
        return len(self.errors) == 0
    
    def _to_json(self, data: dict, path: str) -> None:
        """
        Helper function to save data as json file
        Args:
            data (dict): data to save
            path (str): path to write data to
        """
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    
    @staticmethod
    def _pretty_print(data: dict) -> None:
        """ Helper to aesthetically print dictionaries """
        print(json.dumps(data, indent=4))
        print("\n")
    
    def _bookkeep(self, recording: str) -> bool:
        """
        Helper to lookup, whether we have full labels  available for a recording.

        Args:
            recording (str): name of the recording to lookup 

        Returns:
            bool: whether to do signal-based scoring or sike-based
        """
        full_labels: bool = True
        if recording in list(self.book["newname"]):
            full_labels = self.book["full_labels"].loc[
                self.book["newname"] == recording
            ].item()
        return full_labels
    
    def export(self, path: str, export_mudf: bool=True) -> None:
        """
        Exports the leaderboard-effective, aggregated results. Additionally,
        a dataframe for each recording is exported, containing MU-level information,
        as well as a detailed html report.

        Args:
            path (str): output directory
        """
        # invalid submissions should not be on the leaderboard
        filename: str = os.path.join(path, "scores.json")
        self._to_json(self.metrics, filename)

        # also invalid submissions can be scored
        if export_mudf:
            table_path: str = os.path.join(path, "motor_unit_details")
            if not os.path.exists(table_path):
                os.makedirs(table_path)
            
            for key, df in self.unit_metrics.items():
                filename: str = os.path.join(table_path, key.split("/")[-1].replace("events.tsv", "mu-details.tsv"))
                df.to_csv(filename, sep="\t", index=False)
        
        # export html-report
        self.reporter.save_html_report(os.path.join(path, "detailed_results.html"))

        return None

    @staticmethod
    @timer("Signal-based scoring took")
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
                "step": "get_discharge_metric",
                "metric": "cod_isi"
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
    @timer("Spike-train scoring took")
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
            },
            {
                "step": "get_discharge_metric",
                "metric": "cod_isi"
            },
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

    @timer("Aggregated scoring time")
    def run(self, **kwargs) -> None:
        """ orchestrates scoring """
        label_files: list[str] = sorted([f for f in os.listdir(self.ground_truth_path) if f.endswith("_events.tsv")])
        for label_file in label_files:
            # get ground-truth path
            ground_truth: str = os.path.join(self.ground_truth_path, label_file)
            # get corresponding recording
            recording_id: str = label_file[:13]
            recording: str = os.path.join(
                self.recording_path,
                f"{recording_id}_challenge-{self.mode}",
                f"{label_file.replace("desc-groundtruthspikes_events.tsv", "emg.edf")}"
            )

            # get prediction
            prediction: str = os.path.join(self.prediction_path, label_file.replace("groundtruthspikes", "decomposed"))
            
            # check if there exists an according prediction
            if not os.path.exists(prediction):
                self.warnings.append(
                    ValidationItem(
                        code="MISSING_PREDICTION",
                        location=recording,
                        issueMessage=f"No prediction found for {recording}. Ensure accurate filename conventions, e.g. {prediction}",
                        severity="warning"
                    ).itemize()
                )
                continue

            pred_df: pd.DataFrame = pd.read_csv(prediction, sep="\t")
            if not len(pred_df) > 0:
                self.warnings.append(
                    ValidationItem(
                        code="EMPTY_PREDICTION",
                        location=recording,
                        issueMessage=f"Prediction empty for {recording}",
                        severity="warning"
                    ).itemize()
                )
                continue
            
            print(f"Scoring detected Motor Units\nPrediction: {prediction}\nRecording: {recording}\nLabelfile: {ground_truth}")

            # check if signal-based recording required
            full_labels: bool = self._bookkeep(recording.split("/")[-1])

            if not full_labels:
                # get preprocessed recording
                preprocessed_recording: str = os.path.join(
                    self.recording_path,
                    "preprocessed",
                    f"{recording_id}_challenge-{self.mode}_desc-preProcessed_emg.edf"
                )

                metrics, errors, unit_metrics = self._score_signal_based(
                    prediction=prediction,
                    ground_truth=ground_truth,
                    recording=preprocessed_recording
                )
            else:
                metrics, errors, unit_metrics = self._score_spike_trains(
                    prediction=prediction,
                    ground_truth=ground_truth
                )
            
            self.results[prediction] = metrics
            self.unit_metrics[prediction] = unit_metrics
            self.errors += errors
            
            self._pretty_print(metrics)
        
        print("------ Universal Results ------")
        print(f"Submission status: {'VALID' if self.valid else 'INVALID'}")
        if not self.valid:
            print(f"Number of errors: {len(self.errors)}\n")
        self._pretty_print(self.metrics)

        self.reporter = AlgorithmSubmissionReport(
            results=self.results,
            universal_metrics=self.metrics,
            issues=self.errors + self.warnings
        )
        self.reporter.generate_report()
        
        return None
