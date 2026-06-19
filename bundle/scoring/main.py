import sys
import os
import time

from algorithm_scoring.score_assembler import MUnitQuestAlgorithmChallengeOrchestrator as Scorer


def main():
    assert len(sys.argv) == 5, "Usage python3 main.py <input_path> <ground_truth_path> <output_path> <isometric | dynamic>"
    input_path: str = sys.argv[1]
    ground_truth_path: str = sys.argv[2]
    output_path: str = sys.argv[3]
    mode: str = sys.argv[4]

    munitquest_scorer: Scorer = Scorer(
        prediction_path=input_path,
        data_path=ground_truth_path,
        mode=mode
    )

    munitquest_scorer.run()
    munitquest_scorer.export(output_path)


if __name__ == "__main__":
    main()
