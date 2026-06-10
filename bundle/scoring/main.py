import sys
import os
import time

from algorithm_scoring.score_recording import MUnitQuestScoring, ScoringConfig


if __name__ == "__main__":
    input_path: str = sys.argv[1]
    ground_truth_path: str = sys.argv[2]
    output_path: str = sys.argv[3]

    predictions: list[str] = os.listdir(input_path)
    # debug
    print(os.listdir(ground_truth_path))

    signal_based_scoring: bool = False

    full_duration: float = 0.
    
    for prediction in predictions:
        if prediction.endswith("events.tsv"):
            start = time.time()
            fullpath: str = os.path.join(input_path, prediction)
            ground_truth: str = os.path.join(ground_truth_path, prediction)

            print(f"Scoring {fullpath} based on {ground_truth}")
            size_bytes = os.path.getsize(fullpath)
            size_mb = size_bytes / (1024 * 1024)

            print(f"File size of predictions: {size_mb:.2f} MB")
            size_bytes = os.path.getsize(ground_truth)
            size_mb = size_bytes / (1024 * 1024)

            print(f"File size of ground_truth: {size_mb:.2f} MB")
            
            if signal_based_scoring:
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

                # TODO dynamically allocate files
                cfg = ScoringConfig(
                    fsamp=2048,
                    steps=steps,
                    data=f"{input_path}/example_emg.edf",
                    ground_truth=f"{input_path}/example_reference.tsv",
                    signal_metrics=True
                )

                prediction = f"{input_path}/example_prediction.tsv"
                scorer = MUnitQuestScoring(prediction=prediction, cfg=cfg)
                scorer.validate()
                scorer.get_score()
                print(scorer.metrics)
            else:
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
                    ground_truth=ground_truth,
                    signal_metrics=False
                )

                scorer = MUnitQuestScoring(prediction=fullpath, cfg=cfg)
                scorer.validate()
                scorer.get_score()
                print(scorer.metrics)
            duration = time.time() - start
            full_duration += duration
            print(f"{duration:.2f}")
    print(f"{full_duration:.2f}")
